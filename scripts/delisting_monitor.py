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


def depth_analysis(session, symbol: str) -> dict:
    """订单簿联动：拉 fapi + spot 深度，量化「±1%/±2% 深度 vs 价差」。

    意义（notes/bitmart-first-pot-alpha-20260809.md 容量真相）：
    - 价差是「每单位可吃」的上限，容量决定「能吃多少单位」
    - 下架币价差常 1-4%，但盘口薄 → 实际可吃量 << 价差幅度
    - 这个函数在 SETTLING 信号出现时自动量化「X bps 价差下能吃多少」
    """
    try:
        r = session.get(f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit=1000", timeout=15)
        f = r.json()
        r2 = session.get(f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=1000", timeout=15)
        s = r2.json()
        if "bids" not in f or "bids" not in s:
            return {"error": "深度格式异常"}
        f_bid = float(f["bids"][0][0]) if f["bids"] else 0
        f_ask = float(f["asks"][0][0]) if f["asks"] else 0
        s_bid = float(s["bids"][0][0]) if s["bids"] else 0
        s_ask = float(s["asks"][0][0]) if s["asks"] else 0
        # 价差（合约 vs 现货，bps）
        spread_bps = (f_bid - s_ask) / s_ask * 10000 if s_ask else 0

        def depth_1pct(book, best, pct):
            """从 best 向价格移动 pct% 内累计量（吃单方向）。"""
            cum = 0.0
            for price, qty in book:
                p = float(price)
                if best > 0:
                    if pct > 0 and p <= best * (1 + pct / 100):
                        cum += float(qty)
                    elif pct < 0 and p >= best * (1 + pct / 100):
                        cum += float(qty)
                    else:
                        break
            return cum

        return {
            "spread_bps": round(spread_bps, 1),
            "fapi_bid": f_bid, "fapi_ask": f_ask,
            "spot_bid": s_bid, "spot_ask": s_ask,
            # 合约盘口 ±1%/±2% 深度（按 ask 侧吃 = 做空合约）
            "fapi_ask_1pct": round(depth_1pct(f["asks"], f_ask, 1), 0),
            "fapi_ask_2pct": round(depth_1pct(f["asks"], f_ask, 2), 0),
            # 现货盘口 ±1%/±2% 深度（按 bid 侧 = 做多现货）
            "spot_bid_1pct": round(depth_1pct(s["bids"], s_bid, -1), 0),
            "spot_bid_2pct": round(depth_1pct(s["bids"], s_bid, -2), 0),
        }
    except Exception as e:
        return {"error": str(e)[:80]}


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
        # 订单簿联动：对最近的 SETTLING 合约做深度分析（量化可吃量）
        if settling:
            sym = settling[0]["symbol"]
            dep = depth_analysis(session, sym)
            if "error" not in dep:
                print(f"📊 盘口（{sym}，{now_iso()}）：价差 {dep['spread_bps']:+.1f} bps")
                print(f"   fapi ask: {dep['fapi_ask']} | spot bid: {dep['spot_bid']}")
                print(f"   ±1% 深度: 合约侧 {dep['fapi_ask_1pct']:,.0f} | 现货侧 {dep['spot_bid_1pct']:,.0f}")
                print(f"   ±2% 深度: 合约侧 {dep['fapi_ask_2pct']:,.0f} | 现货侧 {dep['spot_bid_2pct']:,.0f}")
                print(f"   → 价差 {dep['spread_bps']}bps 能吃 {min(dep['fapi_ask_1pct'], dep['spot_bid_1pct']):,.0f} 单位（±1%深度下限）")
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
