#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hyperliquid funding 快照（hl_funding_monitor.py）— 2026-08-13
=============================================================
用途：D9 广度「链上 perp 资金费率」的下一步——HL funding 抓取，与 CEX/Drift 并排观察。
数据源：api.hyperliquid.xyz/info（公开无 key），POST {"type":"metaAndAssetCtxs"}
产出：data/hl_funding.csv（每小时一条快照，全资产 funding 年化）

用法：hermes venv python3 scripts/hl_funding_monitor.py [--quiet]
      挂 cron：no_agent + wrapper，watchdog 模式（异常才报）
"""

import csv
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "hl_funding.csv"
API = "https://api.hyperliquid.xyz/info"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
MIN_ANNUAL = 0.50   # 年化 ≥50% 才打印醒目（cron 用，20% 太吵）

def fetch():
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    req = urllib.request.Request(API, data=json.dumps({"type": "metaAndAssetCtxs"}).encode(),
                                 headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=30) as r:
        return json.loads(r.read().decode())

def main():
    quiet = "--quiet" in sys.argv
    try:
        resp = fetch()  # [meta_dict, assetCtxs_list]
        meta, asset_ctxs = resp[0], resp[1]
    except Exception as e:
        print(f"HL funding 抓取失败: {str(e)[:120]}")  # 非 quiet 模式也报（watchdog 需要）
        return 1
    uni = meta.get("universe", [])
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    new = not CSV_PATH.exists()
    hot = []
    with open(CSV_PATH, "a", newline="") as f:
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
    if hot:
        line = " | ".join(f"{c}: {a*100:+.1f}%/yr" for c, a in sorted(hot, key=lambda x: -abs(x[1])))
        print(f"⚠️ HL funding 极端: {line}")
    elif not quiet:
        print(f"HL funding 快照落盘 {ts}（{len(uni)} 资产，无 ≥{MIN_ANNUAL*100:.0f}% 极端）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
