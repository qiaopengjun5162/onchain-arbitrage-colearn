#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Morpho prey radar v2（高频偏离轮询原型）— 2026-08-26 结营后清算事件线第一步

v1（30min cron 全市场扫描）的瓶颈实测：200 市场串行 eth_call + DeFiLlama ≈ 720s+，
无法支撑高频。v2 设计（全部实测验证）：
- watchlist：启动时 GraphQL 拉 top-N 活跃市场（默认 12，按 supply 排序，listed=true）
- 每 tick：1 次 JSON-RPC 批量 eth_call（publicnode 支持批量，实测 2.2s）拿全部 oracle price()
           + 1 次 DeFiLlama 批量多币种（实测 4 币 1.9s）拿全部现货（SPOT_TTL 缓存 5s）
- 有效节奏 ≈ RPC 往返 ≈ 2-3s（公共 RPC 极限；Flashblocks WS 节点到位后才 <200ms）
- 信号链（08-25 daily 修正）：不监听预言机交易 → 高频轮询偏离。
  偏离突变（dev_delta 跳变）= 现货动了而预言机没跟 = 预言机即将更新 = 清算窗口临近
- 方向语义：dev_bps = (oracle_usd − spot) / oracle_usd，**正值 = oracle 高估 = 危险方向**
  （预言机下修 → 抵押品贬值 → HF 跌破 1 → 清算连环；mGLO 型负值 = oracle 落后 = 偏安全）
- 日志降采样：变化才记（oracle raw 变化 / |dev_delta|≥1bps / level 变化）+ 60s 心跳，
  避免 1s×N 市场全量写盘（一天 130 万行）

用法：
  python scripts/morpho_prey_radar_v2.py --once          # 单次快照（验证/巡检）
  python scripts/morpho_prey_radar_v2.py --duration 300  # 跑 5 分钟高频采样（cron watchdog）
  python scripts/morpho_prey_radar_v2.py --quiet         # 仅报警：偏离≥INFO/SIGNAL/突变/oracle更新
  python scripts/morpho_prey_radar_v2.py --watch 8 --interval 0.5 --jump-bps 30

输出：stdout 表 + data/prey_radar_v2.jsonl（降采样）+ data/prey_radar_v2_state.json（去重）
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = "http://127.0.0.1:7890"
PROXIES = {"http": PROXY, "https": PROXY}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
TIMEOUT = 20

GRAPHQL = "https://blue-api.morpho.org/graphql"
RPC = "https://base-rpc.publicnode.com"
PRICE_SEL = "0xa035b1fe"          # keccak("price()")[:4]（0x57e871e7 会 revert，v1 实测）
SCALES = [18, 20, 24, 30, 33, 34, 36, 37, 42, 45]
FIT_TOL = 0.10                    # 缩放档吻合：oracle/10^s 与现货偏离 <10%

INFO_BPS = 200                    # 偏离 ≥2% 信息级（抢跑者 -2% 进场）
SIGNAL_BPS = 500                  # 偏离 ≥5% 信号级（清算连环阈值）
JUMP_BPS = 20                     # 单 tick 偏离突变阈值（正常漂移 <2bps/tick）
DELTA_LOG_BPS = 1.0               # 偏离变化 ≥1bps 才落日志
SPOT_TTL = 5.0                    # 现货缓存秒数（现货比 oracle 连续，5s 足够）
HEARTBEAT_S = 60                  # 无变化时的心跳日志间隔
DEDUP_MIN = 10                    # 报警去重：同市场同级 10 分钟内不重报

DEFAULT_WATCH = 12
WETH_BASE = "0x4200000000000000000000000000000000000006"

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "data" / "prey_radar_v2.jsonl"
STATE_PATH = ROOT / "data" / "prey_radar_v2_state.json"

