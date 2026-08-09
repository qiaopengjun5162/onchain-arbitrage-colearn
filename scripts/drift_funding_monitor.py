#!/usr/bin/env python3
"""Drift perp 链上 funding 哨兵：86 市场 funding rate + mark/oracle（只读）。

对应 notes/solana/README.md 研究线「perp: Drift」——与 CEX funding_sentinel_v2 形成链上对照：
- CEX funding（okx/bitget/kucoin/gate）已监控；Drift 是 Solana 链上最大 perp DEX
- funding 高 = 链上永续拥挤度（多头/空头成本），与 CEX 对照看跨市场资金流动

实现：driftpy（官方 Python SDK，2026-08-09 uv 装入 hermes venv）
数据：get_perp_market_accounts() → amm.last_funding_rate / last_mark_price_twap / last_oracle_price

用法：
    python scripts/drift_funding_monitor.py             # 单次
    python scripts/drift_funding_monitor.py --watch 3600
    python scripts/drift_funding_monitor.py --watchdog  # cron：静默，仅异常 funding 才报

依赖：hermes venv python3.11 + driftpy（uv pip install driftpy；注意会降级 solana-py 到 0.36.6）
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# 阈值（24h funding rate，百分比）
ALERT_FUNDING_PCT = 1.0   # |funding| >= 1%/24h 报警（极端拥挤；Drift 常规 <0.1%/24h）

# 过滤：预测市场/长尾小市场 funding 天然巨大，只报主流交易市场
MIN_USERS = 10           # 至少 10 个用户才算活跃市场
SKIP_PREDICTION = True   # 跳过预测市场（contract_type == Prediction）


def load_helius_key() -> str:
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return os.environ.get("HELIUS_API_KEY", "")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("HELIUS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("HELIUS_API_KEY", "")


async def collect(url: str) -> list:
    from driftpy.drift_client import DriftClient
    from solana.rpc.async_api import AsyncClient
    from solders.keypair import Keypair
    from driftpy.constants.numeric_constants import FUNDING_RATE_PRECISION

    conn = AsyncClient(url)
    try:
        dc = DriftClient(conn, Keypair(), "mainnet")
        await dc.subscribe()
        markets = dc.get_perp_market_accounts()

        rows = []
        for m in markets:
            if m is None:
                continue
            amm = m.amm
            # 跳过 Prelaunch/无效市场
            try:
                oracle_src = str(amm.oracle_source)
            except Exception:
                oracle_src = "?"
            if "Prelaunch" in oracle_src or (amm.last24h_avg_funding_rate == 0 and amm.last_mark_price_twap == 0):
                continue
            # name 是 ListContainer（list[int]），转字符串
            try:
                name_raw = list(m.name)  # 确保是 list[int]
                name = bytes(name_raw).decode("utf-8", errors="replace").rstrip("\x00 ").strip()
            except Exception:
                name = f"mkt{m.market_index}"
            # 过滤预测市场（名字含 BET/REPUBLICAN/DEMOCRATIC 等）
            if SKIP_PREDICTION and any(k in name.upper() for k in ["BET", "REPUBLICAN", "DEMOCRATIC", "TRUMP-WIN", "HARRIS", "ELECTION", "WIN"]):
                continue
            # 过滤小市场（用户少 = 流动性差，funding 无意义）
            if m.number_of_users < MIN_USERS:
                continue
            funding_per_period = amm.last24h_avg_funding_rate / FUNDING_RATE_PRECISION * 100  # %（24h 均值，1e9 精度）
            funding_pct = funding_per_period  # 已经是 24h 值
            mark = amm.last_mark_price_twap / 1e6
            hist = getattr(amm, "historical_oracle_data", None)
            oracle = getattr(hist, "last_oracle_price", 0) / 1e6 if hist else 0
            basis_pct = (mark - oracle) / oracle * 100 if oracle else 0
            rows.append({
                "market_index": m.market_index,
                "name": name,
                "funding_pct": round(funding_pct, 4),
                "mark": mark,
                "oracle": oracle,
                "basis_pct": round(basis_pct, 3),
                "volume24h": amm.volume24h,
                "n_users": m.number_of_users,
            })
        return rows
    finally:
        await conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--watchdog", action="store_true")
    args = ap.parse_args()

    key = load_helius_key()
    if not key:
        print("ERROR: 未找到 HELIUS_API_KEY", file=sys.stderr)
        return 1
    url = f"https://mainnet.helius-rpc.com/?api-key={key}"

    def tick():
        rows = asyncio.run(collect(url))
        rows.sort(key=lambda r: -abs(r["funding_pct"]))
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 报警：|funding| 超阈值
        alerts = [r for r in rows if abs(r["funding_pct"]) >= ALERT_FUNDING_PCT]

        if args.watchdog:
            if alerts:
                lines = "，".join(f"{r['name']} {r['funding_pct']:+.3f}%/24h" for r in alerts[:5])
                print(f"⚠️ Drift funding 异常 @ {ts}：{lines}")
            return 0

        print(f"\n=== Drift Perp funding @ {ts} ===")
        print(f"活跃市场: {len(rows)} | 报警阈值: ±{ALERT_FUNDING_PCT}%/24h")
        print(f"\n{'mkt':<5}{'币种':<8}{'funding%/24h':>13}{'mark$':>10}{'oracle$':>10}{'basis%':>8}{'用户':>6}")
        for r in rows[:20]:
            mark = " ★" if abs(r["funding_pct"]) >= ALERT_FUNDING_PCT else ""
            print(f"{r['market_index']:<5}{r['name']:<8}{r['funding_pct']:>12.4f}{r['mark']:>10.2f}"
                  f"{r['oracle']:>10.2f}{r['basis_pct']:>8.3f}{r['n_users']:>6}{mark}")
        if not alerts:
            print(f"\n无 |funding| ≥ {ALERT_FUNDING_PCT}%/24h 的市场（链上永续平静）")
        else:
            print(f"\n⚠️ {len(alerts)} 个市场 funding 异常（对照 CEX funding_sentinel 看跨市场资金流动）")
        return 0

    code = tick()
    if args.watch and not args.watchdog:
        import time
        while True:
            time.sleep(args.watch)
            tick()
    return code


if __name__ == "__main__":
    sys.exit(main())
