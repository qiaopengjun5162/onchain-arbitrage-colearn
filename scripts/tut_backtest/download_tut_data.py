#!/usr/bin/env python3
"""TUT 价差窗口回测 · 数据下载（D6，2026-08-09）

目标：重建「币安 vs bitget」TUT 永续价差历史，为两因子回测（价差+爆仓量 → 窗口期）供数。

数据源（实测可用性，2026-08-09 探测）：
- 币安 1h/5m kline：data.binance.vision 月/日 zip（不受地区限制）；当日用 fapi API（需代理 127.0.0.1:7890）
- 币安 funding：fapi /fapi/v1/fundingRate（分页）
- 币安 OI（爆仓量代理）：data.binance.vision metrics 日文件（5m 分辨率，含 sum_open_interest）
- bitget 1h/5m kline + funding：ccxt 分页（hermes venv，ccxt 4.5.71）
- 爆仓量：无公开历史（OKX TUT 无 index；binance vision liquidationSnapshot 404）
  → 用两个代理：① OI 骤降量（metrics）② 插针 1m/5m 成交量（kline）

用法：
  python download_tut_data.py                    # 全量：1h 全历史 + funding + 事件日 5m/OI（自动）
  python download_tut_data.py --resume           # 跳过已存在的文件
输出：data/tut_backtest/{binance,bitget}_1h.csv, _funding.csv, events 日 5m/OI csv

依赖：hermes venv python3.11（ccxt 4.5.71 + pandas）
"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import pandas as pd

PROXY = "http://127.0.0.1:7890"
SYMBOL = "TUTUSDT"
BITGET_SYM = "TUT/USDT:USDT"
LISTING_DATE = "2025-03-20"   # fapi 最早日K 实测
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "tut_backtest"
MONTHLY_URL = "https://data.binance.vision/data/futures/um/monthly/klines/{sym}/1h/{sym}-1h-{ym}.zip"
DAILY_KLINE_URL = "https://data.binance.vision/data/futures/um/daily/klines/{sym}/{tf}/{sym}-{tf}-{d}.zip"
DAILY_METRICS_URL = "https://data.binance.vision/data/futures/um/daily/metrics/{sym}/{sym}-metrics-{d}.zip"
FAPI_BASE = "https://fapi.binance.com"


def curl(url, proxy=True, timeout=30):
    cmd = ["curl", "-s", "--max-time", str(timeout)]
    if proxy:
        cmd += ["-x", PROXY]
    cmd += [url]
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    return r.stdout


def curl_json(url, proxy=True):
    out = curl(url, proxy)
    try:
        return json.loads(out)
    except Exception:
        return None


def read_zip_csv(zbytes: bytes) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    name = z.namelist()[0]
    return pd.read_csv(io.BytesIO(z.read(name)))


def months_between(d1: str, d2: str):
    y1, m1 = map(int, d1.split("-")[:2])
    y2, m2 = map(int, d2.split("-")[:2])
    out = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def dl_binance_1h_history(resume: bool) -> pd.DataFrame:
    """月文件全历史 + 当日 API。返回合并 df。"""
    frames = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for ym in months_between(LISTING_DATE, today):
        out_path = DATA_DIR / f"binance_1h_{ym}.csv"
        if resume and out_path.exists():
            frames.append(pd.read_csv(out_path))
            continue
        url = MONTHLY_URL.format(sym=SYMBOL, ym=ym)
        data = curl(url)
        if data[:2] != b"PK":
            print(f"  [binance 1h] {ym}: 无月文件（{len(data)}B），跳过")
            continue
        df = read_zip_csv(data)
        df = df.iloc[:, :6]
        df.columns = ["ts", "open", "high", "low", "close", "volume"]
        df.to_csv(out_path, index=False)
        frames.append(df)
        print(f"  [binance 1h] {ym}: {len(df)} 行")
    # 当日：API（月文件还没生成）；若已有缓存文件（重试循环/补数脚本存的）直接读入
    today_file = DATA_DIR / f"binance_1h_{today}.csv"
    if today_file.exists():
        tf = pd.read_csv(today_file)
        frames.append(tf)
        print(f"  [binance 1h] {today}: {len(tf)} 行（缓存文件）")
    elif not (resume and today_file.exists()):
        day_start = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        k = curl_json(f"{FAPI_BASE}/fapi/v1/klines?symbol={SYMBOL}&interval=1h&startTime={day_start}&limit=1500")
        # ⚠️ 类型检查：地区限制/限流时返回 dict 错误而非 list（2026-08-09 实测：proxy 节点美国出口被拒）
        if isinstance(k, list) and k:
            df = pd.DataFrame([x[:6] for x in k], columns=["ts", "open", "high", "low", "close", "volume"])
            df.to_csv(today_file, index=False)
            frames.append(df)
            print(f"  [binance 1h] {today}: {len(df)} 行（API）")
        else:
            msg = str(k)[:120] if k else "empty"
            print(f"  [binance 1h] {today}: API 不可用（{msg}）→ 等 vision 日文件补")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset="ts").sort_values("ts")


MONTHLY_FUNDING_URL = "https://data.binance.vision/data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{ym}.zip"


def dl_binance_funding(resume: bool) -> pd.DataFrame:
    """funding 全历史：vision 月度文件（不受地区限制）+ API 兜底当前月。"""
    out_path = DATA_DIR / "binance_funding.csv"
    if resume and out_path.exists():
        return pd.read_csv(out_path)
    frames = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # 1) vision 月度文件（历史全量）
    for ym in months_between(LISTING_DATE, today):
        url = MONTHLY_FUNDING_URL.format(sym=SYMBOL, ym=ym)
        data = curl(url, proxy=False)  # vision 不需要代理
        if data[:2] != b"PK":
            continue
        df = read_zip_csv(data)
        if "last_funding_rate" in df.columns:
            df = df.rename(columns={"calc_time": "ts", "last_funding_rate": "fundingRate"})
            df = df[["ts", "fundingRate"]]
            frames.append(df)
    # 2) API 兜底当前月（含今天；地区受限时跳过）
    if not (resume and (DATA_DIR / f"binance_funding_{today[:7]}.csv").exists()):
        try:
            start = int(datetime.strptime(today[:8] + "01", "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
            k = curl_json(f"{FAPI_BASE}/fapi/v1/fundingRate?symbol={SYMBOL}&startTime={start}&limit=1000")
            if isinstance(k, list) and k:
                df = pd.DataFrame([(int(x["fundingTime"]), float(x["fundingRate"])) for x in k],
                                  columns=["ts", "fundingRate"])
                frames.append(df)
            else:
                print("  [binance funding] 当前月 API 受限，跳过（vision 月度文件稍后补）")
        except Exception as e:
            print(f"  [binance funding] API 异常: {str(e)[:80]}")
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames).drop_duplicates(subset="ts").sort_values("ts")
    df.to_csv(out_path, index=False)
    print(f"  [binance funding] {len(df)} 条")
    return df


def dl_bitget_history(resume: bool) -> pd.DataFrame:
    """ccxt 分页拉 bitget 1h kline 全历史。
    ⚠️ bitget v2 history-candles 单次上限 200（2026-08-09 实测），limit=1500 会被截断。
    """
    out_path = DATA_DIR / "bitget_1h.csv"
    if resume and out_path.exists():
        return pd.read_csv(out_path)
    ex = ccxt.bitget({"enableRateLimit": True, "timeout": 20000, "options": {"defaultType": "swap"}})
    ex.proxies = {"http": PROXY, "https": PROXY}
    since = ex.parse8601(f"{LISTING_DATE}T00:00:00Z")
    all_rows = []
    guard = 0
    while guard < 300:
        guard += 1
        ohlcv = ex.fetch_ohlcv(BITGET_SYM, "1h", since=since, limit=200)
        if not ohlcv:
            break
        all_rows.extend(ohlcv)
        # ⚠️ since 必须按区间对齐（+3600000 而非 +1）：偏移 1ms 会把整根 K 线排除，返回 199 触发提前 break
        since = ohlcv[-1][0] + 3600000
        if len(ohlcv) < 200:
            break
        time.sleep(0.4)
    df = pd.DataFrame(all_rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset="ts").sort_values("ts")
    df.to_csv(out_path, index=False)
    print(f"  [bitget 1h] 共 {len(df)} 行（{datetime.utcfromtimestamp(df['ts'].iloc[0]/1000).strftime('%Y-%m-%d')} → "
          f"{datetime.utcfromtimestamp(df['ts'].iloc[-1]/1000).strftime('%Y-%m-%d %H:%M')}）")
    return df


def dl_bitget_funding(resume: bool) -> pd.DataFrame:
    """bitget funding 历史。
    ⚠️ 实测（2026-08-09）：bitget v2 funding-history 忽略 since，只返回最新 100 条
    （TUT 为 4h 结算 → 约 16.6 天）。诱盘期就在最近两周内，够用；更早数据无解。
    """
    out_path = DATA_DIR / "bitget_funding.csv"
    if resume and out_path.exists():
        return pd.read_csv(out_path)
    ex = ccxt.bitget({"enableRateLimit": True, "timeout": 20000, "options": {"defaultType": "swap"}})
    ex.proxies = {"http": PROXY, "https": PROXY}
    fr = ex.fetch_funding_rate_history(BITGET_SYM, limit=100)
    df = pd.DataFrame([(int(f["timestamp"]), float(f["fundingRate"])) for f in fr],
                      columns=["ts", "fundingRate"]).drop_duplicates(subset="ts").sort_values("ts")
    df.to_csv(out_path, index=False)
    if not df.empty:
        print(f"  [bitget funding] 共 {len(df)} 条（{datetime.utcfromtimestamp(df['ts'].iloc[0]/1000).strftime('%Y-%m-%d %H:%M')} → "
              f"{datetime.utcfromtimestamp(df['ts'].iloc[-1]/1000).strftime('%Y-%m-%d %H:%M')}）")
    return df


def to_epoch_ms(series: pd.Series) -> pd.Series:
    """字符串时间列 → epoch 毫秒。单位无关（pandas 3.0 to_datetime 默认 us，2.x 默认 ns）。"""
    return (pd.to_datetime(series) - pd.Timestamp("1970-01-01")) // pd.Timedelta("1ms")


def dl_event_days(days: list, resume: bool):
    """事件日 5m kline（币安 vision + bitget ccxt）+ 币安 OI metrics。"""
    ex = ccxt.bitget({"enableRateLimit": True, "timeout": 20000, "options": {"defaultType": "swap"}})
    ex.proxies = {"http": PROXY, "https": PROXY}
    for d in days:
        # 币安 5m
        bp = DATA_DIR / f"binance_5m_{d}.csv"
        if not (resume and bp.exists()):
            data = curl(DAILY_KLINE_URL.format(sym=SYMBOL, tf="5m", d=d))
            if data[:2] == b"PK":
                df = read_zip_csv(data).iloc[:, :6]
                df.columns = ["ts", "open", "high", "low", "close", "volume"]
                df.to_csv(bp, index=False)
                print(f"  [binance 5m] {d}: {len(df)} 行")
            else:
                print(f"  [binance 5m] {d}: 无文件")
        # 币安 OI metrics
        mp = DATA_DIR / f"binance_oi_{d}.csv"
        if not (resume and mp.exists()):
            data = curl(DAILY_METRICS_URL.format(sym=SYMBOL, d=d))
            if data[:2] == b"PK":
                df = read_zip_csv(data)[["create_time", "sum_open_interest", "sum_open_interest_value"]]
                df["ts"] = to_epoch_ms(df["create_time"])
                df.to_csv(mp, index=False)
                print(f"  [binance OI] {d}: {len(df)} 行")
            else:
                print(f"  [binance OI] {d}: 无文件")
        # bitget 5m（仅事件日，分页；⚠️ 单次上限 200，since 须按 5m 对齐 +300000）
        gp = DATA_DIR / f"bitget_5m_{d}.csv"
        if not (resume and gp.exists()):
            day_start = ex.parse8601(f"{d}T00:00:00Z")
            day_end = day_start + 86400000
            rows = []
            since = day_start
            guard = 0
            while guard < 10:
                guard += 1
                o = ex.fetch_ohlcv(BITGET_SYM, "5m", since=since, limit=200)
                if not o:
                    break
                rows.extend(o)
                since = o[-1][0] + 300000
                if len(o) < 200 or since >= day_end:
                    break
                time.sleep(0.3)
            if rows:
                df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
                df = df[df["ts"] < day_end]
                df.to_csv(gp, index=False)
                print(f"  [bitget 5m] {d}: {len(df)} 行")


def dl_all_days_full_5m(resume: bool):
    """全历史 5m：binance vision 日文件（并发）+ bitget API（串行分页）。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    days = []
    d = datetime.strptime(LISTING_DATE, "%Y-%m-%d").date()
    today = datetime.now(timezone.utc).date()
    while d <= today:
        days.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    print(f"== 全量 5m：{len(days)} 天（{days[0]} → {days[-1]}）==")

    # binance 5m + OI：vision 并发
    def fetch_binance(day):
        out = []
        bp = DATA_DIR / f"binance_5m_{day}.csv"
        if not (resume and bp.exists()):
            data = curl(DAILY_KLINE_URL.format(sym=SYMBOL, tf="5m", d=day))
            if data[:2] == b"PK":
                df = read_zip_csv(data).iloc[:, :6]
                df.columns = ["ts", "open", "high", "low", "close", "volume"]
                df.to_csv(bp, index=False)
                out.append(f"bn5m {day} {len(df)}")
            else:
                out.append(f"bn5m {day} NONE")
        mp = DATA_DIR / f"binance_oi_{day}.csv"
        if not (resume and mp.exists()):
            data = curl(DAILY_METRICS_URL.format(sym=SYMBOL, d=day))
            if data[:2] == b"PK":
                df = read_zip_csv(data)[["create_time", "sum_open_interest"]]
                df["ts"] = to_epoch_ms(df["create_time"])
                df = df.rename(columns={"sum_open_interest": "oi"})[["ts", "oi"]]
                df.to_csv(mp, index=False)
                out.append(f"bnOI {day} {len(df)}")
            else:
                out.append(f"bnOI {day} NONE")
        return out

    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fetch_binance, day) for day in days]
        done = 0
        for f in as_completed(futs):
            done += 1
            if done % 100 == 0:
                print(f"  binance vision {done}/{len(days)}...")

    # bitget 5m：串行（API 限速）
    bgex = ccxt.bitget({"enableRateLimit": True, "timeout": 20000, "options": {"defaultType": "swap"}})
    bgex.proxies = {"http": PROXY, "https": PROXY}
    for day in days:
        gp = DATA_DIR / f"bitget_5m_{day}.csv"
        if resume and gp.exists():
            continue
        day_start = bgex.parse8601(f"{day}T00:00:00Z")
        day_end = day_start + 86400000
        rows = []
        since = day_start
        guard = 0
        while guard < 8:
            guard += 1
            try:
                o = bgex.fetch_ohlcv(BITGET_SYM, "5m", since=since, limit=200)
            except Exception as e:
                time.sleep(2)
                continue
            if not o:
                break
            rows.extend(o)
            since = o[-1][0] + 300000
            if len(o) < 200 or since >= day_end:
                break
            time.sleep(0.25)
        if rows:
            df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
            df = df[df["ts"] < day_end]
            df.to_csv(gp, index=False)
    print("  bitget 5m 完成")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--events-only", action="store_true", help="只拉事件日明细（跳过全历史）")
    ap.add_argument("--full-5m", action="store_true", help="全历史 5m 模式：币安 vision + bitget API 拉全量日文件")
    ap.add_argument("--date", type=str, default=None, help="补指定日期的 binance 5m/OI（vision 日文件发布后调用）")
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if args.date:
        # 补单个日期：binance 5m + OI（vision 已发布时用）
        print(f"== 补日期 {args.date}（binance 5m + OI）==")
        dl_event_days([args.date], args.resume)
        print("✅ 补数完成")
        return
    if args.full_5m:
        dl_all_days_full_5m(args.resume)
        print("✅ 全量 5m 完成 →", DATA_DIR)
        return
    # 事件日列表：从 1h 粗扫价差 >2.5% 的日子（后续 5m 精扫）
    if not args.events_only:
        print("== 币安 1h 全历史 ==")
        b1h = dl_binance_1h_history(args.resume)
        print("== 币安 funding ==")
        dl_binance_funding(args.resume)
        print("== bitget 1h 全历史 ==")
        dl_bitget_history(args.resume)
        print("== bitget funding ==")
        dl_bitget_funding(args.resume)

        b1h.to_csv(DATA_DIR / "binance_1h.csv", index=False)
        # 粗扫事件日：用 high/low 极值算价差（close 会漏掉小时内插针，2026-08-09 TUT 案例验证）
        g1h = pd.read_csv(DATA_DIR / "bitget_1h.csv")
        m = b1h.merge(g1h, on="ts", suffixes=("_bn", "_bg"))
        m["spread_bn_prem"] = (m["high_bn"] - m["low_bg"]) / m["low_bg"]   # 币安溢价极值
        m["spread_bg_prem"] = (m["high_bg"] - m["low_bn"]) / m["low_bn"]   # bitget 溢价极值
        m["spread_ext"] = m[["spread_bn_prem", "spread_bg_prem"]].abs().max(axis=1)
        m["day"] = pd.to_datetime(m["ts"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
        ev_days = sorted(m[m["spread_ext"] > 0.025]["day"].unique())
        print(f"\n== 粗扫事件日（1h 极值价差 >2.5%）：{len(ev_days)} 天 ==")
        print(ev_days)
        (DATA_DIR / "event_days_1h_scan.txt").write_text("\n".join(ev_days))
    else:
        ev_days = [l.strip() for l in (DATA_DIR / "event_days_1h_scan.txt").read_text().splitlines() if l.strip()]

    print("\n== 事件日 5m + OI 明细 ==")
    dl_event_days(ev_days, args.resume)
    print("\n✅ 下载完成 →", DATA_DIR)


if __name__ == "__main__":
    main()
