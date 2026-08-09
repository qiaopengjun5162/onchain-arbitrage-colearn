#!/usr/bin/env python3
"""币安下架合约价差复盘（只读）。

验证 Paxon 分享策略：「bn下架合约价差能有几十个点，盯着oi猛干就好了」
方法：拉下架结算前 N 天的合约 klines + 现货 klines，对齐算价差序列。

用法：
  python binance_delisting_review.py --symbol ACX --settle 2026-08-07T09:00
  python binance_delisting_review.py --symbols ACX,HFT,PIVX --settle 2026-08-07T09:00 --days 4

依赖：curl（走 Clash 代理 127.0.0.1:7890，binance fapi 被地区限制）
坑：openInterestHist 接口被地区限制（返回 HTML 错误页），OI 只能换数据源
"""

import argparse
import csv
import datetime
import json
import os
import subprocess
import sys
import time

PROXY = "http://127.0.0.1:7890"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125.0 Safari/537.36"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "binance_delisting_review.csv")


def curl(url):
    cmd = ["curl", "-s", "--max-time", "25", "-x", PROXY, "-H", f"User-Agent: {UA}", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    return r.stdout


def review(sym: str, settle: str, days: int = 4) -> list:
    """复盘一个下架案例：返回 [{ts, symbol, contract, spot, spread_bps, contract_vol}]"""
    settle_dt = datetime.datetime.fromisoformat(settle)
    end = int(settle_dt.timestamp() * 1000)
    start = end - days * 86400 * 1000
    fk = curl(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}USDT&interval=1h&startTime={start}&endTime={end}&limit=300")
    sk = curl(f"https://api.binance.com/api/v3/klines?symbol={sym}USDT&interval=1h&startTime={start}&endTime={end}&limit=300")
    try:
        fd, sd = json.loads(fk), json.loads(sk)
    except Exception:
        return []
    if not isinstance(fd, list) or not isinstance(sd, list) or not fd or not sd:
        return []
    spot_by_t = {}
    for c in sd:
        try:
            spot_by_t[int(c[0]) // 3600000] = float(c[4])
        except (ValueError, TypeError, IndexError):
            continue
    rows = []
    for c in fd:
        try:
            h = int(c[0]) // 3600000
        except (ValueError, TypeError):
            continue
        if h in spot_by_t:
            f_p, s_p = float(c[4]), spot_by_t[h]
            rows.append({
                "ts": datetime.datetime.utcfromtimestamp(h * 3600).strftime("%Y-%m-%d %H:%M"),
                "symbol": sym, "contract": f_p, "spot": s_p,
                "spread_bps": round((f_p - s_p) / s_p * 10000, 1),
                "contract_vol": float(c[5]) if len(c) > 5 else 0,
            })
    rows.sort(key=lambda r: r["ts"])
    return rows


def report(rows: list, settle: str):
    if not rows:
        print("无数据"); return
    sym = rows[0]["symbol"]
    bps = [r["spread_bps"] for r in rows if abs(r["spread_bps"]) < 50000]
    vols = [r["contract_vol"] for r in rows]
    last6 = bps[-6:]
    print(f"\n=== {sym} 结算 {settle} UTC | {len(rows)} 小时 ===")
    print(f"价差: max {max(bps):.1f} / min {min(bps):.1f} / avg {sum(bps)/len(bps):.1f} bps")
    print(f"最后6h: avg {sum(last6)/len(last6):.1f} bps | 合约量峰值 {max(vols):,.0f}/h")
    print(f"{'时间':<16}{'合约':>12}{'现货':>12}{'bps':>9}{'量':>14}")
    for r in rows[-12:]:
        print(f"{r['ts']:<16}{r['contract']:>12.6f}{r['spot']:>12.6f}{r['spread_bps']:>9.1f}{r['contract_vol']:>14,.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", help="单个币种，如 ACX")
    ap.add_argument("--symbols", help="逗号分隔多个币种")
    ap.add_argument("--settle", required=True, help="结算时间 ISO，如 2026-08-07T09:00")
    ap.add_argument("--days", type=int, default=4)
    ap.add_argument("--csv", action="store_true", help="落盘 data/binance_delisting_review.csv")
    args = ap.parse_args()

    syms = []
    if args.symbol: syms.append(args.symbol.upper())
    if args.symbols: syms.extend(s.strip().upper() for s in args.symbols.split(","))
    if not syms:
        print("需要 --symbol 或 --symbols"); sys.exit(1)

    all_rows = []
    for sym in syms:
        rows = review(sym, args.settle, args.days)
        report(rows, args.settle)
        all_rows.extend(rows)
        time.sleep(0.8)

    if args.csv and all_rows:
        path = os.path.abspath(OUT)
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            if new: w.writeheader()
            w.writerows(all_rows)
        print(f"\n已落盘: {path} ({len(all_rows)} 行)")


if __name__ == "__main__":
    main()