MARKETS_QUERY = """{ markets(first: 200, orderBy: SupplyAssetsUsd, orderDirection: Desc) {
    items { marketId chain { id } listed lltv oracle { address }
            collateralAsset { symbol address } loanAsset { symbol address }
            state { utilization supplyAssetsUsd borrowAssetsUsd } } } }"""


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def gql_markets(chain_id: int, watch: int, include_broken: bool):
    """GraphQL 拉市场 → watchlist：listed=true 按 supply 取 top-N；--include-broken 时附加冻结论价机市场。"""
    r = requests.post(GRAPHQL, json={"query": MARKETS_QUERY},
                      headers={"Content-Type": "application/json", "User-Agent": UA},
                      proxies=PROXIES, timeout=TIMEOUT)
    d = r.json()
    if d.get("errors"):
        print(f"[!] GraphQL errors: {d['errors']}", file=sys.stderr)
        return []
    items = [m for m in d["data"]["markets"]["items"] if m["chain"]["id"] == chain_id]
    # 过滤无地址市场（GraphQL 偶发 collateral/loan 缺 address，v1 记为 no_meta 行）
    items = [m for m in items
             if (m.get("collateralAsset") or {}).get("address")
             and (m.get("loanAsset") or {}).get("address")
             and (m.get("oracle") or {}).get("address")]
    live = [m for m in items if m["listed"] and (m.get("state") or {}).get("supplyAssetsUsd")]
    live.sort(key=lambda m: -(m["state"]["supplyAssetsUsd"] or 0))
    picked = live[:watch]
    if include_broken:
        # 冻结论价机市场（HERMES 型：raw≥1e40 且无缩放吻合）——预言机修正=清算连环
        for m in items:
            if not m["listed"] and m.get("oracle", {}).get("address"):
                picked.append(m)
    return picked


def batch_oracle_prices(markets):
    """1 次 JSON-RPC 批量 eth_call 拿全部 oracle price() raw。返回 {marketId: raw_or_None}。"""
    reqs = [{"jsonrpc": "2.0", "id": i, "method": "eth_call",
             "params": [{"to": m["oracle"]["address"], "data": PRICE_SEL}, "latest"]}
            for i, m in enumerate(markets)]
    out = {}
    try:
        res = requests.post(RPC, json=reqs, timeout=TIMEOUT,
                            headers={"Content-Type": "application/json", "User-Agent": UA},
                            proxies=PROXIES).json()
        if isinstance(res, list):
            for i, m in enumerate(markets):
                raw = None
                for item in res:
                    if item.get("id") == i and item.get("result"):
                        raw = int(item["result"], 16)
                        break
                out[m["marketId"]] = raw
    except Exception as e:
        print(f"[!] 批量 RPC 失败: {str(e)[:100]}", file=sys.stderr)
    return out


def batch_spot_prices(addresses, chunk=8):
    """DeFiLlama 批量多币种（实测 4 币 1.9s；⚠️ 单请求 >10 币返回空 → 分块，每块 ≤8）。"""
    out = {}
    for i in range(0, len(addresses), chunk):
        grp = list(dict.fromkeys(addresses))[i:i + chunk]
        keys = ",".join(f"base:{a.lower()}" for a in grp)
        try:
            r = requests.get(f"https://coins.llama.fi/prices/current/{keys}",
                             headers={"User-Agent": UA}, proxies=PROXIES, timeout=TIMEOUT)
            for k, v in r.json().get("coins", {}).items():
                if v.get("price"):
                    out[k.split(":")[1]] = v["price"]
        except Exception as e:
            print(f"[!] DeFiLlama 批量失败: {str(e)[:100]}", file=sys.stderr)
    return out


def resolve_oracle_usd(raw, spot, weth_spot, loan_symbol):
    """缩放档自动探测（v1 逻辑）+ WETH 比值预言机兜底。返回 (oracle_usd, scale)。"""
    if not raw or raw <= 0 or not spot or spot <= 0:
        # WETH 报价市场（wstETH→WETH/cbETH→WETH）：oracle 36 位 = 相对比率 × WETH 现货
        if loan_symbol == "WETH" and raw and weth_spot:
            ratio = raw / 1e36
            if 0.01 < ratio < 100:
                return ratio * weth_spot, 36
        return None, None
    best = None
    for s in SCALES:
        v = raw / (10 ** s)
        if v <= 0:
            continue
        dev = abs(v - spot) / spot
        if dev < FIT_TOL and (best is None or dev < best[0]):
            best = (dev, v, s)
    if best:
        return best[1], best[2]
    if loan_symbol == "WETH" and weth_spot:
        ratio = raw / 1e36
        if 0.01 < ratio < 100:
            return ratio * weth_spot, 36
    return None, None


