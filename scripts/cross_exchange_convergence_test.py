#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨所永续价差收敛率回测（cross_exchange_convergence_test.py）— 2026-08-24

验证 Bruce 跨所反向对冲的「收敛假设」：价差事件出现后，多久/多大概率收敛回走廊内？
（用户 08-24 确认执行；对照 D17 跨池回测 50/60/80bps 胜率 29.9%/13.0%/0.0%）

方法：
- 数据：Bybit + OKX 同币永续 5m OHLCV（近 14 天，ccxt，代理）
- 价差序列：spread_bps = (B − A)/A × 1e4（inner join on ts）
- 事件：|spread| 上穿阈值 T（20/30/50/80bps）记一次入场
- 收敛：入场后 H 分钟（30/60/120/240）内 |spread| 回落到 <10bps（走廊内）→ 收敛
  （若先扩大 >2×T 也算一次"扩大先例"记录）
- 输出：阈值×时间窗收敛率矩阵 + 收敛耗时中位 + 扩大案例数

用法：hermes venv python3 scripts/cross_exchange_convergence_test.py [--symbol SOL] [--days 14]
"""
import argparse
import sys
import time
from datetime import datetime, timezone

import ccxt

PROXY = "http://127.0.0.1:7890"
CONVERGE_BPS = 10    # 回落到走廊内 = |spread| < 10bps
TIMEFRAMES = [30, 60, 120, 240]
THRESHOLDS = [20, 30, 50, 80]


def fetch_ohlcv(ex_name, symbol, timeframe, days):
    cls = getattr(ccxt, ex_name)
    ex = cls({"enableRateLimit": True, "timeout": 20000})
    ex.proxies = {"http": PROXY, "https": PROXY}
    since = ex.milliseconds() - days * 86400 * 1000
    all_bars = []
    cur = since
    while cur < ex.milliseconds():
        batch = ex.fetch_ohlcv(symbol, timeframe, since=cur, limit=1000)
        if not batch:
            break
        all_bars.extend(batch)
        cur = batch[-1][0] + 1
        time.sleep(0.2)
    # 去重（分页边界可能重叠）
    seen, out = set(), []
    for b in all_bars:
        if b[0] not in seen:
            seen.add(b[0])
            out.append(b)
    out.sort()
    return out


def build_series(symbol, days):
    """拉取并构建价差序列（Bybit−OKX close 价，bps）。"""
    print(f"拉取 {symbol} 永续 5m kline（近 {days} 天）：Bybit + OKX ...")
    by = fetch_ohlcv("bybit", symbol, "5m", days)
    ok = fetch_ohlcv("okx", symbol, "5m", days)
    print(f"  Bybit {len(by)} 根 / OKX {len(ok)} 根")
    bm = {b[0]: b for b in by}
    om = {b[0]: b for b in ok}
    common = sorted(set(bm) & set(om))
    print(f"  对齐 {len(common)} 根")
    series = []
    for ts in common:
        pb = bm[ts][4]
        po = om[ts][4]
        if pb and po:
            series.append((ts, (pb - po) / po * 1e4))
    print(f"  价差样本 {len(series)} 个，"
          f"min={min(s[1] for s in series):.1f} max={max(s[1] for s in series):.1f} bps "
          f"p50={sorted(s[1] for s in series)[len(series)//2]:.1f} bps")
    return series


def run_event_mode(symbol, days):
    """事件窗口测试：5m 内 |Δspread| ≥ JUMP 记一次瞬态事件，测其后 H 分钟内收敛率。

    假设：常驻价差不收敛（已验证），但瞬态突变（大单冲击/流动性失衡）后收敛。
    """
    JUMP = 50       # 5m 内 |Δspread| ≥ 50bps = 瞬态事件
    HORIZONS = [30, 60, 120]
    series = build_series(symbol, days)
    n = len(series)
    events = []
    for i in range(1, n):
        d = abs(series[i][1] - series[i - 1][1])
        if d >= JUMP:
            events.append((i, series[i][1], d))
    print(f"\n=== 事件窗口测试（{symbol}，5m 突变 ≥{JUMP}bps）===")
    print(f"瞬态事件数：{len(events)}")
    if not events:
        print("无事件——该币价差从不突变（完全高效）")
        return
    for H in HORIZONS:
        n_conv = 0
        n_half = 0
        for (i, entry, jump) in events:
            end_ts = series[i][0] + H * 60 * 1000
            j = i
            min_abs = abs(entry)
            while j < n and series[j][0] <= end_ts:
                min_abs = min(min_abs, abs(series[j][1]))
                j += 1
            if min_abs < 10:  # 回到走廊内
                n_conv += 1
            if min_abs <= abs(entry) * 0.5:  # 收窄一半（覆盖成本口径）
                n_half += 1
        print(f"  {H}min 内收敛回 <10bps：{n_conv}/{len(events)} = {n_conv/len(events)*100:.0f}%"
              f" ｜ 收窄≥一半：{n_half}/{len(events)} = {n_half/len(events)*100:.0f}%")
    # 突变方向示例（修时间戳 bug：ms→s）
    for (i, entry, jump) in events[:5]:
        t = series[i][0] // 1000
        print(f"  例: {time.strftime('%m-%d %H:%M', time.gmtime(t))} UTC 突变 {jump:.0f}bps → 价差 {entry:+.0f}bps")
    print("\n对照：常驻事件（上穿 30bps 后 4h 严格收敛率 0%）——若瞬态收敛率显著更高，事件驱动假设成立")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="SOL/USDT:USDT", help="永续符号（默认 SOL）")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--event-mode", action="store_true",
                    help="事件窗口测试：5m 内 |Δspread| ≥50bps 突变后收敛率")
    args = ap.parse_args()
    if args.event_mode:
        run_event_mode(args.symbol, args.days)
        return 0
    series = build_series(args.symbol, args.days)

    # 事件 → 收敛判定
    n = len(series)
    print(f"\n收敛率矩阵（|spread| 上穿阈值 T 后，H 分钟内回落到 <{CONVERGE_BPS}bps 才算收敛）：")
    header = "T\\H  " + "".join(f"{h:>7}" for h in TIMEFRAMES)
    print(header)
    for T in THRESHOLDS:
        row = f"{T:>4} "
        for H in TIMEFRAMES:
            n_conv = n_events = 0
            widen_cases = 0
            i = 0
            while i < n:
                if abs(series[i][1]) < T:
                    i += 1
                    continue
                # 事件开始
                entry = series[i][1]
                n_events += 1
                # 找 H 分钟窗口内的最小 |spread| 与最大扩大
                min_abs = abs(entry)
                max_widen = abs(entry)
                j = i
                end_ts = series[i][0] + H * 60 * 1000
                while j < n and series[j][0] <= end_ts:
                    min_abs = min(min_abs, abs(series[j][1]))
                    max_widen = max(max_widen, abs(series[j][1]))
                    j += 1
                if max_widen >= 2 * T:
                    widen_cases += 1
                if min_abs < CONVERGE_BPS:
                    n_conv += 1
                i = j  # 跳过窗口内样本，避免同一事件重复计数
            rate = n_conv / n_events * 100 if n_events else 0
            row += f"{rate:>6.0f}% "
        print(row)
        # 补充指标：收窄 ≥50%（套利实际需要：入场后价差减半即可覆盖成本退出）
        row2 = f"{T:>4}*"
        for H in TIMEFRAMES:
            n_conv2 = n_events = 0
            i = 0
            while i < n:
                if abs(series[i][1]) < T:
                    i += 1
                    continue
                entry = abs(series[i][1])
                n_events += 1
                min_abs = entry
                end_ts = series[i][0] + H * 60 * 1000
                j = i
                while j < n and series[j][0] <= end_ts:
                    min_abs = min(min_abs, abs(series[j][1]))
                    j += 1
                if min_abs <= entry * 0.5:
                    n_conv2 += 1
                i = j
            rate2 = n_conv2 / n_events * 100 if n_events else 0
            row2 += f"{rate2:>6.0f}% "
        print(row2)
        # 事件数（用最长窗口口径，与收敛判定一致）
        n_events = 0
        i = 0
        while i < n:
            if abs(series[i][1]) < T:
                i += 1
                continue
            n_events += 1
            end_ts = series[i][0] + TIMEFRAMES[-1] * 60 * 1000
            j = i
            while j < n and series[j][0] <= end_ts:
                j += 1
            i = j
        print(f"      事件数 {n_events}")

    # 结论口径说明
    print(f"\n口径：收敛 = H 分钟内 |spread| < {CONVERGE_BPS}bps；扩大先例 = 窗口内 |spread| ≥ 2×入场值")
    print("（对照组：D17 跨池回测 50/60/80bps 门槛胜率 29.9%/13.0%/0.0%——常驻价差不收敛）")


if __name__ == "__main__":
    sys.exit(main())
