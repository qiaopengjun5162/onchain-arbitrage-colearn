#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hyperliquid Funding 抓取（hl_funding_monitor.py）— 合并版（2026-08-16）
========================================================================
D9 广度「链上 perp 资金费率」观察窗第一块。**合并两代功能**：
  - v1（2026-08-13 Codex + 08-15 dsh 修）：--quiet watchdog 模式、flock 原子写、
    指数退避重试、年化 ≥50% 极端告警 → cron wrapper run_hl_funding.sh 依赖这些
  - v2（2026-08-16 新增）：--snapshot/--history/--top 参数化、fundingHistory 主流币历史
  ⚠️ 2026-08-16 教训：write_file 覆盖已有脚本时先查 git 历史/引用方（cron wrapper 用
  --quiet），否则 cron 下次运行 argparse 报错失败。

数据源：api.hyperliquid.xyz/info（公开无 key）
产出：data/hl_funding.csv（v1 快照，cron 每小时追加）+ data/hl_funding_snapshot.csv
      （v2 全量快照）+ data/hl_funding_history.csv（v2 主流币历史）

用法：
  python scripts/hl_funding_monitor.py [--quiet]        # v1 兼容：快照落盘+极端告警（cron）
  python scripts/hl_funding_monitor.py --snapshot --top 10   # v2：全量快照+TOP 展示
  python scripts/hl_funding_monitor.py --history 7d     # v2：主流币历史