def main():
    ap = argparse.ArgumentParser(description="Morpho prey radar v2 高频偏离轮询原型")
    ap.add_argument("--chain", type=int, default=8453)
    ap.add_argument("--watch", type=int, default=DEFAULT_WATCH, help="watchlist 市场数")
    ap.add_argument("--interval", type=float, default=1.0, help="目标轮询间隔秒")
    ap.add_argument("--spot-ttl", type=float, default=SPOT_TTL, help="现货缓存秒数")
    ap.add_argument("--jump-bps", type=int, default=JUMP_BPS, help="偏离突变阈值 bps/tick")
    ap.add_argument("--once", action="store_true", help="单次快照后退出")
    ap.add_argument("--duration", type=int, default=0, help="运行秒数后退出（0=无限）")
    ap.add_argument("--quiet", action="store_true", help="仅输出报警行")
    ap.add_argument("--include-broken", action="store_true", help="附加冻结论价机(下架)市场")
    args = ap.parse_args()

    markets = gql_markets(args.chain, args.watch, args.include_broken)
    if not markets:
        print("[!] watchlist 为空", file=sys.stderr)
        return 1

    # 预取现货集合：全部抵押品 + WETH（比值预言机需要）。⚠️ 统一小写——DeFiLlama key 是小写，
    # GraphQL 是 checksum 地址，不统一会 cache miss（实测 WETH 因天然小写才命中）
    spot_addrs = {m["collateralAsset"]["address"].lower() for m in markets} | {WETH_BASE}
    spot_cache = {}        # addr -> (ts, usd)
    last_sample = {}       # marketId -> 上一条记录（delta 计算 + 日志降采样）
    last_alert = {}        # key -> ts（报警去重）
    alert_state = {}       # 跨进程去重（v1 模式，24h 同信号不重报）
    try:
        if STATE_PATH.exists():
            alert_state = json.loads(STATE_PATH.read_text())
    except Exception:
        pass
    started = time.time()
    first_pass = True

    if not args.quiet and not args.once:
        print(f"=== prey radar v2 @ {utcnow()} UTC | chain {args.chain} | "
              f"watchlist {len(markets)} 市场 | 目标 {args.interval}s/tick ===")
        for m in markets:
            st = m.get("state") or {}
            print(f"  {m['collateralAsset']['symbol']:<9}→{m['loanAsset']['symbol']:<6} "
                  f"supply=${(st.get('supplyAssetsUsd') or 0)/1e6:.1f}M "
                  f"lltv={int(m['lltv'])/1e18:.0%}")

    while True:
        tick_t0 = time.time()
        raws = batch_oracle_prices(markets)
        # 现货缓存刷新
        now = time.time()
        stale = [a for a in spot_addrs if a not in spot_cache or now - spot_cache[a][0] >= args.spot_ttl]
        if stale:
            fresh = batch_spot_prices(stale)
            for a, p in fresh.items():
                spot_cache[a] = (now, p)
        # WETH 现货（比值预言机 + 全局备用）
        weth_spot = spot_cache.get(WETH_BASE, (0, None))[1]

        samples = []
        for m in markets:
            col = m["collateralAsset"]
            loan = m["loanAsset"]
            st = m.get("state") or {}
            raw = raws.get(m["marketId"])
            spot = spot_cache.get(col["address"].lower(), (0, None))[1]
            prev = last_sample.get(m["marketId"])
            oracle_usd, scale = resolve_oracle_usd(
                raw, spot, weth_spot, loan["symbol"]) if (raw or prev) else (None, None)

            rec = {
                "ts": utcnow(), "chain": args.chain, "market": m["marketId"][:10],
                "collateral": col["symbol"], "loan": loan["symbol"],
                "lltv": int(m["lltv"]) / 1e18, "util": st.get("utilization"),
                "supply_usd": st.get("supplyAssetsUsd"),
                "oracle_raw": raw, "oracle_usd": oracle_usd, "scale": scale,
                "spot_usd": spot,
            }
            oracle_updated = bool(prev and raw is not None and prev.get("oracle_raw") is not None
                                  and raw != prev["oracle_raw"])
            rec["oracle_updated"] = oracle_updated

            level = "no_price"
            dev = delta = None
            if oracle_usd is not None and spot:
                # 有符号偏离：正 = oracle 高估（危险方向），负 = oracle 落后（偏安全）
                dev = (oracle_usd - spot) / oracle_usd * 10000
                rec["dev_bps"] = round(dev, 1)
                if prev and prev.get("dev_bps") is not None:
                    delta = dev - prev["dev_bps"]
                    rec["dev_delta_bps"] = round(delta, 1)
                if dev >= SIGNAL_BPS:
                    level = "SIGNAL"
                elif dev >= INFO_BPS:
                    level = "INFO"
                elif oracle_updated:
                    level = "ORACLE_UPDATE"
                elif delta is not None and delta >= args.jump_bps:
                    level = "JUMP"
                else:
                    level = "ok"
            elif raw is not None and raw >= 10 ** 40:
                level = "BROKEN_ORACLE"
            elif raw is None:
                level = "no_price"
            else:
                level = "scale?"
            rec["level"] = level

            # 日志降采样：oracle 更新 / |delta|≥1bps / level 变化 / 心跳（60s）
            last_ts = last_sample.get(m["marketId"], {}).get("ts")
            changed = False
            if oracle_updated:
                changed = True
            elif delta is not None and abs(delta) >= DELTA_LOG_BPS:
                changed = True
            elif prev is None or prev.get("level") != level:
                changed = True
            elif last_ts:
                try:
                    last_dt = datetime.fromisoformat(last_ts)
                    changed = (datetime.now(timezone.utc) - last_dt).total_seconds() >= HEARTBEAT_S
                except Exception:
                    pass
            if changed:
                samples.append(rec)
            last_sample[m["marketId"]] = rec

        if samples:
            try:
                LOG_PATH.parent.mkdir(exist_ok=True)
                with open(LOG_PATH, "a") as f:
                    for r in samples:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[!] 写日志失败: {e}", file=sys.stderr)

        # 报警输出
        if args.quiet:
            hits = [r for r in samples if r["level"] in
                    ("SIGNAL", "INFO", "JUMP", "ORACLE_UPDATE", "BROKEN_ORACLE")]
            now_ts = time.time()
            for r in hits:
                key = f"{r['chain']}:{r['collateral']}->{r['loan']}:{r['level']}"
                # 跨进程去重：24h 同信号不重报
                st = alert_state.get(key)
                if st and now_ts - st.get("ts", 0) < 86400 and st.get("level") == r["level"]:
                    continue
                if key in last_alert and now_ts - last_alert[key] < DEDUP_MIN * 60:
                    continue
                last_alert[key] = now_ts
                alert_state[key] = {"ts": now_ts, "level": r["level"], "dev_bps": r.get("dev_bps")}
                dev = f"{r['dev_bps']}bps" if r.get("dev_bps") is not None else "-"
                dd = f"Δ{r['dev_delta_bps']:+.1f}bps" if r.get("dev_delta_bps") is not None else ""
                upd = " 🔄oracle更新" if r.get("oracle_updated") else ""
                print(f"🚨 [Morpho {r['chain']}] {r['collateral']}→{r['loan']} {r['level']} "
                      f"偏离 {dev}{dd}{upd} oracle=${r.get('oracle_usd') or 0:,.2f} "
                      f"spot=${r.get('spot_usd') or 0:,.2f}")
        elif not args.once and samples:
            for r in samples[-8:]:
                dev = f"{r['dev_bps']:.1f}" if r.get("dev_bps") is not None else "-"
                dd = f" Δ{r['dev_delta_bps']:+.1f}" if r.get("dev_delta_bps") is not None else ""
                print(f"  [{r['ts'][11:19]}] {r['collateral']:<9}→{r['loan']:<6} {r['level']:<14} "
                      f"{dev}bps{dd}", flush=True)

        if args.once:
            # 单次快照：全市场表格
            print(f"\n=== prey radar v2 单次快照 @ {utcnow()} UTC (chain {args.chain}, "
                  f"{len(markets)} 市场) ===")
            print(f"{'抵押品':<10}{'借出':<7}{'LTV':>6}{'偏离bps':>10}{'oracle$':>12}{'spot$':>12}"
                  f"{'级别':>14}")
            for r in sorted(samples, key=lambda x: -(x.get("dev_bps") or 0)):
                dev = f"{r['dev_bps']:.1f}" if r.get("dev_bps") is not None else "-"
                o = f"{r.get('oracle_usd') or 0:,.2f}"
                s = f"{r.get('spot_usd') or 0:,.2f}"
                print(f"{r['collateral']:<10}{r['loan']:<7}{r['lltv']:.0%}  {dev:>10}{o:>12}{s:>12}"
                      f"{r['level']:>13}")
            break

        if args.duration and time.time() - started >= args.duration:
            break

        # 节奏：目标 interval，但受 RPC 批量往返（~2.2s）约束
        elapsed = time.time() - tick_t0
        sleep = max(0.1, args.interval - elapsed)
        time.sleep(sleep)
        first_pass = False

    try:
        STATE_PATH.parent.mkdir(exist_ok=True)
        STATE_PATH.write_text(json.dumps(alert_state))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
