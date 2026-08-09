#!/usr/bin/env python3
"""TUT 价差窗口回测 · 分析（D6，2026-08-09）

假设（Paxon 2026-08-09 口述 + 记忆定稿）：
  插针/爆仓潮后「价差+爆仓量」两因子可预判窗口期长度 → 决定搬砖能否从容双边进场。

数据（data/tut_backtest/）：
  binance_1h.csv / bitget_1h.csv        全历史 1h
  binance_5m_{d}.csv / bitget_5m_{d}.csv  事件日 5m（细扫）
  binance_oi_{d}.csv                    币安 OI（5m，爆仓量代理①）
  binance_funding.csv / bitget_funding.csv  8h funding（诱盘判别）

输出（data/tut_backtest/）：
  windows_5m.csv        事件窗口明细（含全部因子）
  report_*.txt          统计摘要

用法：
  python analyze_tut_windows.py [--spread-th 0.02] [--min-window 10]
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "tut_backtest"


def load_5m_series() -> tuple[pd.DataFrame, pd.DataFrame]:
    """合并所有事件日 5m → (binance df, bitget df)。"""
    bns, bgs = [], []
    for p in sorted(DATA_DIR.glob("binance_5m_*.csv")):
        bns.append(pd.read_csv(p))
    for p in sorted(DATA_DIR.glob("bitget_5m_*.csv")):
        bgs.append(pd.read_csv(p))
    bn = pd.concat(bns).drop_duplicates("ts").sort_values("ts") if bns else pd.DataFrame()
    bg = pd.concat(bgs).drop_duplicates("ts").sort_values("ts") if bgs else pd.DataFrame()
    return bn, bg


def load_oi() -> pd.DataFrame:
    frames = []
    for p in sorted(DATA_DIR.glob("binance_oi_*.csv")):
        df = pd.read_csv(p)
        # 兼容两种 schema：新版 [ts, oi] / 旧版 [create_time, sum_open_interest, ...]
        if "oi" in df.columns:
            df = df[["ts", "oi"]]
        elif "sum_open_interest" in df.columns:
            df = df.rename(columns={"sum_open_interest": "oi"})[["ts", "oi"]]
        else:
            continue
        # ⚠️ ts 单位防御：pandas 3.0 曾把 OI 存成秒（bug），归一化到毫秒
        t = df["ts"].astype("int64")
        if t.max() < 10**11:
            df["ts"] = t * 1000
        frames.append(df)
    return pd.concat(frames).drop_duplicates("ts").sort_values("ts") if frames else pd.DataFrame()


def load_funding() -> tuple[pd.DataFrame, pd.DataFrame]:
    bn = pd.read_csv(DATA_DIR / "binance_funding.csv")
    bg = pd.read_csv(DATA_DIR / "bitget_funding.csv")
    return bn, bg


def detect_windows(spread: pd.Series, ts: pd.Series, th: float, cooldown_bars: int = 3):
    """找 |spread| > th 的连续窗口。返回 [(start_idx, end_idx, direction)]"""
    above = spread.abs() > th
    windows = []
    i = 0
    n = len(spread)
    while i < n:
        if above.iloc[i]:
            j = i
            last_above = i
            while j < n and (above.iloc[j] or j - last_above <= cooldown_bars):
                if above.iloc[j]:
                    last_above = j
                j += 1
            windows.append((i, last_above))
            i = j
        else:
            i += 1
    return windows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spread-th", type=float, default=0.02, help="窗口判定价差阈值（默认 2%）")
    ap.add_argument("--min-window", type=int, default=6, help="最短窗口（5m bar 数，默认 6=30min，匹配 TUT 半小时窗口）")
    args = ap.parse_args()

    print("== 载入 5m 数据 ==")
    bn, bg = load_5m_series()
    oi = load_oi()
    bn_f, bg_f = load_funding()
    print(f"binance 5m: {len(bn)} 行 | bitget 5m: {len(bg)} 行 | OI: {len(oi)} 行 | funding: {len(bn_f)}/{len(bg_f)}")

    if bn.empty or bg.empty:
        print("❌ 5m 数据为空——先跑 download_tut_data.py")
        return

    m = bn.merge(bg, on="ts", suffixes=("_bn", "_bg"))
    m["spread"] = (m["close_bn"] - m["close_bg"]) / m["close_bg"]
    # 合并 OI（前向填充）
    if not oi.empty:
        m = m.merge(oi, on="ts", how="left")
        m["oi"] = m["oi"].ffill()
    # funding 合并（每个 4h/8h 结算点前向填充到 5m 粒度）
    funding_factor = None
    if not bn_f.empty and not bg_f.empty:
        ff = bn_f.rename(columns={"fundingRate": "funding_bn"})
        ff2 = bg_f.rename(columns={"fundingRate": "funding_bg"})
        m = m.merge(ff, on="ts", how="left").merge(ff2, on="ts", how="left")
        m["funding_bn"] = m["funding_bn"].ffill()
        m["funding_bg"] = m["funding_bg"].ffill()
        m["funding_spread"] = (m["funding_bg"] - m["funding_bn"]).abs()
        funding_factor = True
        print(f"funding 因子已合并（bn {len(bn_f)} 条 / bg {len(bg_f)} 条）")

    windows = detect_windows(m["spread"], m["ts"], args.spread_th)
    print(f"粗窗口数（|spread|>{args.spread_th:.1%}）: {len(windows)}")

    # 因子提取
    rows = []
    for s, e in windows:
        seg = m.iloc[s:e + 1]
        if len(seg) < 3:
            continue
        dur_min = (seg["ts"].iloc[-1] - seg["ts"].iloc[0]) / 60000
        if dur_min < args.min_window * 5:
            continue
        # 窗口前 2h 基线
        pre = m.iloc[max(0, s - 24):s]
        oi_pre = pre["oi"].mean() if not pre.empty and pre["oi"].notna().any() else np.nan
        oi_min = seg["oi"].min() if seg["oi"].notna().any() else np.nan
        # funding 差（窗口启动时刻，诱盘判别）
        fs = seg["funding_spread"].iloc[0] if funding_factor and "funding_spread" in seg and seg["funding_spread"].notna().any() else np.nan
        # 插针量：窗口内最大 5m 成交量（两侧合计）
        vol_max = (seg["volume_bn"] + seg["volume_bg"]).max()
        vol_base = pre["volume_bn"].mean() + pre["volume_bg"].mean() if not pre.empty else np.nan
        # 窗口内价格路径
        px_bn0, px_bn1 = seg["close_bn"].iloc[0], seg["close_bn"].iloc[-1]
        px_bg0, px_bg1 = seg["close_bg"].iloc[0], seg["close_bg"].iloc[-1]
        rows.append({
            "start_ts": int(seg["ts"].iloc[0]),
            "end_ts": int(seg["ts"].iloc[-1]),
            "dur_min": round(dur_min, 1),
            "max_spread": round(seg["spread"].abs().max(), 4),
            "spread_at_start": round(abs(seg["spread"].iloc[0]), 4),
            "mean_spread": round(seg["spread"].abs().mean(), 4),
            "dir": "bn_premium" if seg["spread"].iloc[0] > 0 else "bg_premium",
            "oi_drop_pct": round((oi_pre - oi_min) / oi_pre * 100, 1) if pd.notna(oi_pre) and oi_pre > 0 else np.nan,
            "vol_spike_x": round(vol_max / vol_base, 1) if vol_base and vol_base > 0 else np.nan,
            "funding_spread": round(fs, 5) if pd.notna(fs) else np.nan,
            "bn_px_change": round((px_bn1 - px_bn0) / px_bn0 * 100, 2),
            "bg_px_change": round((px_bg1 - px_bg0) / px_bg0 * 100, 2),
            "both_fell": 1 if (px_bn1 < px_bn0 and px_bg1 < px_bg0) else 0,
            "diverged_further": 1 if seg["spread"].abs().iloc[-1] > seg["spread"].abs().iloc[0] else 0,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        print("❌ 无满足最短窗口的样本")
        return
    df = df.sort_values("start_ts")
    df.to_csv(DATA_DIR / "windows_5m.csv", index=False)
    print(f"✅ 有效窗口: {len(df)} 个 → windows_5m.csv")
    print(df[["start_ts", "dur_min", "max_spread", "dir", "oi_drop_pct", "vol_spike_x", "both_fell", "diverged_further"]].to_string(index=False))

    # ---- 统计：两因子 vs 窗口期 ----
    print("\n== 相关性（dur_min vs 因子）==")
    for col in ["max_spread", "oi_drop_pct", "vol_spike_x", "spread_at_start", "mean_spread", "funding_spread"]:
        sub = df[[col, "dur_min"]].dropna()
        if len(sub) >= 5:
            r = np.corrcoef(sub[col], sub["dur_min"])[0, 1]
            print(f"  {col:>15}: r={r:+.3f}  (n={len(sub)})")

    # 诱盘判别：funding 差 >0.5%/期 的窗口 vs 正常的窗口
    if df["funding_spread"].notna().sum() >= 8:
        print("\n== 诱盘判别：窗口启动时 funding 差（bg-bn）==")
        trap = df[df["funding_spread"] > 0.005]
        norm = df[df["funding_spread"] <= 0.005]
        if len(trap) >= 3 and len(norm) >= 3:
            print(f"  高 funding 差窗口（>0.5%/期）: n={len(trap)}, 窗口期中位 {trap['dur_min'].median():.0f}min, "
                  f"双边同跌 {trap['both_fell'].mean():.0%}")
            print(f"  正常 funding 窗口:             n={len(norm)}, 窗口期中位 {norm['dur_min'].median():.0f}min, "
                  f"双边同跌 {norm['both_fell'].mean():.0%}")

    print("\n== 窗口期分布 ==")
    print(df["dur_min"].describe().round(1).to_string())

    print("\n== 窗口期内双边价格 ==")
    print(f"  双边同跌占比: {df['both_fell'].mean():.1%}（Paxon 担心的『一起下跌』）")
    print(f"  价差继续扩大占比: {df['diverged_further'].mean():.1%}")
    print(f"  窗口内币安价格中位变动: {df['bn_px_change'].median():+.2f}%")

    # 分档：深价差 vs 浅价差 的窗口期
    print("\n== 分档：max_spread 中位数分组 → 窗口期 ==")
    med = df["max_spread"].median()
    shallow = df[df["max_spread"] <= med]
    deep = df[df["max_spread"] > med]
    print(f"  浅档（max_spread ≤ {med:.2%}）: 窗口期中位 {shallow['dur_min'].median():.0f}min, n={len(shallow)}")
    print(f"  深档（max_spread > {med:.2%}）: 窗口期中位 {deep['dur_min'].median():.0f}min, n={len(deep)}")

    if df["oi_drop_pct"].notna().sum() >= 5:
        print("\n== 分档：OI 骤降分组 → 窗口期 ==")
        med_oi = df["oi_drop_pct"].median()
        low = df[df["oi_drop_pct"] <= med_oi]
        high = df[df["oi_drop_pct"] > med_oi]
        print(f"  OI 降 ≤ {med_oi:.1f}%: 窗口期中位 {low['dur_min'].median():.0f}min, n={len(low)}")
        print(f"  OI 降 > {med_oi:.1f}%: 窗口期中位 {high['dur_min'].median():.0f}min, n={len(high)}")


if __name__ == "__main__":
    main()
