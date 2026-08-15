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
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "hl_funding.csv"
LOCK_PATH = CSV_PATH.with_suffix(".csv.lock")
API = "https://api.hyperliquid.xyz/info"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
MIN_ANNUAL = 0.50   # 年化 ≥50% 才打印醒目（cron 用，20% 太吵）
RETRIES = 3         # 网络抖动重试次数（watchdog 场景：失败就丢一次快照，值得重试）

def fetch():
    """带指数退避重试的抓取。3 次都失败才抛异常。"""
    last_err = None
    for attempt in range(RETRIES):
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
            req = urllib.request.Request(API, data=json.dumps({"type": "metaAndAssetCtxs"}).encode(),
                                         headers={"Content-Type": "application/json"})
            with opener.open(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # 超时/连接拒绝/HTTP 错误都算
            last_err = e
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"HL funding 抓取 {RETRIES} 次均失败: {last_err}") if last_err else RuntimeError("HL funding 抓取失败")

def write_snapshot(uni, asset_ctxs, ts):
    """追加快照：flock 防并发重复写 + 临时文件原子替换，杜绝半截 CSV。"""
    import fcntl
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
                os.replace(tmp_name, CSV_PATH)  # 原子替换，比直接 append 安全
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            return hot
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)

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

    # 数据一致性校验：universe 与 assetCtxs 必须等长，否则 zip 会静默截断写脏数据
    if len(uni) != len(asset_ctxs):
        print(f"⚠️ 数据长度不匹配: universe={len(uni)} vs assetCtxs={len(asset_ctxs)}，"
              f"本次快照将跳过 {len(uni)-len(asset_ctxs) if len(uni)>len(asset_ctxs) else len(asset_ctxs)-len(uni)} 行", file=sys.stderr)

    hot = write_snapshot(uni, asset_ctxs, ts)
    if hot:
        line = " | ".join(f"{c}: {a*100:+.1f}%/yr" for c, a in sorted(hot, key=lambda x: -abs(x[1])))
        print(f"⚠️ HL funding 极端: {line}")
    elif not quiet:
        print(f"HL funding 快照落盘 {ts}（{len(uni)} 资产，无 ≥{MIN_ANNUAL*100:.0f}% 极端）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
