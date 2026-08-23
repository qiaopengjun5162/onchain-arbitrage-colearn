#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solana 原生币股（Backpack Securities 发行）开盘收敛异常监控（watchdog 模式）

逻辑：美股开盘后（北京 21:30 起），Solana 链上币股应向真实美股价格收敛。
      开盘 35 分钟后仍偏离 >= 阈值 → 真错价（流动性没跟上 / 插针残留）→ 推送。
      未开盘 / 无异常 → 静默（空输出）。

标的（2026-08-23 上市，Sunrise 发行 / Backpack Securities 承销）：
  LLY  = Eli Lilly       mint LLYuwZ33keFihgwoxXsBawy31AiRFLFSva32TYq5TvD
  MRNA = Moderna         mint MRNAzXzhNcaEXJPibHEn8cd4vyekCDiivTyEwswLUCT

用法：
  python solana_stock_convergence_watchdog.py            # 全量输出（调试）
  python solana_stock_convergence_watchdog.py --quiet    # watchdog：有信号才输出

部署：cron 每 15 分钟（21:00-22:55，周一至五）
数据源：DeFiLlama coins API（链上聚合价，confidence 0.99）+ GeckoTerminal（池子/流动性）
        + yfinance 实时美股（hermes venv）
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
THRESHOLD_BPS = int(os.environ.get("THRESHOLD_BPS", "150"))

# Solana 币股 -> {mint, 美股代码}
SOL_STOCK_MAP = {
    "LLY": {
        "mint": "LLYuwZ33keFihgwoxXsBawy31AiRFLFSva32TYq5TvD",
        "us": "LLY",
    },
    "MRNA": {
        "mint": "MRNAzXzhNcaEXJPibHEn8cd4vyekCDiivTyEwswLUCT",
        "us": "MRNA",
    },
}


def http_json(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    return json.loads(opener.open(req, timeout=timeout).read())


def fetch_sol_prices():
    """DeFiLlama 链上聚合价 + GeckoTerminal 主池流动性。返回 {sym: {px, liq, vol24h}}"""
    out = {}
    try:
        ids = ",".join(f"solana:{v['mint']}" for v in SOL_STOCK_MAP.values())
        d = http_json(f"https://coins.llama.fi/prices/current/{ids}")
        for sym, v in SOL_STOCK_MAP.items():
            c = d.get("coins", {}).get(f"solana:{v['mint']}")
            if c:
                out[sym] = {"px": c["price"], "liq": None, "vol24h": None}
    except Exception as e:
        print(f"[!] DeFiLlama 拉取失败: {str(e)[:100]}", file=sys.stderr)
        return out
    # GeckoTerminal 补流动性/24h 量（取 24h 量最大池）
    for sym, v in SOL_STOCK_MAP.items():
        try:
            d = http_json(
                f"https://api.geckoterminal.com/api/v2/networks/solana/tokens/{v['mint']}/pools?page=1")
            best = None
            for p in d.get("data", []):
                a = p["attributes"]
                vol = float(a.get("volume_usd", {}).get("h24") or 0)
                if best is None or vol > best[0]:
                    best = (vol, float(a.get("reserve_in_usd") or 0))
            if best:
                out[sym]["vol24h"] = best[0]
                out[sym]["liq"] = best[1]
        except Exception:
            pass
    return out


def fetch_us_prices():
    """yfinance 美股实时价。未开盘时 last 可能=昨收，由调用方判断。"""
    import yfinance as yf
    os.environ.setdefault("HTTPS_PROXY", PROXY)
    os.environ.setdefault("HTTP_PROXY", PROXY)
    out = {}
    for sym, v in SOL_STOCK_MAP.items():
        us = v["us"]
        try:
            h = yf.Ticker(us).history(period="2d")
            if len(h) >= 2:
                out[sym] = {
                    "last": float(h["Close"].iloc[-1]),
                    "prev": float(h["Close"].iloc[-2]),
                    "vol": float(h["Volume"].iloc[-1]),
                }
        except Exception:
            continue
    return out


def is_us_market_open(us: dict) -> bool:
    if not us:
        return False
    open_count = sum(
        1 for d in us.values() if d["vol"] > 0 and abs(d["last"] - d["prev"]) > 1e-9)
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
    if weekday >= 5:
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 周末，美股休市")
        return
    if not (21 * 60 <= hour_min <= 23 * 60):
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 非监控窗口（北京 21:00-23:00）")
        return
    if hour_min < 21 * 60 + 35:
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 开盘前窗口（21:00-21:35），跳过判断")
        return

    sol = fetch_sol_prices()
    us = fetch_us_prices()
    if not sol or not us:
        if not args.quiet:
            print("[!] 数据拉取失败，本次跳过")
        return

    if not is_us_market_open(us):
        if not args.quiet:
            print(f"[{now:%Y-%m-%d %H:%M}] 美股未开盘（无最新成交），跳过")
        return

    signals = []
    for sym, v in SOL_STOCK_MAP.items():
        if sym not in sol or sym not in us:
            continue
        spx = sol[sym]["px"]
        upx = us[sym]["last"]
        bps = (spx / upx - 1) * 10000
        liq = sol[sym].get("liq")
        vol = sol[sym].get("vol24h")
        if abs(bps) >= args.threshold_bps:
            signals.append(
                f"⚠️ {sym} 开盘后链上偏离 {bps:+.0f}bps\n"
                f"  链上 ${spx:,.2f} vs 美股 ${upx:,.2f}\n"
                f"  主池流动性 ${liq:,.0f} | 24h量 ${vol:,.0f}"
                if liq is not None else
                f"⚠️ {sym} 开盘后链上偏离 {bps:+.0f}bps\n"
                f"  链上 ${spx:,.2f} vs 美股 ${upx:,.2f}")

    if signals:
        print(f"[{now:%Y-%m-%d %H:%M} 北京] Solana 币股开盘收敛异常（阈值 {args.threshold_bps}bps）")
        for s in signals:
            print(s)
    elif not args.quiet:
        print(f"[{now:%Y-%m-%d %H:%M}] 美股开盘，无偏离 ≥{args.threshold_bps}bps 的标的（正常收敛）")


if __name__ == "__main__":
    main()
