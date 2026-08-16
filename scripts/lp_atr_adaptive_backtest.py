#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LP 区间宽度自适应 vs 固定半宽（lp_atr_adaptive_backtest.py）— D12 补充（2026-08-16）
====================================================================================
D11/D12 笔记「下一步」最后一项：动态区间宽度自适应（ATR/波动率定宽）vs 固定半宽。

核心问题：LP 回测里半宽是固定参数（±10%）。波动率自适应假设——高波动时放宽区间
（减少出区间+减少调仓），低波动时收窄区间（fee 更集中）。本脚本用 ATR% 动态计算
半宽（半宽 = k × ATR%），与固定 ±10% 对比，跑两个数据窗口（下跌段/牛市段）。

模型（与 lp_dynamic_range_backtest.py 完全一致，只改 half_w 来源）：
  - ATR% = 过去 N=24 根 K 线的平均真实波幅 / 价格（滚动）
  - half_w_t = min(max(k × ATR%_t, 2%), 30%)  # 限制范围，k 为缩放系数
  - 触发调仓阈值仍固定 5%（与 D11 对照），区间中心平移到现价

用法：
  python scripts/lp_atr_adaptive_backtest.py                       # 下跌段
  python scripts/lp_atr_adaptive_backtest.py --csv data/grid_btc_1h_bull_cache.csv --days 365  # 牛市段

依赖：hermes venv python3.11
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from lp_dynamic_range_backtest import (load_candles, simulate, INIT_NAV,
                                       FEE_RATE, SHARE, REBAL_COST_BPS, VOL_SCALE)

HALF_WIDTH_FIXED = 0.10     # 固定对照：±10%（D11 主参数）
TRIGGER_BPS = 500           # 触发阈值 5%（与 D11 最优一致）
ATR_N = 24                  # ATR 窗口（24h）
ATR_K = 1.0                 # 半宽 = k × ATR%（默认 1 倍）
ATR_MIN, ATR_MAX = 0.02, 0.30


def atr_series(candles, n=ATR_N):
    """滚动 ATR%（真实波幅均值 / 前收）。返回与 candles 等长的 half_w 序列（前 n 根用均值填充）。"""
    half_ws = []
    trs = []
    for i, k in enumerate(candles):
        if i == 0:
            tr = k["h"] - k["l"]
        else:
            prev_c = candles[i - 1]["c"]
            tr = max(k["h"] - k["l"], abs(k["h"] - prev_c), abs(k["l"] - prev_c))
        trs.append(tr / k["c"])  # 真实波幅百分比
        if i < n:
            half_ws.append(ATR_MIN)
        else:
            atr = sum(trs[i - n:i]) / n
            half_w = max(min(ATR_K * atr, ATR_MAX), ATR_MIN)
            half_ws.append(half_w)
    return half_ws


