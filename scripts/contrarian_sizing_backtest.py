#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逆势加仓思想回测（contrarian_sizing_backtest.py）— 2026-08-23
================================================================
验证 CryptoPainter 帖「越接近历史最大回撤/极端，给越多资金」思想，
套用到我们自己的数据场景：跨池价差（corridor_series.csv, 2824 条真实快照）。

问题：D17/D18 已证明常驻价差「机会每天有但全卡在成本线下」。那如果把
「价差越大 → 仓位越重」（逆势加仓=越接近极端越下注）会不会改变结论？

对照三策略（同一样本）：
  A 恒定仓位：每笔固定名义 100（D17/D18 的基准）
  B 线性加仓：仓位 = 100 × (spread / p90)，价差越大越重
  C 门槛加仓：spread ≥ p90 才开 300，否则 100（「等极端再重注」）

口径：毛利 = spread_bps，成本 = 50bps（乐观双腿），每笔盈亏 = (spread - cost) × 名义 / 10000
  —— 与 D17/D18 完全同口径，可直接对比结论。

用法：python3 scripts/contrarian_sizing_backtest.py
"""
import csv
import statistics
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "corridor_series.csv"
COST_BPS = 50.0
BASE_SIZE = 100.0
P90 = 61.2   # 实测 p90（清洗后，剔除 >5000bps 损坏）
P50 = 34.2


def load_spreads():
    spreads = []
    for row in csv.DictReader(open(DATA)):
        try:
            s = float(row["spread_bps"])
        except (ValueError, KeyError):
            continue
        if abs(s) > 5000:   # D17 清洗规则：剔除报价损坏
            continue
        spreads.append(s)
    return spreads


def backtest(spreads, size_fn):
    """size_fn(spread) -> 名义仓位。返回 (总收益USD, 笔数, 胜率, 最大回撤)."""
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    wins = 0
    n = 0
    for s in spreads:
        size = size_fn(s)
        if size <= 0:
            continue
        pnl = (s - COST_BPS) * size / 10000.0
        equity += pnl
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
        if pnl > 0:
            wins += 1
        n += 1
    return equity, n, wins / n if n else 0, max_dd


def main():
    spreads = load_spreads()
    print(f"样本: {len(spreads)} 条快照（清洗后）| 成本 {COST_BPS:.0f}bps | p50={P50} p90={P90}")
    print()

    strategies = {
        "A 恒定仓位(基准)": lambda s: BASE_SIZE,
        "B 线性加仓(越极端越重)": lambda s: BASE_SIZE * min(3.0, max(0.5, s / P50)),
        "C 门槛加仓(≥p90才3x)": lambda s: BASE_SIZE * 3 if s >= P90 else BASE_SIZE,
    }

    results = []
    for name, fn in strategies.items():
        tot, n, wr, dd = backtest(spreads, fn)
        results.append((name, tot, n, wr, dd))
        print(f"{name:<22} 总盈亏 ${tot:>10,.0f} | 笔数 {n:>5} | 胜率 {wr*100:>5.1f}% | 最大回撤 ${dd:>10,.0f}")

    print()
    print("解读：")
    best = max(results, key=lambda r: r[1])
    print(f"  · 总盈亏排序: {' > '.join(f'{r[0].split()[0]}({r[1]:,.0f})' for r in sorted(results, key=lambda r: -r[1]))}")
    if best[1] <= 0:
        print("  · 三种仓位策略全为负 —— 加仓方式改变不了「常驻价差不可执行」结论，")
        print("    肉只在事件窗口（D17/D18 已证）。逆势加仓=在错误的地方加杠杆。")
    else:
        print(f"  · {best[0]} 最优，但需结合 D17/D18 的事件窗口结论判断是否幸存者偏差")

    # 加仓的代价：B/C 的总名义是 A 的几倍（风险暴露）
    tot_a = sum(BASE_SIZE for _ in spreads)
    tot_b = sum(BASE_SIZE * min(3.0, max(0.5, s / P50)) for s in spreads)
    tot_c = sum(BASE_SIZE * 3 if s >= P90 else BASE_SIZE for s in spreads)
    print(f"\n  风险暴露对比（总名义）: A={tot_a:,.0f} | B={tot_b:,.0f} (×{tot_b/tot_a:.2f}) | C={tot_c:,.0f} (×{tot_c/tot_a:.2f})")


if __name__ == "__main__":
    main()
