#!/usr/bin/env python3
"""期现套利成本模型：实时算「可套利空间」（只读）。

方法论（Paxon 2026-08-09 分享 + notes/basis-arb-hidden-blowup-and-amplitude-filter-20260809.md）：
- 期现套利（永续空 + 现货多）不是看到价差就进——「1倍杠杆统一账户也能爆」的机制
- 可套利空间 = 价差 - Σ(资金费率 + 手续费 + 提币费 + 滑点) - 安全缓冲
- 只有「空间 > 阈值」才值得进；否则就是裸入场等被收割

数据源（ccxt 走 Clash 代理）：
- 永续价 + funding 费率（swap ticker）
- 现货价（spot ticker）
- 手续费/提币费：各所近似常量（可配置）

用法：
  python basis_arb_model.py --once
  python basis_arb_model.py --symbols BTC,ETH,SOL
  python basis_arb_model.py --watch 3600

依赖：hermes venv python3.11（ccxt 4.5.71）
"""

import argparse
import csv
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
SYMBOLS = ["BTC", "ETH", "SOL", "DOGE", "XRP", "BNB"]

# 各所成本参数（近似常量，可调；taker 费率主流 VIP0）
EXCHANGES = {
    "okx": {"swap": "{sym}/USDT:USDT", "spot": "{sym}/USDT",
            "taker_bps": 10.0, "withdraw_bps": 10.0},
    "bitget": {"swap": "{sym}/USDT:USDT", "spot": "{sym}/USDT",
               "taker_bps": 10.0, "withdraw_bps": 10.0},
    "kucoin": {"swap": "{sym}/USDT:USDT", "spot": "{sym}/USDT",
               "taker_bps": 10.0, "withdraw_bps": 10.0},
    "gate": {"swap": "{sym}/USDT:USDT", "spot": "{sym}/USDT",
             "taker_bps": 10.0, "withdraw_bps": 20.0},
}

MIN_SPACE_BPS = 30       # 可套利空间 ≥30bps 才报（覆盖波动+安全缓冲）
PERSIST_WINDOW = 24      # 持续性检测窗口（小时）
PERSIST_MIN_RATIO = 0.4  # 窗口内「空间>阈值」占比 ≥40% 才算持续机会（防快照假象）
HOLD_HOURS = 8           # 持仓周期（funding 结算周期）
LOG_PATH = Path(__file__).parent.parent / "data" / "basis_arb_log.csv"


def build_exchange(name: str):
    cls = getattr(ccxt, name)
    ex = cls({"enableRateLimit": True, "timeout": 15000, "options": {"defaultType": "swap"}})
    if os.environ.get("NO_PROXY") != "1":
        ex.proxies = {"http": PROXY, "https": PROXY}
    return ex


def fetch_basis_model(ex, cfg: dict, sym: str) -> dict:
    """拉单所单币：价差 + funding + 成本 → 可套利空间（bps + 年化）。"""
    swap = cfg["swap"].format(sym=sym)
    spot = cfg["spot"].format(sym=sym)
    try:
        st = ex.fetch_ticker(swap)
        sp = ex.fetch_ticker(spot)
        swap_p = st.get("last")
        spot_p = sp.get("last")
        # funding 单独拉（ticker 不一定带 fundingRate）
        funding = None
        try:
            fr = ex.fetch_funding_rate(swap)
            funding = fr.get("fundingRate")
        except Exception:
            funding = st.get("fundingRate")
        if not swap_p or not spot_p:
            return {}
        # 价差（永续溢价现货，正 = 永续贵）
        basis_bps = (swap_p - spot_p) / spot_p * 10000
        # 资金费率成本：持有 8h 一次结算。做「永续空+现货多」时，正 funding = 空头付钱 = 成本
        funding_bps = (funding or 0) * 10000 if funding is not None else 0
        # 手续费：两腿 taker（永续开 + 现货买）
        fee_bps = cfg["taker_bps"] * 2
        # 提币费：跨所搬砖才需要；同所期现对冲不需要（设为 0，跨所场景手动加）
        withdraw_bps = 0.0
        # 滑点：薄币差异大，用固定近似
        slippage_bps = 5.0
        # 可套利空间（做多现货做空永续方向）：
        # 收益 = basis 收敛 + funding 收入（负 funding 时空头收钱）
        # 成本 = 两腿手续费 + 滑点 + 提币
        space_bps = basis_bps - funding_bps - fee_bps - slippage_bps - withdraw_bps
        # 年化（按 3 次/天复利近似：每 8h 一轮，单轮收益 = space_bps/10000）
        per_round = space_bps / 10000
        annual = (1 + per_round) ** (365 * 3) - 1 if per_round > 0 else 0
        return {
            "symbol": sym, "ex": "",  # ex 由调用方填
            "basis_bps": round(basis_bps, 2),
            "funding_bps": round(funding_bps, 2),
            "fee_bps": round(fee_bps, 2),
            "slippage_bps": slippage_bps,
            "space_bps": round(space_bps, 2),
            "annual_pct": round(annual * 100, 1),
        }
    except Exception:
        return {}


