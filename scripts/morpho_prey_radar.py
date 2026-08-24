#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Morpho prey radar v1（预言机偏离扫描，事件驱动清算哨兵）— 2026-08-24

背景（notes/morpho-discovery-monitoring-digest-20260814.md + 132 篇 digest 笔记010）：
- Morpho Blue 清算套利的关键 = 预言机节奏预测：oracle 价 vs 现货价偏离即"埋雷"，
  预言机一旦更新 → 头寸资不抵债 → 清算连环（先到先得，Flashblocks 200ms 决胜）
- 本哨兵 = 路径①系统性价差扫描落地：GraphQL 拉市场 → eth_call oracle.price()
  → DeFiLlama 现货 → 偏离分层（≥2% INFO / ≥5% SIGNAL）+ 冻结论价机独立信号

⚠️ oracle 缩放实测（2026-08-24，base 链）——各预言机 price() 小数位不同，不能写死：
- wstETH→WETH / cbETH→WETH / cbXRP→USDC：36 位（raw/1e36 = 报价资产相对价）
- WETH→USDC / cbETH→USDC / USDe / mGLO / USR：24 位（raw/1e24 = USD 价）
- cbBTC→USDC：37 位（raw/1e37 = $77,017）
- HERMES→USDC ×N：冻在 1e45（≈1e9，code 203 字节冻结论价机）= 埋雷
→ 解法：对每个市场尝试候选缩放 [18,20,24,30,36,37,42,45]，选与现货最吻合的档
  （偏离 <10%）；无档吻合且 raw≥1e40 = BROKEN_ORACLE（冻结论价机，埋雷候选）

数据源（全部免 key，实测可用）：
- Morpho GraphQL：https://blue-api.morpho.org/graphql（markets 字段 chain{id}/lltv/oracle/
  collateralAsset/loanAsset/state{utilization supplyAssetsUsd borrowAssetsUsd}；
  ⚠️ chainId 不是合法参数，chain 才是）
- Base RPC：https://base-rpc.publicnode.com（eth_call price() selector 0xa035b1fe；
  ⚠️ 0x57e871e7 是错的会 revert）
- DeFiLlama coins API：https://coins.llama.fi/prices/current/base:{addr}

用法：
  python scripts/morpho_prey_radar.py            # 全表输出
  python scripts/morpho_prey_radar.py --quiet    # watchdog：仅偏离 ≥INFO / 冻结论价机才输出
  python scripts/morpho_prey_radar.py --chain 1  # 换链（默认 8453 Base）

输出：stdout 表 + JSONL 追加 data/prey_radar.jsonl
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = "http://127.0.0.1:7890"
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 25
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

GRAPHQL = "https://blue-api.morpho.org/graphql"
BASE_RPC = "https://base-rpc.publicnode.com"
PRICE_SEL = "0xa035b1fe"          # keccak("price()")[:4]，eth_utils 实测
SCALES = [18, 20, 24, 30, 33, 34, 36, 37, 42, 45]  # 实测覆盖：18 位币→1e24，9 位币→1e33，8 位币→1e34，比值预言机→1e36

INFO_BPS = 200                    # deviation ≥ 2% 信息级（抢跑者 -2% 进场）
SIGNAL_BPS = 500                  # deviation ≥ 5% 信号级（清算连环阈值）
FIT_TOL = 0.10                    # 缩放档吻合判定：oracle/scale 与现货偏离 <10%
DEDUP_HOURS = 24                  # 同信号去重窗口：24h 内不重复报警
DEV_CHANGE_PCT = 50               # 偏离变化 >50%（相对）才重报
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "prey_radar.jsonl"
STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "prey_radar_state.json"

MARKETS_QUERY = """{ markets(first: 200, orderBy: SupplyAssetsUsd, orderDirection: Desc) {
    items { marketId chain { id } listed lltv oracle { address }
            collateralAsset { symbol address } loanAsset { symbol address }
            state { utilization supplyAssetsUsd borrowAssetsUsd } } } }"""
WETH_BASE = "0x4200000000000000000000000000000000000006"


def gql_markets(chain_id: int) -> list:
    """返回全部市场（含 listed=false 的已下架/死市场——埋雷高发区，如 HERMES 冻结论价机）。"""
    r = requests.post(GRAPHQL, json={"query": MARKETS_QUERY},
                      headers={"Content-Type": "application/json", "Accept": "application/json",
                               "User-Agent": UA}, proxies=PROXIES, timeout=TIMEOUT)
    d = r.json()
    if d.get("errors"):
        print(f"[!] GraphQL errors: {d['errors']}", file=sys.stderr)
        return []
    return [m for m in d["data"]["markets"]["items"] if m["chain"]["id"] == chain_id]


