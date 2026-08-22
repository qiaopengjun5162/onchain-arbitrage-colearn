#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bStock 开盘收敛异常监控（watchdog 模式）

逻辑：美股开盘后（北京 21:30 起），Binance bStock 应向真实美股价格收敛。
      开盘 30-90 分钟内仍偏离 >= 阈值 → 真错价（流动性没跟上 / 插针残留）→ 推送。
      未开盘 / 无异常 → 静默（空输出）。

用法：
  python bstock_convergence_watchdog.py            # 全量输出（调试）
  python bstock_convergence_watchdog.py --quiet    # watchdog：有信号才输出

部署：cron 每 15 分钟（21:00-22:50，周一至五），wrapper 见 run_bstock_conv.sh
数据源：Binance data-api 镜像（不封）+ yfinance 实时美股
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
THRESHOLD_BPS = int(os.environ.get("THRESHOLD_BPS", "150"))
# bStock 资产 -> yfinance 美股代码（Binance 现货 XXXBUSDT）
BSTOCK_MAP = {
    "MSTR": "MSTR", "SPY": "SPY", "QQQ": "QQQ", "NVDA": "NVDA",
    "TSLA": "TSLA", "AAPL": "AAPL", "COIN": "COIN", "AVGO": "AVGO",
    "ALAB": "ALAB", "GME": "GME", "AMZN": "AMZN", "META": "META",
    "MSFT": "MSFT", "NFLX": "NFLX",
}


def http_json(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    return json.loads(opener.open(req, timeout=timeout).read())


def fetch_bstock_prices():
    """Binance 现货 bStock 24h tickers → {sym: {px, vol24h}}"""
    out = {}
    try:
        tickers = http_json("https://data-api.binance.vision/api/v3/ticker/24hr")
        for t in tickers:
            sym = t["symbol"]
            if sym.endswith("BUSDT") and sym[:-5] in BSTOCK_MAP:
                out[sym[:-5]] = {
                    "px": float(t["lastPrice"]),
                    "vol24h": float(t["quoteVolume"]),
                }
    except Exception as e:
        print(f"[!] bStock 拉取失败: {str(e)[:100]}", file=sys.stderr)
    return out


def fetch_us_prices():
    """yfinance 美股实时价。未开盘/假日时 last 可能=昨收，由调用方判断。"""
    import yfinance as yf
    os.environ.setdefault("HTTPS_PROXY", PROXY)
    os.environ.setdefault("HTTP_PROXY", PROXY)
    out = {}
    for sym in BSTOCK_MAP:
        try:
            h = yf.Ticker(sym).history(period="2d")
            if len(h) >= 2:
                last = float(h["Close"].iloc[-1])
                prev = float(h["Close"].iloc[-2])
                # 交易活跃度：最后一根成交量
                vol = float(h["Volume"].iloc[-1])
                out[sym] = {"last": last, "prev": prev, "vol": vol}
        except Exception:
            continue
    return out


def is_us_market_open(us: dict) -> bool:
    """粗略判断美股是否开盘：yfinance 最新一根有量（>0）且价格不同于昨收。"""
    if not us:
        return False
    open_count = 0
    for sym, d in us.items():
        if d["vol"] > 0 and abs(d["last"] - d["prev"]) > 1e-9:
            open_count += 1
    return open_count >= max(1, len(us) // 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="watchdog 模式：无异常静默")
    ap.add_argument("--threshold-bps", type=int, default=THRESHOLD_BPS)
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    weekday = now.weekday()  # 0=周一
    hour_min = now.hour * 60 + now.minute

    # 美股夏令时开盘 = 北京 21:30；监控窗口 21:00-23:00（含开盘前预热）
    if weekday >= 5:  # 周六日不开盘
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 周末，美股休市")
        return
    if not (21 * 60 <= hour_min <= 23 * 60):
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 非监控窗口（北京 21:00-23:00）")
        return

    bstocks = fetch_bstock_prices()
    us = fetch_us_prices()
    if not bstocks or not us:
        if not args.quiet:
            print("[!] 数据拉取失败，本次跳过")
        return

    # 开盘前（21:00-21:30）不判断（可能还没开盘）
    if hour_min < 21 * 60 + 35:
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 开盘前窗口（21:00-21:35），跳过判断")
        return
    if not is_us_market_open(us):
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 美股尚未开盘（假日/延迟），跳过")
        return

    rows = []
    for sym, b in bstocks.items():
        u = us.get(sym)
        if not u:
            continue
        # 实时价（开盘后 yfinance last = 实时价）
        dev_bps = (b["px"] - u["last"]) / u["last"] * 10000
        rows.append((sym, b["px"], u["last"], dev_bps, b["vol24h"]))

    rows.sort(key=lambda x: -abs(x[3]))
    signals = [r for r in rows if abs(r[3]) >= args.threshold_bps]

    if not signals:
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 无异常：全部 bStock 偏离 < {args.threshold_bps}bps")
        return  # watchdog：空输出 = 静默

    # 有信号才输出
    print(f"⚡ bStock 开盘收敛异常 @ {now:%Y-%m-%d %H:%M}（美股已开盘，阈值 {args.threshold_bps}bps）")
    print(f"{'美股':<6}{'bStock价':>10}{'美股实时':>10}{'偏离bps':>9}{'24h量$':>13}")
    for sym, px, up, dev, vol in signals:
        tag = " 溢价" if dev > 0 else " 折价"
        print(f"{sym:<6}{px:>10.2f}{up:>10.2f}{dev:>+9.1f}{vol:>13,.0f}{tag}")
    print("\n提示：开盘后仍大幅偏离 = 真错价（流动性没跟上/插针残留），收敛是大概率事件；")
    print("      单腿可做但需确认反向锚（正股可买/可空），仓位按蚂蚁仓+收敛锚设止损。")


if __name__ == "__main__":
    main()
