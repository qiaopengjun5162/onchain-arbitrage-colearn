#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CEX 异常挂单雷达（错误单扫描，第 1 档）

逻辑：扫 Bybit/Binance 主流币订单簿深盘（limit=500），找偏离中价 >= 阈值的挂单：
  - 买单远高于中价（bid 高于 ask → 有人愿意高价买，或价格输入错误）
  - 卖单远低于中价（ask 低于 bid → 有人愿意低价卖，= 错误卖单，接走即赚）
金额 >= $5K 才报（避免尘单噪音）。

用法：
  python abnormal_order_radar.py --quiet                # watchdog：有信号才输出
  python abnormal_order_radar.py --threshold-pct 2.0 --min-usd 5000 --symbols BTC,ETH,SOL

输出：
  偏离 >= 阈值的挂单列表：方向（买高/卖低）、偏离%、金额、挂在第几档
  watchdog 模式空输出 = 静默

数据源：Bybit/Binance 公开 API（无需 key）
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")

# 主流币（流动性好、符合用户选标偏好）
SYMBOLS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "ADA", "AVAX", "LINK", "SUI",
           "TIA", "WIF", "PEPE", "OP", "ARB", "APT", "INJ", "SEI", "JUP", "W"]

EXCHANGES = ["bybit", "binance"]


def http_json(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    return json.loads(opener.open(req, timeout=timeout).read())


def fetch_orderbook_bybit(symbol: str, limit: int = 500):
    """Bybit 永续订单簿 → {"bids": [(px, qty)], "asks": [(px, qty)]}"""
    try:
        d = http_json(f"https://api.bybit.com/v5/market/orderbook?category=linear"
                      f"&symbol={symbol}USDT&limit={limit}")
        if d.get("retCode") != 0:
            return None
        return {"bids": [(float(b[0]), float(b[1])) for b in d["result"]["b"]],
                "asks": [(float(a[0]), float(a[1])) for a in d["result"]["a"]]}
    except Exception:
        return None


def fetch_orderbook_binance(symbol: str, limit: int = 500):
    """Binance 永续订单簿"""
    try:
        d = http_json(f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}USDT&limit={limit}")
        return {"bids": [(float(b[0]), float(b[1])) for b in d["bids"]],
                "asks": [(float(a[0]), float(a[1])) for a in d["asks"]]}
    except Exception:
        return None


def find_abnormal(ob, mid, threshold_pct, min_usd):
    """找偏离中价 >= threshold_pct 且金额 >= min_usd 的挂单。"""
    if not ob or not mid:
        return []
    found = []
    thr = threshold_pct / 100.0
    # 买单高于中价（bid > mid*(1+thr)）
    for px, qty in ob["bids"]:
        val = px * qty
        if val >= min_usd and px > mid * (1 + thr):
            found.append({"side": "买高", "px": px, "val": val,
                          "dev_pct": (px / mid - 1) * 100})
    # 卖单低于中价（ask < mid*(1-thr)）
    for px, qty in ob["asks"]:
        val = px * qty
        if val >= min_usd and px < mid * (1 - thr):
            found.append({"side": "卖低", "px": px, "val": val,
                          "dev_pct": (px / mid - 1) * 100})
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="watchdog 模式：无异常静默")
    ap.add_argument("--threshold-pct", type=float, default=2.0)
    ap.add_argument("--min-usd", type=float, default=5000)
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    now = dt.datetime.now(dt.timezone.utc)
    all_signals = []

    for ex_name in EXCHANGES:
        fetcher = fetch_orderbook_bybit if ex_name == "bybit" else fetch_orderbook_binance
        for sym in symbols:
            ob = fetcher(sym)
            if not ob:
                continue
            # 中价 = 前 5 档加权中价（比单纯 best 稳）
            b5 = ob["bids"][:5]
            a5 = ob["asks"][:5]
            if not b5 or not a5:
                continue
            mid = (sum(p for p, _ in b5) / len(b5) + sum(p for p, _ in a5) / len(a5)) / 2
            for sig in find_abnormal(ob, mid, args.threshold_pct, args.min_usd):
                all_signals.append((ex_name, sym, sig))

    if not all_signals:
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M} UTC] 无异常挂单："
                  f"{len(symbols)}币 × {len(EXCHANGES)}所，阈值 {args.threshold_pct}% / ≥${args.min_usd:,.0f}")
        return  # watchdog：空输出 = 静默

    all_signals.sort(key=lambda x: -abs(x[2]["dev_pct"]))
    print(f"⚡ 异常挂单雷达 @ {now:%Y-%m-%d %H:%M} UTC（阈值 {args.threshold_pct}% / ≥${args.min_usd:,.0f}）")
    print(f"{'所':<8}{'币':<7}{'方向':<5}{'偏离%':>8}{'金额$':>12}{'挂单价':>14}")
    for ex, sym, s in all_signals:
        print(f"{ex:<8}{sym:<7}{s['side']:<5}{s['dev_pct']:>+8.2f}{s['val']:>12,.0f}{s['px']:>14.6g}")
    print("\n提示：错误单存在时间极短，人工看到已晚；要做需挂机器监控+自动执行（风险自担）。")


if __name__ == "__main__":
    main()