def simulate_adaptive(candles, half_ws, trigger_bps, fee_rate, share, rebal_cost_bps):
    """与 simulate() 同构，但 half_w 来自 ATR 序列（每根 K 线可能不同）。"""
    center = candles[0]["o"]
    lo, hi = center * (1 - half_ws[0]), center * (1 + half_ws[0])
    prev = candles[0]["o"]
    fee = 0.0
    rebal_cost = 0.0
    rebal_n = 0
    out_h = 0
    nav = INIT_NAV
    trigger = trigger_bps / 10000.0

    for i, k in enumerate(candles):
        price = k["c"]
        r = price / prev - 1.0
        prev = price
        in_range = lo <= price <= hi
        if in_range:
            fee += k["v"] * price * fee_rate * share * VOL_SCALE
            nav *= (1.0 + 0.5 * r)
        else:
            out_h += 1
            nav *= (1.0 + r)
        if abs(price - center) / center > trigger:
            cost = nav * rebal_cost_bps / 10000.0
            rebal_cost += cost
            rebal_n += 1
            center = price
            hw = half_ws[i]
            lo, hi = center * (1 - hw), center * (1 + hw)

    nav_end = nav + fee - rebal_cost
    return {
        "fee": fee, "rebal_cost": rebal_cost, "rebal_n": rebal_n,
        "out_h": out_h, "nav_end": nav_end,
        "pnl_pct": (nav_end / INIT_NAV - 1.0) * 100.0,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=str, help="自定义 K 线 CSV（默认下跌段）")
    ap.add_argument("--days", type=int, default=420, help="天数（年化换算）")
    ap.add_argument("--atr-k", type=float, default=ATR_K, help="ATR 缩放系数（半宽=k×ATR%）")
    args = ap.parse_args()

    candles = load_candles(args.csv)
    days = args.days
    base_half_ws = atr_series(candles)

    # 三线对比：固定 ±10% / ATR 自适应（k 扫描）/ 死守
    fixed = simulate(candles, HALF_WIDTH_FIXED, TRIGGER_BPS, FEE_RATE, SHARE, REBAL_COST_BPS)
    hold = {"pnl_pct": (candles[-1]["c"] / candles[0]["o"] - 1.0) * 100.0}

    def apr(p):
        return p / days * 365

    trend = "上涨" if candles[-1]["c"] > candles[0]["o"] else "下跌"
    pct = (candles[-1]["c"] / candles[0]["o"] - 1) * 100
    print(f"[data] {len(candles)} candles | {candles[0]['o']:,.0f} → {candles[-1]['c']:,.0f} "
          f"({pct:+.1f}% {trend}段) | {days} 天")
    print(f"[param] ATR N={ATR_N} | 触发 {TRIGGER_BPS/100:.1f}% | "
          f"固定半宽 ±{HALF_WIDTH_FIXED*100:.0f}% | VOL_SCALE {VOL_SCALE*100:.0f}%\n")

    print(f"{'策略':<24}{'fee收入':>10}{'调仓成本':>10}{'调仓次':>7}{'出区间h':>8}{'净收益%':>10}{'年化%':>9}")
    print(f"{'A. 固定 ±10%':<22}{fixed['fee']:>10,.0f}{fixed['rebal_cost']:>10,.0f}"
          f"{fixed['rebal_n']:>7}{fixed['out_h']:>8}{fixed['pnl_pct']:>10.1f}{apr(fixed['pnl_pct']):>9.1f}")
    print(f"{'C. 直接持有':<22}{'-':>10}{'-':>10}{'-':>7}{'-':>8}{hold['pnl_pct']:>10.1f}{apr(hold['pnl_pct']):>9.1f}")

    # ATR k 扫描（k=1.5 起步，避免 1.0 的过窄死区）
    print(f"\n=== ATR 自适应 k 扫描（半宽 = k × ATR%，夹在 ±2%~±30%）===")
    print(f"{'k':<6}{'平均半宽':>9}{'fee收入':>10}{'调仓成本':>10}{'调仓次':>7}{'出区间h':>8}{'净收益%':>10}")
    best = None
    for k in [1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]:
        half_ws = [max(min(k * hw, ATR_MAX), ATR_MIN) for hw in base_half_ws]
        ad = simulate_adaptive(candles, half_ws, TRIGGER_BPS, FEE_RATE, SHARE, REBAL_COST_BPS)
        avg_hw = sum(half_ws) / len(half_ws)
        print(f"{k:<6}{avg_hw*100:>8.1f}%{ad['fee']:>10,.0f}{ad['rebal_cost']:>10,.0f}"
              f"{ad['rebal_n']:>7}{ad['out_h']:>8}{ad['pnl_pct']:>10.1f}")
        if best is None or ad["pnl_pct"] > best[1]["pnl_pct"]:
            best = (k, ad)

    k_best, adaptive = best
    diff = adaptive["pnl_pct"] - fixed["pnl_pct"]
    print(f"\n=== 结论（{trend}段）===")
    print(f"最优 ATR k={k_best}（净 {adaptive['pnl_pct']:.1f}%） vs 固定 ±10%（净 {fixed['pnl_pct']:.1f}%）"
          f"→ 净差 {diff:+.1f}pct（自适应 {'胜' if diff > 0 else '负'}）")
    if diff > 0:
        print(f"  自适应调仓更少（{adaptive['rebal_n']} vs {fixed['rebal_n']}）、出区间更少"
              f"（{adaptive['out_h']}h vs {fixed['out_h']}h）→ 波动率定宽有效")
    else:
        print(f"  固定半宽更优 → ATR 定宽在本窗口不划算（宽窄切换的滞后/边界效应 > 收益）")


if __name__ == "__main__":
    main()