依赖：hermes venv python3.11（urllib 即可）
"""

import argparse
import csv
import datetime as dt
import fcntl
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "hl_funding.csv"            # v1 快照（cron 每小时追加）
LOCK_PATH = CSV_PATH.with_suffix(".csv.lock")
SNAP_CSV = DATA_DIR / "hl_funding_snapshot.csv"   # v2 全量快照
HIST_CSV = DATA_DIR / "hl_funding_history.csv"    # v2 主流币历史
API = "https://api.hyperliquid.xyz/info"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
MIN_ANNUAL = 0.50        # 年化 ≥50% 才告警（cron watchdog 用，20% 太吵）
RETRIES = 3              # 指数退避重试（watchdog 场景：失败就丢一次快照，值得重试）
MAINSTREAM = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "SUI"]


def http_post(url, payload, timeout=30):
    """带指数退避重试的 POST。3 次都失败才抛异常。"""
    last_err = None
    for attempt in range(RETRIES):
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
            req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
            with opener.open(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # 超时/连接拒绝/HTTP 错误都算
            last_err = e
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"HL API {RETRIES} 次均失败: {last_err}") if last_err else RuntimeError("HL API 失败")


def fetch_all():
    """metaAndAssetCtxs → (uni, asset_ctxs)"""
    resp = http_post(API, {"type": "metaAndAssetCtxs"})
    return resp[0], resp[1]


def fetch_history(coin, hours=24 * 7):
    """fundingHistory 近 N 小时 → list[dict]"""
    end = int(time.time() * 1000)
    start = end - hours * 3600 * 1000
    d = http_post(API, {"type": "fundingHistory", "coin": coin,
                        "startTime": start, "endTime": end})
    if not isinstance(d, list):
        raise RuntimeError(f"fundingHistory {coin} 异常: {str(d)[:200]}")
    return d


def write_snapshot_v1(uni, asset_ctxs, ts):
    """v1 追加快照：flock 防并发 + 临时文件原子替换。返回 hot 列表（年化 ≥MIN_ANNUAL）。"""
    with open(LOCK_PATH, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            new = not CSV_PATH.exists()
            hot = []
            fd, tmp_name = tempfile.mkstemp(dir=CSV_PATH.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", newline="") as f:
                    w = csv.writer(f)
                    if new:
                        w.writerow(["ts", "coin", "funding_hourly", "funding_annual", "markPx", "oiUsd"])
                    for u, c in zip(uni, asset_ctxs):
                        fh = float(c.get("funding", 0))
                        fa = fh * 24 * 365
                        oi = c.get("openInterest", 0)
                        px = c.get("markPx", 0)
                        oi_usd = float(oi) * float(px) if oi and px else 0
                        w.writerow([ts, u["name"], round(fh, 8), round(fa * 100, 2), px, round(oi_usd, 0)])
                        if abs(fa) >= MIN_ANNUAL:
                            hot.append((u["name"], fa))
                os.replace(tmp_name, CSV_PATH)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            return hot
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def cmd_v1(quiet):
    """v1 兼容路径：快照落盘 + 极端告警（cron watchdog 用）。"""
    try:
        meta, asset_ctxs = fetch_all()
    except Exception as e:
        print(f"HL funding 抓取失败: {str(e)[:120]}")
        return 1
    uni = meta.get("universe", [])
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if len(uni) != len(asset_ctxs):
        print(f"⚠️ 数据长度不匹配: universe={len(uni)} vs assetCtxs={len(asset_ctxs)}", file=sys.stderr)

    hot = write_snapshot_v1(uni, asset_ctxs, ts)
    if hot:
        line = " | ".join(f"{c}: {a*100:+.1f}%/yr" for c, a in sorted(hot, key=lambda x: -abs(x[1])))
        print(f"⚠️ HL funding 极端: {line}")
    elif not quiet:
        print(f"HL funding 快照落盘 {ts}（{len(uni)} 资产，无 ≥{MIN_ANNUAL*100:.0f}% 极端）")
    return 0


def cmd_snapshot(top=None):
    """v2 全量快照 → hl_funding_snapshot.csv + TOP 展示。"""
    meta, asset_ctxs = fetch_all()
    uni = meta.get("universe", [])
    rows = []
    for u, c in zip(uni, asset_ctxs):
        fh = float(c.get("funding", 0))
        fa = fh * 24 * 365
        px = float(c.get("markPx", 0))
        oi = c.get("openInterest", 0)
        oi_usd = float(oi) * px if oi and px else 0
        rows.append({"coin": u["name"], "funding_h": fh, "funding_apr_pct": fa * 100,
                     "mark_px": px, "oi_usd": oi_usd})
    rows.sort(key=lambda r: -abs(r["funding_apr_pct"]))
    SNAP_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAP_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "coin", "funding_h", "funding_apr_pct", "mark_px", "oi_usd"])
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        for r in rows:
            w.writerow([ts, r["coin"], r["funding_h"], round(r["funding_apr_pct"], 4),
                        r["mark_px"], round(r["oi_usd"], 0)])
    print(f"✅ 快照 {len(rows)} 资产 → {SNAP_CSV.name}")
    print(f"{'币':<8}{'1h费率':>10}{'年化%':>10}{'价格':>12}")
    for r in rows[: (top or 10)]:
        print(f"{r['coin']:<8}{r['funding_h']:>10.7f}{r['funding_apr_pct']:>10.2f}{r['mark_px']:>12.2f}")


def cmd_history(days=7):
    """v2 主流币 funding 历史 → hl_funding_history.csv（追加）。"""
    hours = days * 24
    for coin in MAINSTREAM:
        hist = fetch_history(coin, hours)
        with open(HIST_CSV, "a", newline="") as f:
            w = csv.writer(f)
            for row in hist:
                w.writerow([dt.datetime.fromtimestamp(int(row["time"]) / 1000,
                                                      tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
                            coin, row["fundingRate"], row["premium"]])
        print(f"✅ {coin}: {len(hist)} 条历史（{days} 天）")
        time.sleep(0.3)
    print(f"已追加到 {HIST_CSV.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="v1 模式：无极端不打印（cron watchdog）")
    ap.add_argument("--snapshot", action="store_true", help="v2：全量快照+TOP 展示")
    ap.add_argument("--history", type=int, help="v2：主流币 N 天历史")
    ap.add_argument("--top", type=int, default=10, help="v2 snapshot 显示 TOP N")
    args = ap.parse_args()

    if args.snapshot:
        cmd_snapshot(args.top)
    elif args.history:
        cmd_history(args.history)
    else:
        return cmd_v1(args.quiet)   # 默认 = v1 兼容（cron wrapper 依赖）


if __name__ == "__main__":
    sys.exit(main())
