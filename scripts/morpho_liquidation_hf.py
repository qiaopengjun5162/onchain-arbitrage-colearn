#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Morpho HF 清算触发价扫描器（morpho_liquidation_hf.py）— 2026-08-24

010 清算手册第 2 步落地：预言机节奏预测之后，算出「价格跌 X% → 触发 Y 规模清算」。
配合 prey_radar（预言机偏离扫描）组成完整清算哨兵：
- prey_radar：预言机 vs 现货错价（埋雷检测）
- 本脚本：持仓级 HF + 清算触发跌幅（priceVariationToLiquidationPrice）+ 临近清算规模

数据源（实测 2026-08-24）：
- Morpho GraphQL `marketPositions`：where { marketUniqueKey_in, healthFactor_lte, marketListed }
  → items { healthFactor priceVariationToLiquidationPrice user market state }
- MarketPositionState 字段名：collateralUsd / borrowAssetsUsd（不是 collateralValueUsd）
- priceVariationToLiquidationPrice：负数 = 价格需跌 |v|（如 -0.005 = 跌 0.5% 触发清算）
- 无 chainId 参数 → 用市场白名单过滤（本脚本拉 Base 活市场 marketId）

用法：
  python scripts/morpho_liquidation_hf.py                  # 全表（HF≤1.5，collateral≥$100K）
  python scripts/morpho_liquidation_hf.py --quiet          # watchdog：仅临近清算大仓（≥$1M 且触发跌幅≤2%）
  python scripts/morpho_liquidation_hf.py --max-hf 1.3 --min-collateral 1000000
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = "http://127.0.0.1:7890"
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 30
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
GRAPHQL = "https://blue-api.morpho.org/graphql"

DEFAULT_HF = 1.5          # 扫描 HF ≤ 1.5 的持仓
MIN_COLLATERAL = 100_000  # 过滤 dust：抵押品 ≥ $100K
WATCH_HF = 1.2            # watchdog：HF ≤ 1.2 才算临近
WATCH_COLLATERAL = 1_000_000  # watchdog：抵押品 ≥ $1M
WATCH_TRIGGER = 0.02      # watchdog：触发跌幅 ≤ 2% 才报
DEDUP_HOURS = 24          # 同 (user, market) 24h 去重
USDE_BASE = "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34"
DEPEG_ALERT = 0.995       # USDe 现货跌破 0.995 触发脱锚预警
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "morpho_hf.jsonl"
STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "morpho_hf_state.json"

MARKETS_QUERY = """{ markets(first: 200, orderBy: SupplyAssetsUsd, orderDirection: Desc) {
    items { marketId chain { id } listed collateralAsset { symbol } } } }"""


def gql(query):
    r = requests.post(GRAPHQL, json={"query": query},
                      headers={"Content-Type": "application/json", "Accept": "application/json",
                               "User-Agent": UA}, proxies=PROXIES, timeout=TIMEOUT)
    return r.json()


def base_market_keys():
    d = gql(MARKETS_QUERY)
    return [m["marketId"] for m in d["data"]["markets"]["items"]
            if m.get("chain", {}).get("id") == 8453 and m.get("listed")
            and (m.get("collateralAsset") or {}).get("symbol")]


def scan(keys, max_hf, min_collateral):
    q = """{ marketPositions(first: 200,
          where: { marketUniqueKey_in: %s, healthFactor_lte: %s, marketListed: true },
          orderBy: HealthFactor, orderDirection: Asc) {
        items { healthFactor priceVariationToLiquidationPrice
                user { address }
                market { marketId collateralAsset { symbol } loanAsset { symbol } }
                state { collateralUsd borrowAssetsUsd } } } }""" % (json.dumps(keys), max_hf)
    d = gql(q)
    if d.get("errors"):
        print(f"[!] GraphQL errors: {d['errors']}", file=sys.stderr)
        return []
    out = []
    for p in d["data"]["marketPositions"]["items"]:
        m = p["market"]
        st = p["state"]
        coll = st.get("collateralUsd") or 0
        borrow = st.get("borrowAssetsUsd") or 0
        if coll < min_collateral:
            continue
        pv = p.get("priceVariationToLiquidationPrice")
        trigger = -pv if isinstance(pv, (int, float)) and pv < 0 else pv
        out.append({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "market": f"{m['collateralAsset']['symbol']}→{m['loanAsset']['symbol']}",
            "hf": round(p["healthFactor"], 4),
            "trigger_drop_pct": round(trigger * 100, 2) if isinstance(trigger, (int, float)) and 0 < trigger < 100 else None,
            "collateral_usd": coll, "borrow_usd": borrow,
            "user": p["user"]["address"],
        })
    out.sort(key=lambda x: x["hf"])
    return out


