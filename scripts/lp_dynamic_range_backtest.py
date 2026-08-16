#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LP 动态调区间回测 v1 (lp_dynamic_range_backtest.py)
====================================================
背景：notes/lp-dynamic-range.md 群讨论沉淀的核心问题——
「上涨行情中死守一个区间既踏空又停收 fee，动态调区间把被动 LP 变主动策略，
但每次调区间都是一笔真实交易（gas+滑点+swap 费），调太频繁 fee 被成本吃掉，
调太慢长期跑出区间颗粒无收」。

笔记留的可验证动作：「选一个池子，用历史价格序列回算：假如每偏离 X% 调一次区间，
累计调仓成本和手续费是多少，同期 fee 收入是多少」。

本脚本在 BTC/USDT 1h 真实行情上（data/grid_btc_1h_cache.csv，14 个月）模拟
一个 CLMM 集中流动性 LP，对比三条曲线：
  A. 死守宽区间（±w，从不调整）
  B. 动态调区间（价格偏离中心触发阈值 t 时，区间中心平移到现价，保持宽度 w）
  C. 直接持有（基准：无 LP 费，纯价格涨跌）

成本/收入模型（全部参数化，可扫）：
  - fee 收入：K 线价格在区间内时，volume_usd × fee_rate × 份额占比
  - 调仓成本：rebalance 时名义价值的比例成本（swap 手续费 + 滑点 + gas 摊销），
    每次调整把区间中心移到现价即付一次
  - 无常损失：区间内按 CLMM 线性持仓近似；出区间 = 单边资产（停收 fee）
  - 净收益 = 累计 fee − 累计调仓成本 + 期末持仓净值变化（含 IL）

