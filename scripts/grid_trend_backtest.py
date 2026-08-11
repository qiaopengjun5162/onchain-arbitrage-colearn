#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格策略趋势市回测 v2 (grid_trend_backtest.py)
================================================
背景：X 推文「在金」vibe-coding 网格系统跑 4 交易所 6 账户，1 个月赚 1300U，
评论区点破「这一个月没啥波动，所以网格特别舒服」。
问题：网格策略的盈利是否依赖低波动震荡市？趋势月是不是稳定亏损？
方法：OKX BTC/USDT 1h 真实行情（数据缓存 data/），按月独立回测（网格区间用前
30 天极值，无未来函数），输出每月 PnL 与当月趋势/波动指标对照 + 手续费敏感性 +
宽窄区间对比 + 杠杆强平视角，验证幸存者偏差假设。
v2 变更：①数据缓存避免重复拉取 ②max_dd 改为占本金% ③手续费扫描 ④窄(×1.05)/
宽(×1.30)区间双跑。
用法：hermes venv python3 scripts/grid_trend_backtest.py
"""

import ccxt
import datetime as dt
import json
import math
import os
import statistics
import sys

# ---------------- 参数 ----------------
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
MONTHS_BACK = 14          # 14 个月（前 1 个月做区间 warmup）
GRID_LEVELS = 90          # 评论区问「区间内放 90 个网格吗」
NOTIONAL_PER_LEVEL = 100.0
FEES_BPS = [0, 2, 5, 8, 10]   # 手续费扫描（maker，bps）
DEFAULT_FEE_BPS = 8
RANGE_WIDTHS = {"narrow": 1.05, "wide": 1.30}
WARMUP_DAYS = 30
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
CACHE_CSV = os.path.join(DATA_DIR, "grid_btc_1h_cache.csv")

# ---------------- 数据（带缓存） ----------------
def fetch_ohlcv(symbol, timeframe, months):
    if os.path.exists(CACHE_CSV):
        rows = []
        for line in open(CACHE_CSV):
            p = line.strip().split(",")
            rows.append([int(p[0])] + [float(x) for x in p[1:]])
        print(f"[data] cache {CACHE_CSV}: {len(rows)} candles")
        return rows
    proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
    ex = ccxt.okx({"enableRateLimit": True, "timeout": 25000})
    try:
        ex.load_markets()
    except Exception:
        print("[data] direct failed, retry with proxy")
        ex = ccxt.okx({"enableRateLimit": True, "timeout": 25000, "proxies": proxies})
        ex.load_markets()
    since = ex.milliseconds() - months * 30 * 24 * 3600 * 1000
    all_rows = []
    while since < ex.milliseconds():
        batch = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=300)
        if not batch:
            break
        all_rows.extend(batch)
        if len(batch) < 300:
            break
        since = batch[-1][0] + 1
    seen, uniq = set(), []
    for r in all_rows:
        if r[0] not in seen:
            seen.add(r[0]); uniq.append(r)
    uniq.sort(key=lambda r: r[0])
    with open(CACHE_CSV, "w") as f:
        for r in uniq:
            f.write(",".join(str(x) for x in r) + "\n")
    print(f"[data] {symbol} {timeframe}: {len(uniq)} candles cached")
    return uniq

# ---------------- 网格模拟 ----------------
def run_grid_month(candles, grid_lo, grid_hi, levels, notional, fee_rate):
    """静态网格月度模拟（经典网格机制：L_i 买入 → L_{i+1} 卖出，赚一格价差）。
    返回 trades/realized/unrealized/net/inv_qty/max_dd_pct/exit_events。"""
    spacing = (grid_hi - grid_lo) / (levels - 1) if levels > 1 else 0
    levels_px = [grid_lo + i * spacing for i in range(levels)]
    holds = [0.0] * levels     # holds[i] = 在 L_i 买入、待 L_{i+1} 卖出的量
    buy_px = [0.0] * levels
    realized = 0.0
    inv_qty = 0.0
    inv_cost = 0.0
    trades = 0
    equity_peak = None
    max_dd_usd = 0.0
    exit_events = 0
    last_px = candles[0][1]

    for (ts, o, h, l, c, v) in candles:
        for i, px in enumerate(levels_px):
            if last_px > px and l <= px:          # 向下穿越 L_i -> 买入，待 L_{i+1} 卖
                if holds[i] == 0:
                    q = notional / px
                    holds[i] = q; buy_px[i] = px
                    inv_qty += q; inv_cost += notional
                    trades += 1
            elif last_px < px and h >= px and i > 0:  # 向上穿越 L_i -> 卖出 L_{i-1} 买入的货
                if holds[i - 1] > 0:
                    q = holds[i - 1]
                    realized += (px - buy_px[i - 1]) * q - 2 * notional * fee_rate
                    holds[i - 1] = 0.0
                    inv_qty -= q; inv_cost -= notional
                    trades += 1
        last_px = c
        if c < grid_lo or c > grid_hi:
            exit_events += 1
        equity = realized + inv_qty * c - inv_cost
        if equity_peak is None or equity > equity_peak:
            equity_peak = equity
        if equity_peak is not None:
            max_dd_usd = max(max_dd_usd, equity_peak - equity)
    unreal = inv_qty * last_px - inv_cost
    capital = notional * levels
    return {
        "trades": trades, "realized": realized, "unrealized": unreal,
        "net": realized + unreal, "inv_qty": inv_qty,
        "max_dd_pct": max_dd_usd / capital * 100, "exit_events": exit_events,
        "last_px": last_px,
    }

# ---------------- 月度特征 ----------------
def month_stats(mc):
    m_open, m_close = mc[0][1], mc[-1][4]
    m_ret = (m_close / m_open - 1) * 100
    amp = (max(r[2] for r in mc) - min(r[3] for r in mc)) / m_open * 100
    rets = [math.log(mc[i][4] / mc[i - 1][4]) for i in range(1, len(mc)) if mc[i - 1][4] > 0]
    vol = statistics.pstdev(rets) * math.sqrt(24 * 365) * 100 if rets else 0
    return m_ret, amp, vol

def main():
    candles = fetch_ohlcv(SYMBOL, TIMEFRAME, MONTHS_BACK)
    if len(candles) < 2000:
        print("[err] 数据不足"); sys.exit(1)

    months = {}
    for r in candles:
        months.setdefault(dt.datetime.utcfromtimestamp(r[0] / 1000).strftime("%Y-%m"), []).append(r)
    month_keys = sorted(months.keys())

    # 每个宽度配置独立跑全月序列
    for width_name, width in RANGE_WIDTHS.items():
        print(f"\n{'='*88}\n【区间宽度 {width_name} = 前30天极值×{width}】  {GRID_LEVELS} 档 × ${NOTIONAL_PER_LEVEL:.0f} "
              f"· maker费 {DEFAULT_FEE_BPS}bps\n{'='*88}")
        rows = []
        for mk in month_keys:
            mc = months[mk]
            month_start_ts = mc[0][0]
            warm = [r for r in candles if r[0] < month_start_ts]
            if len(warm) < 24 * WARMUP_DAYS:
                continue
            warm_c = [r[4] for r in warm[-24 * WARMUP_DAYS:]]
            lo = min(warm_c) / width
            hi = max(warm_c) * width
            res = run_grid_month(mc, lo, hi, GRID_LEVELS, NOTIONAL_PER_LEVEL, DEFAULT_FEE_BPS / 1e4)
            m_ret, amp, vol = month_stats(mc)
            rows.append({
                "month": mk, "ret": m_ret, "amp": amp, "vol": vol, **res,
                "grid_lo": lo, "grid_hi": hi,
            })
        # 表
        hdr = f"{'月份':<8}{'月涨跌%':>7}{'振幅%':>6}{'波动%':>6}{'成交':>5}{'已实现$':>9}{'浮亏$':>8}{'净收益$':>9}{'回撤%本金':>9}{'穿界':>5}"
        print(hdr); print("-" * len(hdr))
        for r in rows:
            print(f"{r['month']:<8}{r['ret']:>7.2f}{r['amp']:>6.1f}{r['vol']:>6.0f}{r['trades']:>5}"
                  f"{r['realized']:>9.2f}{r['unrealized']:>8.2f}{r['net']:>9.2f}{r['max_dd_pct']:>9.1f}{r['exit_events']:>5}")
        trend = [r for r in rows if abs(r["ret"]) >= 10]
        rng = [r for r in rows if abs(r["ret"]) < 10]
        for name, rs in (("趋势月(≥10%)", trend), ("震荡月(<10%)", rng)):
            if rs:
                print(f"  {name} n={len(rs)}: 净 {sum(r['net'] for r in rs):>9.2f}$ "
                      f"(已实现 {sum(r['realized'] for r in rs):.2f} + 浮亏 {sum(r['unrealized'] for r in rs):.2f}) "
                      f"平均回撤 {statistics.mean(r['max_dd_pct'] for r in rs):.1f}% 本金")
        # 负月 vs 非负月盈亏率
        down = [r for r in rows if r["ret"] < 0]
        nondown = [r for r in rows if r["ret"] >= 0]
        dlose = sum(1 for r in down if r["net"] < 0)
        nwin = sum(1 for r in nondown if r["net"] > 0)
        print(f"  [生存分析] 下跌月 {len(down)} 个，亏损 {dlose} 个（{dlose/len(down)*100:.0f}%）；"
              f"非下跌月 {len(nondown)} 个，盈利 {nwin} 个（{nwin/len(nondown)*100:.0f}%）")
        xs = [abs(r["ret"]) for r in rows]; ys = [r["net"] for r in rows]
        if len(rows) > 2 and statistics.pstdev(xs) > 0:
            corr = sum((x - statistics.mean(xs)) * (y - statistics.mean(ys)) for x, y in zip(xs, ys)) \
                   / (len(rows) * statistics.pstdev(xs) * statistics.pstdev(ys))
            print(f"  月净收益 vs |月涨跌| 相关系数: {corr:.3f}")

        # 手续费扫描（该宽度下全期合计）
        print("  --- 手续费敏感性（全期 13 个月合计） ---")
        for fb in FEES_BPS:
            tot_net = tot_real = 0.0
            for mk in month_keys:
                mc = months[mk]
                warm = [r for r in candles if r[0] < mc[0][0]]
                if len(warm) < 24 * WARMUP_DAYS:
                    continue
                wc = [r[4] for r in warm[-24 * WARMUP_DAYS:]]
                res = run_grid_month(mc, min(wc) / width, max(wc) * width,
                                     GRID_LEVELS, NOTIONAL_PER_LEVEL, fb / 1e4)
                tot_net += res["net"]; tot_real += res["realized"]
            print(f"    fee {fb:>2}bps: 净 {tot_net:>9.2f}$（已实现 {tot_real:.2f}$）")

        # 杠杆强平视角（用月度内最大回撤 vs 保证金；网格单边突破时会先打穿强平价再回来）
        cap = NOTIONAL_PER_LEVEL * GRID_LEVELS
        for lev in (1, 3, 10):
            margin_pct = 100.0 / lev
            blow = [r for r in rows if r["max_dd_pct"] >= margin_pct]
            tag = " — " + ", ".join(f"{r['month']}({r['max_dd_pct']:.1f}%)" for r in blow) if blow else ""
            print(f"  [爆仓] {lev}x（保证金=本金{100/lev:.0f}%）: {len(blow)}/{len(rows)} 月{tag}")

        if width_name == "narrow":   # 默认配置落盘 CSV
            with open(os.path.join(DATA_DIR, "grid_monthly_backtest.csv"), "w") as f:
                cols = ["month", "ret", "amp", "vol", "trades", "realized", "unrealized",
                        "net", "max_dd_pct", "exit_events", "grid_lo", "grid_hi"]
                f.write(",".join(cols) + "\n")
                for r in rows:
                    f.write(",".join(str(r[k]) for k in cols) + "\n")
            print(f"  [saved] {os.path.join(DATA_DIR, 'grid_monthly_backtest.csv')}")

    # 最差月明细存档
    with open(os.path.join(DATA_DIR, "grid_backtest_worst_month.json"), "w") as f:
        json.dump({"note": "v2 网格回测，详见 stdout/CSV", "params": {
            "symbol": SYMBOL, "levels": GRID_LEVELS, "notional_per_level": NOTIONAL_PER_LEVEL,
            "fee_bps": DEFAULT_FEE_BPS, "widths": RANGE_WIDTHS}}, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {CACHE_CSV} / data/grid_monthly_backtest.csv 下次直接读缓存")

if __name__ == "__main__":
    main()