def oracle_price_raw(oracle_addr: str):
    """eth_call oracle.price() → 原始 int；revert/异常返回 None。"""
    rpc = {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
           "params": [{"to": oracle_addr, "data": PRICE_SEL}, "latest"]}
    try:
        res = requests.post(BASE_RPC, json=rpc, timeout=TIMEOUT,
                            headers={"Content-Type": "application/json"}).json()
        raw = res.get("result")
        if raw and len(raw) > 2:
            return int(raw, 16)
    except Exception:
        pass
    return None


def spot_price(addr: str):
    """DeFiLlama 现货价，失败重试一次。"""
    for _ in range(2):
        try:
            r = requests.get(f"https://coins.llama.fi/prices/current/base:{addr}", timeout=TIMEOUT,
                             headers={"User-Agent": UA}, proxies=PROXIES)
            coins = r.json().get("coins", {})
            for v in coins.values():
                if v.get("price"):
                    return v["price"]
        except Exception:
            pass
    return None


def resolve_oracle_usd(raw, spot):
    """自动探测缩放档：raw/10^s ≈ spot 则返回 (usd_price, scale)；否则 (None, None)。"""
    if not raw or raw <= 0 or not spot or spot <= 0:
        return None, None
    best = None
    for s in SCALES:
        v = raw / (10 ** s)
        if v <= 0:
            continue
        dev = abs(v - spot) / spot
        if dev < FIT_TOL:
            if best is None or dev < best[0]:
                best = (dev, v, s)
    if best:
        return best[1], best[2]
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", type=int, default=8453, help="链 id（默认 8453 Base）")
    ap.add_argument("--quiet", action="store_true", help="watchdog：仅偏离 ≥INFO / 冻结论价机才输出")
    args = ap.parse_args()

    markets = gql_markets(args.chain)
    if not markets:
        print("[!] 无市场数据", file=sys.stderr)
        return 1

    rows = []
    weth_spot = spot_price(WETH_BASE) if any((m.get("loanAsset") or {}).get("symbol") == "WETH" for m in markets) else None
    for m in markets:
        st = m.get("state") or {}
        col = m.get("collateralAsset") or {}
        loan = m.get("loanAsset") or {}
        symbol_col = col.get("symbol") or "?"
        symbol_loan = loan.get("symbol") or "?"
        if not (col.get("address") and loan.get("address")):
            rows.append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         "chain": args.chain, "listed": m["listed"],
                         "collateral": symbol_col, "loan": symbol_loan,
                         "lltv": int(m["lltv"]) / 1e18 if m.get("lltv") else None,
                         "util": st.get("utilization"),
                         "supply_usd": st.get("supplyAssetsUsd"), "borrow_usd": st.get("borrowAssetsUsd"),
                         "oracle_raw": None, "oracle_usd": None, "scale": None,
                         "spot_usd": None, "dev_bps": None, "level": "no_meta"})
            continue
        oracle_addr = (m.get("oracle") or {}).get("address")
        if not oracle_addr:
            rows.append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         "chain": args.chain, "listed": m["listed"],
                         "collateral": symbol_col, "loan": symbol_loan,
                         "lltv": int(m["lltv"]) / 1e18, "util": st.get("utilization"),
                         "supply_usd": st.get("supplyAssetsUsd"), "borrow_usd": st.get("borrowAssetsUsd"),
                         "oracle_raw": None, "oracle_usd": None, "scale": None,
                         "spot_usd": None, "dev_bps": None, "level": "no_oracle"})
            continue
        raw = oracle_price_raw(oracle_addr)
        spot = spot_price(col["address"])
        lltv = int(m["lltv"]) / 1e18
        oracle_usd, scale = resolve_oracle_usd(raw, spot)
        # WETH 报价市场（wstETH→WETH / cbETH→WETH）：oracle 36 位小数 = 相对比率，
        # oracle_usd = 比率 × WETH 现货（DeFiLlama 常缺 base:cbETH/wstETH 价）
        if oracle_usd is None and symbol_loan == "WETH" and raw and weth_spot:
            ratio = raw / 1e36
            if 0.01 < ratio < 100:
                oracle_usd, scale = ratio * weth_spot, 36
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "chain": args.chain, "listed": m["listed"],
            "collateral": symbol_col,
            "loan": symbol_loan,
            "lltv": lltv, "util": st.get("utilization"),
            "supply_usd": st.get("supplyAssetsUsd"), "borrow_usd": st.get("borrowAssetsUsd"),
            "oracle_raw": raw, "oracle_usd": oracle_usd, "scale": scale,
            "spot_usd": spot,
        }
        if oracle_usd is not None:
            deviation = abs(oracle_usd - spot) / oracle_usd
            rec["dev_bps"] = round(deviation * 10000, 1)
            rec["borrowable_usd"] = round(oracle_usd * lltv, 4)
            rec["level"] = ("SIGNAL" if deviation >= SIGNAL_BPS / 10000
                            else "INFO" if deviation >= INFO_BPS / 10000 else "ok")
        elif raw is not None and raw >= 10 ** 40:
            # 无缩放吻合 + raw 巨大 = 冻结论价机（HERMES 型：1e45≈1e9）
            rec["dev_bps"] = None
            rec["level"] = "BROKEN_ORACLE"
        elif raw is None:
            rec["dev_bps"] = None
            rec["level"] = "no_price"
        else:
            rec["dev_bps"] = None
            rec["level"] = "scale?"
        rows.append(rec)

    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with open(LOG_PATH, "a") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception:
        pass

    if args.quiet:
        hits = [r for r in rows if r["level"] in ("SIGNAL", "INFO", "BROKEN_ORACLE")]
        # 去重聚合：同 (collateral, loan, level) 合并（HERMES 型 24 市场同信号会刷屏），供给求和 + 计数
        agg = {}
        for r in sorted(hits, key=lambda x: -(x["dev_bps"] or 0)):
            k = (r["collateral"], r["loan"], r["level"])
            if k not in agg:
                agg[k] = dict(r)
                agg[k]["n"] = 1
            else:
                agg[k]["n"] += 1
                if r.get("supply_usd"):
                    agg[k]["supply_usd"] = (agg[k].get("supply_usd") or 0) + r["supply_usd"]
        # 状态去重：24h 内同信号不重报，偏离变化 >50% 才重报（防 HERMES 型常驻信号每 30min 刷屏）
        state = {}
        try:
            if STATE_PATH.exists():
                state = json.loads(STATE_PATH.read_text())
        except Exception:
            pass
        now = datetime.now(timezone.utc).timestamp()
        to_report = []
        for k, r in agg.items():
            key = f"{r['chain']}:{k[0]}->{k[1]}:{k[2]}"
            last = state.get(key)
            dev = r["dev_bps"] or 0
            changed = False
            if last:
                age_h = (now - last.get("ts", 0)) / 3600
                last_dev = last.get("dev_bps") or 0
                changed = (age_h >= DEDUP_HOURS) or (
                    dev and last_dev and abs(dev - last_dev) / max(last_dev, 1) * 100 >= DEV_CHANGE_PCT)
            if not last or changed:
                to_report.append((key, r))
                state[key] = {"ts": now, "dev_bps": dev}
        try:
            STATE_PATH.parent.mkdir(exist_ok=True)
            STATE_PATH.write_text(json.dumps(state))
        except Exception:
            pass
        for key, r in to_report:
            dev = f"{r['dev_bps']}bps" if r["dev_bps"] is not None else "-"
            dead = "💀下架" if not r["listed"] else ""
            ltv = f"{r['lltv']:.0%}" if r["lltv"] is not None else "-"
            utl = f"{r['util']:.0%}" if r["util"] is not None else "-"
            sup = f"${r['supply_usd']/1e6:.1f}M" if r["supply_usd"] else "?"
            n = f" ×{r['n']}" if r["n"] > 1 else ""
            print(f"🚨 [Morpho {r['chain']}] {r['collateral']}→{r['loan']} {r['level']}{dead}{n} "
                  f"偏离 {dev} oracle=${r['oracle_usd'] or 0:,.2f} spot=${r['spot_usd'] or 0:,.2f} "
                  f"lltv={ltv} util={utl} supply={sup}")
        return 0

    print(f"=== Morpho prey radar @ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC "
          f"(chain {args.chain}, {len(rows)} markets, 含下架) ===")
    print(f"{'抵押品':<10}{'借出':<7}{'LTV':>6}{'利用':>6}{'oracle$':>12}{'spot$':>12}{'偏离bps':>9}{'级别':>14}")
    for r in sorted(rows, key=lambda x: -(x["dev_bps"] or 0)):
        dev = f"{r['dev_bps']:.1f}" if r["dev_bps"] is not None else "-"
        o = f"{r['oracle_usd']:,.2f}" if r["oracle_usd"] else "-"
        s = f"{r['spot_usd']:,.2f}" if r["spot_usd"] else "-"
        ltv = f"{r['lltv']:.0%}" if r["lltv"] is not None else "-"
        utl = f"{r['util']:.0%}" if r["util"] is not None else "-"
        dead = "💀" if not r["listed"] else " "
        print(f"{r['collateral']:<10}{r['loan']:<7}{ltv:>6}{utl:>6}  {o:>12}{s:>12}{dev:>9}{r['level']:>13} {dead}")
    n_sig = sum(1 for r in rows if r["level"] == "SIGNAL")
    n_info = sum(1 for r in rows if r["level"] == "INFO")
    n_broken = sum(1 for r in rows if r["level"] == "BROKEN_ORACLE")
    print(f"\nSIGNAL {n_sig} / INFO {n_info} / BROKEN_ORACLE {n_broken} / "
          f"ok {sum(1 for r in rows if r['level']=='ok')} / 其他 {sum(1 for r in rows if r['level'] not in ('SIGNAL','INFO','BROKEN_ORACLE','ok'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