def fetch_persistence(ex, cfg: dict, sym: str, threshold_bps: float = MIN_SPACE_BPS) -> dict:
    """持续性检测：拉窗口内历史 klines，算「永续溢价现货 > 阈值」的占比。

    动机（notes/longtail-basis-test-snapshot-vs-persistence-20260809.md）：
    长尾币快照价差是剧烈摆动（MEW ±70bps），单点快照不可信。
    只有历史窗口内「价差持续 > 阈值」的占比高，才是真机会。
    """
    swap = cfg["swap"].format(sym=sym)
    spot = cfg["spot"].format(sym=sym)
    try:
        end = ex.milliseconds()
        start = end - PERSIST_WINDOW * 3600 * 1000
        sw = ex.fetch_ohlcv(swap, "1h", since=start, limit=PERSIST_WINDOW + 5)
        sp = ex.fetch_ohlcv(spot, "1h", since=start, limit=PERSIST_WINDOW + 5)
        if len(sw) < 6 or len(sp) < 6:
            return {}
        spot_by_t = {int(c[0]) // 3600000: c[4] for c in sp}
        basis_list = []
        for c in sw:
            h = int(c[0]) // 3600000
            if h in spot_by_t and spot_by_t[h]:
                basis_list.append((c[4] - spot_by_t[h]) / spot_by_t[h] * 10000)
        if len(basis_list) < 6:
            return {}
        over = sum(1 for b in basis_list if b > threshold_bps)
        ratio = over / len(basis_list)
        return {
            "persist_n": len(basis_list),
            "persist_over": over,
            "persist_ratio": round(ratio, 2),
            "basis_min": round(min(basis_list), 1),
            "basis_max": round(max(basis_list), 1),
            "basis_avg": round(sum(basis_list) / len(basis_list), 1),
        }
    except Exception:
        return {}


def collect(symbols: list) -> list:
    rows = []
    for ex_name, cfg in EXCHANGES.items():
        try:
            ex = build_exchange(ex_name)
            ex.load_markets()
        except Exception as e:
            print(f"  [!] {ex_name} 初始化失败: {str(e)[:60]}", file=sys.stderr)
            continue
        for sym in symbols:
            r = fetch_basis_model(ex, cfg, sym)
            if r:
                r["ex"] = ex_name
                # 持续性检测（防快照假象）：只对快照有正空间的跑
                if r["space_bps"] > 0:
                    p = fetch_persistence(ex, cfg, sym)
                    if p:
                        r.update(p)
                rows.append(r)
            time.sleep(0.2)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    args = ap.parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    def tick():
        rows = collect(symbols)
        # 按可套利空间排序
        rows.sort(key=lambda r: -r["space_bps"])
        # 信号 = 快照空间达标 AND 持续性达标（防快照假象）
        def is_signal(r):
            if r["space_bps"] < MIN_SPACE_BPS:
                return False
            if "persist_ratio" in r:
                return r["persist_ratio"] >= PERSIST_MIN_RATIO
            return False  # 快照正但持续性检测失败/无数据 → 不报
        signals = [r for r in rows if is_signal(r)]
        # 落盘
        if rows:
            new = not LOG_PATH.exists()
            with open(LOG_PATH, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["ts"])
                if new:
                    w.writeheader()
                for r in rows:
                    w.writerow({**r, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        # 输出
        if signals or not args.quiet:
            print(f"\n=== 期现套利空间 @ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC ===")
            print(f"{'币种':<6}{'所':<10}{'价差bps':>9}{'funding':>9}{'空间bps':>9}{'持续占比':>8}{'均值bps':>8}{'max':>7}")
            for r in rows[:15]:
                mark = " ★" if r in signals else ""
                pr = f"{r.get('persist_ratio', 0):.0%}" if "persist_ratio" in r else "-"
                pavg = f"{r.get('basis_avg', 0):.0f}" if "basis_avg" in r else "-"
                pmax = f"{r.get('basis_max', 0):.0f}" if "basis_max" in r else "-"
                print(f"{r['symbol']:<6}{r['ex']:<10}{r['basis_bps']:>9.1f}{r['funding_bps']:>9.1f}"
                      f"{r['space_bps']:>9.1f}{pr:>8}{pavg:>8}{pmax:>7}{mark}")
            if not signals:
                print(f"\n无持续机会（快照≥{MIN_SPACE_BPS}bps 且 历史占比≥{PERSIST_MIN_RATIO:.0%} 才报）")

    tick()
    if args.watch and not args.once:
        while True:
            time.sleep(args.watch)
            tick()


if __name__ == "__main__":
    sys.exit(main())