def usde_spot():
    """USDe 现货价（DeFiLlama）。失败返回 None。"""
    try:
        r = requests.get(f"https://coins.llama.fi/prices/current/base:{USDE_BASE}",
                         headers={"User-Agent": UA}, proxies=PROXIES, timeout=15)
        coins = r.json().get("coins", {})
        return coins.get(f"base:{USDE_BASE}", {}).get("price")
    except Exception:
        return None


def depeg_ladder(rows):
    """USDe 触发阶梯：按触发跌幅排序的 (跌幅, 累计清算规模)。"""
    usde = [r for r in rows if r["market"] == "USDe→USDC"]
    out = []
    for r in sorted(usde, key=lambda x: x["trigger_drop_pct"] or 99):
        out.append((r["trigger_drop_pct"], r["collateral_usd"]))
    return out


def whale_trend(n=24):
    """鲸鱼仓 HF 趋势：读 morpho_hf.jsonl，提取大仓（collateral ≥ $10M）的 HF 时间序列。"""
    try:
        lines = LOG_PATH.read_text().splitlines()
    except Exception:
        return {}
    seen = {}
    for ln in lines[-2000:]:
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if (r.get("collateral_usd") or 0) < 10_000_000:
            continue
        key = f"{r['user'][:10]} {r['market']}"
        seen.setdefault(key, []).append((r["ts"], r["hf"], r["trigger_drop_pct"]))
    out = {}
    for k, v in seen.items():
        out[k] = v[-n:]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-hf", type=float, default=DEFAULT_HF)
    ap.add_argument("--min-collateral", type=float, default=MIN_COLLATERAL)
    ap.add_argument("--quiet", action="store_true", help="watchdog：仅临近清算大仓才输出")
    ap.add_argument("--whale-trend", type=int, default=0, metavar="N",
                    help="鲸鱼仓 HF 趋势：输出最近 N 次扫描（读 jsonl，不请求）")
    args = ap.parse_args()

    if args.whale_trend:
        trend = whale_trend(args.whale_trend)
        if not trend:
            print("暂无鲸鱼仓数据（等 cron 攒几轮）")
            return 0
        print(f"=== 鲸鱼仓 HF 趋势（collateral ≥ $10M，最近 {args.whale_trend} 次扫描）===")
        for k, v in sorted(trend.items(), key=lambda x: x[1][-1][1]):
            print(f"\n{k}:")
            for ts, hf, trig in v:
                t = ts[11:16] if len(ts) > 16 else ts
                tr = f"{trig}%" if trig is not None else "?"
                print(f"  {t} HF={hf:.3f} 触发跌幅 {tr}")
        return 0

    keys = base_market_keys()
    rows = scan(keys, args.max_hf, args.min_collateral)
    usde = usde_spot()
    depeg = usde is not None and usde < DEPEG_ALERT
    ladder = depeg_ladder(rows) if depeg else []

    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with open(LOG_PATH, "a") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception:
        pass

    if args.quiet:
        if depeg:
            total = sum(c for _, c in ladder) / 1e6
            print(f"⚠️ [USDe 脱锚] 现货 ${usde:.4f} < {DEPEG_ALERT}——清算触发阶梯（跌 {ladder[0][0]}% → ${ladder[0][1]/1e6:.1f}M 起，"
                  f"至 {ladder[-1][0]}% 累计 ${total:.0f}M）："
                  + " ".join(f"{p}%→${c/1e6:.1f}M" for p, c in ladder[:4]))
        hits = [r for r in rows if r["hf"] <= WATCH_HF
                and r["collateral_usd"] >= WATCH_COLLATERAL
                and (r["trigger_drop_pct"] is None or r["trigger_drop_pct"] <= WATCH_TRIGGER * 100)]
        # 24h 去重（USDe 型常驻风险仓会每 30min 命中，防刷屏）
        state = {}
        try:
            if STATE_PATH.exists():
                state = json.loads(STATE_PATH.read_text())
        except Exception:
            pass
        now = datetime.now(timezone.utc).timestamp()
        to_report = []
        for r in sorted(hits, key=lambda x: x["hf"]):
            key = f"{r['user']}:{r['market']}"
            last = state.get(key)
            changed = not last or (now - last.get("ts", 0)) / 3600 >= DEDUP_HOURS \
                or abs((last.get("hf") or 0) - r["hf"]) >= 0.005  # HF 明显变化也重报
            if changed:
                to_report.append(r)
                state[key] = {"ts": now, "hf": r["hf"]}
        try:
            STATE_PATH.parent.mkdir(exist_ok=True)
            STATE_PATH.write_text(json.dumps(state))
        except Exception:
            pass
        for r in to_report:
            trig = f"{r['trigger_drop_pct']}%" if r["trigger_drop_pct"] is not None else "?"
            print(f"🚨 [Morpho HF] {r['market']} HF={r['hf']:.3f} "
                  f"触发跌幅 {trig} | collateral=${r['collateral_usd']/1e6:.2f}M "
                  f"borrow=${r['borrow_usd']/1e6:.2f}M user={r['user'][:10]}..")
        return 0

    print(f"=== Morpho HF 清算触发扫描 @ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC "
          f"(HF≤{args.max_hf}, collateral≥${args.min_collateral/1e3:.0f}K) ===")
    if usde is not None:
        print(f"USDe 现货 ${usde:.4f}{' ⚠️ 已脱锚' if depeg else '（正常）'}")
    if depeg:
        total = sum(c for _, c in ladder) / 1e6
        print(f"⚠️ USDe 触发阶梯（现货已 ${usde:.4f}，相对现价再跌 {ladder[0][0]}% 触发 ${ladder[0][1]/1e6:.1f}M）："
              + " ".join(f"{p}%→${c/1e6:.1f}M" for p, c in ladder[:6])
              + (f" …… 至 {ladder[-1][0]}% 累计 ${total:.0f}M" if len(ladder) > 6 else ""))
    if not rows:
        print("无临近清算大仓")
        return 0
    print(f"{'市场':<18}{'HF':>8}{'触发跌幅':>9}{'抵押品':>12}{'借款':>12}{'用户':>14}")
    for r in rows:
        trig = f"{r['trigger_drop_pct']}%" if r["trigger_drop_pct"] is not None else "?"
        print(f"{r['market']:<18}{r['hf']:>8.3f}{trig:>9}"
              f"${r['collateral_usd']/1e6:>9.2f}M${r['borrow_usd']/1e6:>9.2f}M{r['user'][:12]:>14}")
    # 按市场汇总临近清算规模
    by_mkt = {}
    for r in rows:
        by_mkt.setdefault(r["market"], {"n": 0, "coll": 0, "borrow": 0})
        by_mkt[r["market"]]["n"] += 1
        by_mkt[r["market"]]["coll"] += r["collateral_usd"]
        by_mkt[r["market"]]["borrow"] += r["borrow_usd"]
    print("\n按市场汇总（临近清算总规模）:")
    for m, v in sorted(by_mkt.items(), key=lambda x: -x[1]["coll"]):
        print(f"  {m}: {v['n']} 仓 | collateral ${v['coll']/1e6:.2f}M | borrow ${v['borrow']/1e6:.2f}M")
    return 0


if __name__ == "__main__":
    sys.exit(main())
