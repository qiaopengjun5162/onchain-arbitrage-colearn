#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hyperliquid Funding 抓取（hl_funding_monitor.py）— D12 广度落地（2026-08-16）
============================================================================
链上 perp funding 观察窗第一块（D9 广度笔记「下一步」第 1 项）：
  - 全资产 funding 快照（metaAndAssetCtxs）：232 资产 × 当前 1h funding
  - BTC/ETH/SOL 等主流 funding 历史（fundingHistory）：可回看跨所价差
  - 输出：data/hl_funding_snapshot.csv（快照，cron 用）+ data/hl_funding_history.csv（追加历史）

用法：
  python scripts/hl_funding_monitor.py --snapshot     # 只存当前快照（cron 每 1h）
  python scripts/hl_funding_monitor.py --history 7d   # 拉近 7 天 BTC/ETH/SOL funding 历史
  python scripts/hl_funding_monitor.py --top 10       # 只看当前 funding 绝对值 TOP10

依赖：hermes venv python3.11（urllib 即可，无第三方）
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
HL_INFO = "https://api.hyperliquid.xyz/info"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SNAP_CSV = DATA_DIR / "hl_funding_snapshot.csv"
HIST_CSV = DATA_DIR / "hl_funding_history.csv"

MAINSTREAM = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "SUI"]

# ⚠️ 关键换算：HL funding 是 1h 结算，fundingRate 字段是每小时费率（非年化）。
#    年化 = rate × 24 × 365。文档 https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding
FUNDING_HOURS_PER_DAY = 24
FUNDING_DAYS_PER_YEAR = 365


def http_post(url, payload, timeout=30):
    data = json.dumps(payload).encode()
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with op.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400] if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body}") from e


def fetch_all_funding():
    """metaAndAssetCtxs → [{coin, funding_h, funding_apr_pct, mark_px, open_interest}]"""
    d = http_post(HL_INFO, {"type": "metaAndAssetCtxs"})
    if not (isinstance(d, list) and len(d) == 2):
        raise RuntimeError(f"metaAndAssetCtxs 返回异常: {str(d)[:200]}")
    metas = d[0]["universe"]
    ctxs = d[1]
    out = []
    for m, c in zip(metas, ctxs):
        funding_h = float(c["funding"])          # 每小时费率（小数，如 0.0000125 = 0.00125%/h）
        funding_apr = funding_h * FUNDING_HOURS_PER_DAY * FUNDING_DAYS_PER_YEAR * 100  # %
        out.append({
            "coin": m["name"],
            "funding_h": funding_h,
            "funding_apr_pct": funding_apr,
            "mark_px": float(c.get("markPx", 0)),
            "oi_usd": float(c.get("openInterest", 0)) * float(c.get("markPx", 0)),
        })
    return out


def fetch_history(coin, hours=24 * 7):
    """fundingHistory 近 N 小时 → [{time, funding_h, premium}]"""
    end = int(time.time() * 1000)
    start = end - hours * 3600 * 1000
    d = http_post(HL_INFO, {"type": "fundingHistory", "coin": coin,
                            "startTime": start, "endTime": end})
    if not isinstance(d, list):
        raise RuntimeError(f"fundingHistory {coin} 异常: {str(d)[:200]}")
    return d


def fmt_ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def cmd_snapshot(top=None):
    rows = fetch_all_funding()
    rows.sort(key=lambda r: -abs(r["funding_apr_pct"]))
    SNAP_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAP_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "coin", "funding_h", "funding_apr_pct", "mark_px", "oi_usd"])
        ts = fmt_ts(int(time.time() * 1000))
        for r in rows:
            w.writerow([ts, r["coin"], r["funding_h"], round(r["funding_apr_pct"], 4),
                        r["mark_px"], round(r["oi_usd"], 0)])
    print(f"✅ 快照 {len(rows)} 资产 → {SNAP_CSV.name}")
    print(f"{'币':<8}{'1h费率':>10}{'年化%':>10}{'价格':>12}")
    for r in rows[: (top or 10)]:
        print(f"{r['coin']:<8}{r['funding_h']:>10.7f}{r['funding_apr_pct']:>10.2f}{r['mark_px']:>12.2f}")


def cmd_history(days=7):
    hours = days * 24
    for coin in MAINSTREAM:
        hist = fetch_history(coin, hours)
        with open(HIST_CSV, "a", newline="") as f:
            w = csv.writer(f)
            for row in hist:
                w.writerow([fmt_ts(int(row["time"])), coin,
                            row["fundingRate"], row["premium"]])
        print(f"✅ {coin}: {len(hist)} 条历史（{days} 天）")
        time.sleep(0.3)
    print(f"已追加到 {HIST_CSV.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="存全资产 funding 快照")
    ap.add_argument("--history", type=int, help="拉主流币 N 天 funding 历史")
    ap.add_argument("--top", type=int, default=10, help="快照显示 TOP N（默认 10）")
    args = ap.parse_args()

    if args.history:
        cmd_history(args.history)
    elif args.snapshot:
        cmd_snapshot(args.top)
    else:
        # 默认：快照（cron 友好，输出即告警信号）
        cmd_snapshot(args.top)


if __name__ == "__main__":
    main()
