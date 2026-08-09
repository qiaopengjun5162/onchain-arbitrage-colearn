#!/usr/bin/env python3
"""币安合约下架监控（watchdog：有信号才输出）。

原理：不抓公告（反爬），直接用 fapi exchangeInfo 的 SETTLING 状态做「下架进行中」实时信号。
- exchangeInfo 里 status=SETTLING 的永续 = 正在结算/即将下架（公告已发，reduce-only 或已平仓）
- 策略关联：notes/binance-delisting-arb-verified-20260809.md（下架前价差实测 1-4%）

用法：
  python delisting_monitor.py              # 拉取+检测（cron watchdog：非空即推送）
  python delisting_monitor.py --verbose    # 显示全部 SETTLING
  python delisting_monitor.py --watch 3600 # 轮询

依赖：hermes venv python3.11 + requests；binance fapi 走 Clash 代理 127.0.0.1:7890（地区限制）
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
FAPI_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def fetch_settling(session) -> list:
    """拉 fapi exchangeInfo，返回 SETTLING 的合约（按 deliveryDate 过滤未来结算）。"""
    r = session.get(FAPI_INFO, timeout=25)
    r.raise_for_status()
    d = r.json()
    now_ms = time.time() * 1000
    out = []
    for s in d.get("symbols", []):
        if s.get("status") == "SETTLING" and s.get("contractType") == "PERPETUAL":
            dd = s.get("deliveryDate", 0)
            # 只报未来结算的（历史遗留 SETTLING 过滤掉——它们早就下架了）
            if dd > now_ms:
                out.append({
                    "symbol": s["symbol"],
                    "deliveryDate": dd,
                    "pair": s.get("pair", ""),
                })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true", help="显示全部 SETTLING 而非仅新增")
    ap.add_argument("--watch", type=int, default=0)
    args = ap.parse_args()

    proxies = {"http": PROXY, "https": PROXY}
    session = requests.Session()
    session.proxies.update(proxies)
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    def tick(first=False):
        try:
            settling = fetch_settling(session)
        except Exception as e:
            print(f"[err] {now_iso()} {str(e)[:100]}", file=sys.stderr)
            return
        if not settling:
            if first and args.verbose:
                print(f"无未来结算合约（{now_iso()}）")
            return
        settling.sort(key=lambda s: s["deliveryDate"])
        if args.verbose or first:
            print(f"⚠️ {len(settling)} 个合约正在结算/下架（{now_iso()}）：")
            for s in settling[:25]:
                dd = datetime.utcfromtimestamp(s["deliveryDate"] / 1000).strftime("%m-%d %H:%M") if s["deliveryDate"] else "?"
                print(f"  {s['symbol']:<18} 结算 {dd} UTC")
        else:
            print(f"⚠️ {len(settling)} 个合约 SETTLING（{now_iso()}），最近结算: "
                  f"{settling[0]['symbol']} @ {datetime.utcfromtimestamp(settling[0]['deliveryDate']/1000).strftime('%m-%d %H:%M')} UTC")

    tick(first=True)
    if args.watch:
        while True:
            time.sleep(args.watch)
            tick()


if __name__ == "__main__":
    sys.exit(main())