用法：hermes venv python3 scripts/lp_dynamic_range_backtest.py
输出：每月对比表 + 触发阈值扫描 + 最优参数 + 结论
"""
import os
import sys
import math
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
CACHE_CSV = os.path.join(DATA_DIR, "grid_btc_1h_cache.csv")
# ---------------- 参数 ----------------
HALF_WIDTH = 0.10            # 区间半宽 ±10%（CLMM 集中流动性典型值）
FEE_RATE = 0.003             # 池子费率 0.30%（Raydium SOL-USDC 实测反推值）
SHARE = 0.001                # 我的流动性占池子份额 0.1%
REBAL_COST_BPS = 10          # 每次调仓成本：名义价值 10bps（swap 费+滑点+gas 摊销）
TRIGGERS_BPS = [50, 100, 200, 300, 500]  # 触发阈值扫描（偏离中心 %）
INIT_NAV = 100_000.0         # 初始投入名义价值（USD，统一各策略的净收益基准）
VOL_SCALE = 0.038            # ⚠️ 数据源是 OKX CEX 成交量，DEX 池按 ~3.8% 折算
                             # （2026-08-15 实测校准：wBTC 前3 DEX 池 24h $8.66M vs
                             # OKX BTC/USDT $227.6M = 3.8%；原假设 2% 偏保守）
BASE_PRICE = 100_000.0       # 归一化基准价（不依赖真实 BTC 价格水平）
DAYS = 420                   # 数据窗口天数（10080 根 1h）

def load_candles(csv_path=None):
    rows = []
    path = csv_path or CACHE_CSV
    for line in open(path):
        p = line.strip().split(",")
        rows.append({"ts": int(p[0]), "o": float(p[1]), "h": float(p[2]),
                     "l": float(p[3]), "c": float(p[4]), "v": float(p[5])})
    return rows

def simulate(candles, half_w, trigger_bps, fee_rate, share, rebal_cost_bps):
    """单次模拟。返回 {fee, rebal_cost, rebal_n, out_of_range_h, nav_end, pnl_pct}

    持仓模型（简化但自洽）：
      - 初始 nav=1（价格 p0 时投入，区间中心= p0，50/50 双币）
      - 每根 K 线：收盘价相对上一根涨跌 r
        · 价格在区间内 → delta ≈ 0.5（集中流动性中心半暴露），nav *= (1 + 0.5r)，收 fee
        · 价格出区间   → 单边资产，delta = 1.0，nav *= (1 + r)，不收 fee
      - 偏离中心超触发阈值 → 调仓：付成本 nav×cost_bps，区间中心移到现价
    """
    center = candles[0]["o"]
    lo, hi = center * (1 - half_w), center * (1 + half_w)
    prev = candles[0]["o"]
    fee = 0.0
    rebal_cost = 0.0
    rebal_n = 0
    out_h = 0
    nav = INIT_NAV
    trigger = trigger_bps / 10000.0

    for k in candles:
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
        # 触发调仓
        if abs(price - center) / center > trigger:
            cost = nav * rebal_cost_bps / 10000.0
            rebal_cost += cost
            rebal_n += 1
            center = price
            lo, hi = center * (1 - half_w), center * (1 + half_w)

    nav_end = nav + fee - rebal_cost
    return {
        "fee": fee, "rebal_cost": rebal_cost, "rebal_n": rebal_n,
        "out_h": out_h, "nav_end": nav_end,
        "pnl_pct": (nav_end / INIT_NAV - 1.0) * 100.0,
    }

def regime_analysis(candles):
    """按月切分，对比死守 vs 动态（5% 触发），验证「上涨段调区间更值」"""
    from collections import OrderedDict
    months = OrderedDict()
    for k in candles:
        m = datetime.fromtimestamp(k["ts"] / 1000, tz=timezone.utc).strftime("%Y-%m")
        months.setdefault(m, []).append(k)

    print(f"\n=== Regime 分段（按月，动态触发 5.0%，半宽 ±10%）===")
    print(f"{'月份':<10}{'涨跌%':>8}{'死守净%':>9}{'动态净%':>9}{'动态-死守':>10}{'fee倍数':>8}")
    results = []
    for m, mc in months.items():
        if len(mc) < 24:
            continue
        ret = (mc[-1]["c"] / mc[0]["o"] - 1) * 100
        a = simulate(mc, HALF_WIDTH, 10**9, FEE_RATE, SHARE, REBAL_COST_BPS)
        b = simulate(mc, HALF_WIDTH, 500, FEE_RATE, SHARE, REBAL_COST_BPS)
        diff = b["pnl_pct"] - a["pnl_pct"]
        fee_mult = b["fee"] / a["fee"] if a["fee"] > 0 else float("nan")
        results.append((m, ret, a, b))
        print(f"{m:<10}{ret:>8.1f}{a['pnl_pct']:>9.1f}{b['pnl_pct']:>9.1f}{diff:>10.1f}{fee_mult:>8.1f}")

    # 汇总：上涨月 vs 下跌月
    up = [r for r in results if r[1] > 0]
    down = [r for r in results if r[1] <= 0]
    def avg(xs, key):
        return sum(key(r) for r in xs) / len(xs) if xs else float("nan")
    print(f"\n上涨月({len(up)}个) 平均: 死守 {avg(up, lambda r: r[2]['pnl_pct']):.1f}% / "
          f"动态 {avg(up, lambda r: r[3]['pnl_pct']):.1f}% / 增益 {avg(up, lambda r: r[3]['pnl_pct']-r[2]['pnl_pct']):+.1f}pct")
    print(f"下跌月({len(down)}个) 平均: 死守 {avg(down, lambda r: r[2]['pnl_pct']):.1f}% / "
          f"动态 {avg(down, lambda r: r[3]['pnl_pct']):.1f}% / 增益 {avg(down, lambda r: r[3]['pnl_pct']-r[2]['pnl_pct']):+.1f}pct")

def halfwidth_sweep(candles):
    """半宽敏感性：区间越窄，死守越容易出区间，动态调区间的相对优势应越大"""
    print(f"\n=== 半宽敏感性（全程 420 天，动态触发 5.0%）===")
    print(f"{'半宽':<8}{'死守净%':>9}{'动态净%':>9}{'动态-死守':>10}{'死守出区间h':>12}{'fee倍数':>8}")
    for hw in [0.03, 0.05, 0.10, 0.20, 0.30]:
        a = simulate(candles, hw, 10**9, FEE_RATE, SHARE, REBAL_COST_BPS)
        b = simulate(candles, hw, 500, FEE_RATE, SHARE, REBAL_COST_BPS)
        diff = b["pnl_pct"] - a["pnl_pct"]
        fm = b["fee"] / a["fee"] if a["fee"] > 0 else float("nan")
        print(f"±{hw*100:>4.0f}%  {a['pnl_pct']:>9.1f}{b['pnl_pct']:>9.1f}{diff:>10.1f}{a['out_h']:>12}{fm:>8.1f}")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=str, help="自定义 K 线 CSV 路径（默认 data/grid_btc_1h_cache.csv）")
    ap.add_argument("--days", type=int, default=DAYS, help="数据窗口天数（用于年化换算）")
    args = ap.parse_args()
    candles = load_candles(args.csv)
    days = args.days if args.csv else DAYS

    # A. 死守（从不调仓 → trigger=∞）
    a = simulate(candles, HALF_WIDTH, 10**9, FEE_RATE, SHARE, REBAL_COST_BPS)
    # C. 直接持有：全程 delta=1.0，无 fee，基准同为 INIT_NAV
    c = {"pnl_pct": (candles[-1]["c"] / candles[0]["o"] - 1) * 100.0}

    def k(v):
        return f"{v/1000:,.1f}k"

    def apr(pnl_pct):
        return pnl_pct / days * 365

    print(f"[data] {len(candles)} candles | 区间 {candles[0]['o']:,.0f} → {candles[-1]['c']:,.0f} "
          f"({(candles[-1]['c']/candles[0]['o']-1)*100:+.1f}%) | {days} 天")
    print(f"[param] 半宽 ±{HALF_WIDTH*100:.0f}% | 费率 {FEE_RATE*100:.2f}% | 份额 {SHARE*100:.2f}% "
          f"| 调仓成本 {REBAL_COST_BPS}bps | DEX/CEX 量 {VOL_SCALE*100:.0f}%\n")

    # A. 死守（从不调仓 → trigger=∞）
    a = simulate(candles, HALF_WIDTH, 10**9, FEE_RATE, SHARE, REBAL_COST_BPS)
    # C. 直接持有：全程 delta=1.0，无 fee，基准同为 INIT_NAV
    c = {"pnl_pct": (candles[-1]["c"] / candles[0]["o"] - 1) * 100.0}

    print(f"{'策略':<22}{'fee收入':>10}{'调仓成本':>9}{'调仓次数':>7}{'出区间h':>7}{'净收益%':>9}{'年化%':>9}")
    print(f"{'A. 死守宽区间':<20}{k(a['fee']):>10}{k(a['rebal_cost']):>9}{a['rebal_n']:>7}{a['out_h']:>7}{a['pnl_pct']:>9.1f}{apr(a['pnl_pct']):>9.1f}")
    print(f"{'C. 直接持有':<20}{'-':>10}{'-':>9}{'-':>7}{'-':>7}{c['pnl_pct']:>9.1f}{apr(c['pnl_pct']):>9.1f}")
    print()

    # B. 触发阈值扫描
    print(f"{'触发阈值':<12}{'fee收入':>10}{'调仓成本':>9}{'调仓次数':>7}{'出区间h':>7}{'净收益%':>9}{'年化%':>9}")
    results = []
    for t in TRIGGERS_BPS:
        r = simulate(candles, HALF_WIDTH, t, FEE_RATE, SHARE, REBAL_COST_BPS)
        results.append((t, r))
        print(f"{t/100:>8.1f}%   {k(r['fee']):>10}{k(r['rebal_cost']):>9}{r['rebal_n']:>7}{r['out_h']:>7}{r['pnl_pct']:>9.1f}{apr(r['pnl_pct']):>9.1f}")

    # 最优
    best = max(results, key=lambda x: x[1]["pnl_pct"])
    print(f"\n🏆 最优触发: {best[0]/100:.1f}% (净 {best[1]['pnl_pct']:.2f}%)")
    print(f"   死守 vs 最优: 净差 {best[1]['pnl_pct'] - a['pnl_pct']:.2f}pct")
    print(f"   持有 vs 最优: 净差 {best[1]['pnl_pct'] - c['pnl_pct']:.2f}pct")
    print(f"   最优调仓成本占比: {best[1]['rebal_cost']/max(best[1]['fee'],1e-9)*100:.0f}% of fee")

    # 结论
    trend_desc = "上涨" if candles[-1]["c"] > candles[0]["o"] else "下跌"
    trend_pct = (candles[-1]["c"] / candles[0]["o"] - 1) * 100
    print(f"\n=== 结论（本数据窗口：BTC {trend_pct:+.1f}% {trend_desc}段，{days} 天）===")
    print(f"1. 动态调区间 vs 死守：最优({best[0]/100:.1f}%) 净 {best[1]['pnl_pct']:.1f}% "
          f"vs 死守 {a['pnl_pct']:.1f}% vs 持有 {c['pnl_pct']:.1f}%")
    print(f"2. fee 收入 {best[1]['fee']/1000:.1f}k vs 死守 {a['fee']/1000:.1f}k "
          f"= {best[1]['fee']/a['fee']:.1f}x —— 动态调区间全程在区间内收 fee（出区间 {best[1]['out_h']}h vs 死守 {a['out_h']}h）")
    print(f"3. 调仓成本占比：最优触发时 {best[1]['rebal_cost']/best[1]['fee']*100:.0f}% of fee；"
          f"触发越频繁成本占比越高（0.5% 触发时 {results[0][1]['rebal_cost']/results[0][1]['fee']*100:.0f}%，反噬）")
    print(f"4. 关键对比：{trend_desc}段动态调区间的相对价值——见 regime 分段（上涨月 vs 下跌月逐月拆解）")

    regime_analysis(candles)
    halfwidth_sweep(candles)

if __name__ == "__main__":
    main()
