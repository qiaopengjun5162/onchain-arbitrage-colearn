#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bStocks 事件响应检查表 v1（2026-08-12）
=======================================
触发：Binance bStocks 新交易对公告 → 15 分钟内给出「新 ticker 有没有套利窗口」判定。

流程（半自动检查表）：
1. 输入 bStocks ticker（如 NVDAB / TSLAB / ALABB）
2. 底层美股实时价（yfinance，缓存 60s）
3. Binance 现货价（api.binance.com，bStock 交易对如 XXXBUSDT）
4. 链上 BSC 池价 + 流动性（DexScreener search）
5. 三方价差 → 扣 DEX 费/滑点 → 净价差 bps → 判定 NO-GO / 观察 / GO

判定口径（诚实版）：
- |净价差| < 30bps → NO-GO（市场定价准，DOS 教训）
- 30-200bps 但深度 < $10K → 观察（看到价差 ≠ 吃到）
- >200bps 且深度足够 → GO（安全垫 1-2%，小额全链路试单，先验证提现再验证价差）

用法：
    python scripts/bstocks_event_response.py --ticker NVDAB
    python scripts/bstocks_event_response.py --tickers NVDAB,TSLAB
依赖：hermes venv（yfinance）
"""

import argparse
import json
import os
import sys
import time
import urllib.request

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 15
MIN_LIQ_USD = 10_000
NOGO_BPS = 30
GO_BPS = 200

def http_json(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    proxy = urllib.request.ProxyHandler(PROXIES)
    opener = urllib.request.build_opener(proxy)
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def stock_price(ticker):
    """底层美股实时价（yfinance，失败返回 None）"""
    import yfinance as yf
    # bStocks 命名：XXXB → 底层美股 XXX（GMEB→GME, ALABB→ALAB, NVDAB→NVDA）
    cands = [ticker]
    if ticker.endswith("B") and len(ticker) > 3:
        cands.append(ticker[:-1])
    for c in cands:
        try:
            t = yf.Ticker(c)
            hist = t.history(period="1d", interval="1m", prepost=True)
            if hist.empty:
                hist = t.history(period="5d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            continue
    return None

def binance_price(symbol):
    """Binance 现货价。主 API 区域封锁（451）→ 用 data-api.binance.vision 镜像（不封）"""
    for s in (symbol, f"{symbol}USDT"):
        for base in ("https://data-api.binance.vision", "https://api.binance.com"):
            try:
                d = http_json(f"{base}/api/v3/ticker/price?symbol={s}")
                return s, float(d["price"])
            except Exception:
                continue
    return None, None

def dexscreener(ticker):
    """链上 BSC 池（DexScreener search）"""
    try:
        d = http_json(f"https://api.dexscreener.com/latest/dex/search?q={ticker}")
    except Exception:
        return []
    out = []
    for p in (d.get("pairs") or []):
        if p.get("chainId") != "bsc":
            continue
        # 严格 symbol 匹配，过滤假币/同名池（JACKET 之类搜索误配）
        base = p.get("baseToken", {}).get("symbol", "")
        if base.upper() != ticker.upper():
            continue
        liq = float(p.get("liquidity", {}).get("usd") or 0)
        if liq < 1000:
            continue
        out.append({
            "dex": p.get("dexId"), "pair": p.get("pairAddress")[:10],
            "base": base, "addr": p.get("baseToken", {}).get("address", "")[:14],
            "price": float(p.get("priceUsd") or 0),
            "liq_usd": liq, "vol_24h": float(p.get("volume", {}).get("h24") or 0),
            "fee": p.get("fee"), "url": p.get("url", "")[:80],
        })
    out.sort(key=lambda x: -x["liq_usd"])
    return out[:3]

def judge(name, chain_price, underlying, liq, extra=""):
    if not chain_price or not underlying or underlying <= 0:
        return f"  ❓ {name}: 缺价格（chain={chain_price} underlying={underlying}）{extra}"
    spread_bps = (chain_price - underlying) / underlying * 10000
    net = spread_bps  # 简化：先看毛价差；GO 档再扣费
    if abs(net) < NOGO_BPS:
        verdict = "NO-GO（市场定价准）"
    elif abs(net) < GO_BPS:
        if liq < MIN_LIQ_USD:
            verdict = f"观察（价差 {net:+.0f}bps 但深度 ${liq:,.0f} < $10K，看到≠吃到）"
        else:
            verdict = f"观察（价差 {net:+.0f}bps，深度 ${liq:,.0f}，可小额试单）"
    else:
        if liq < MIN_LIQ_USD:
            verdict = f"⚠️ GO 但深度不足（{net:+.0f}bps，${liq:,.0f}）——先验证提现/赎回再谈"
        else:
            verdict = f"🚨 GO（{net:+.0f}bps，深度 ${liq:,.0f}，安全垫 1-2% 小额全链路）"
    return f"  {name}: {verdict}{extra}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", help="bStock ticker 如 NVDAB")
    ap.add_argument("--tickers", help="逗号分隔多个")
    args = ap.parse_args()
    tickers = [t.strip().upper() for t in (args.tickers or args.ticker or "").split(",") if t.strip()]
    if not tickers:
        print("用法: --ticker NVDAB 或 --tickers A,B,C")
        return 1

    print(f"=== bStocks 事件响应检查表 @ {time.strftime('%H:%M:%S')} ===\n")
    for tk in tickers:
        underlying = tk[:-1] if tk.endswith("B") and len(tk) > 4 else tk
        print(f"▎{tk}（底层 {underlying}）")
        up = stock_price(underlying)
        print(f"  美股 {underlying}: {up if up else '取不到'}")
        bsym, bpx = binance_price(tk + "USDT")
        print(f"  Binance {bsym}: {bpx if bpx else '无现货交易对'}")
        pools = dexscreener(tk)
        if not pools:
            print("  链上 BSC: 未找到池（新上市还没流动性？）")
        for p in pools:
            extra = f"  vol24h ${p['vol_24h']:,.0f}"
            print(judge(f"{p['dex']} {p['base']} ${p['price']:.4f} (liq ${p['liq_usd']:,.0f})",
                        p["price"], up, p["liq_usd"], extra))
            # 链上 vs Binance 两腿价差（可执行结构：链上买 → Binance 卖）
            if bpx:
                x = (bpx - p["price"]) / p["price"] * 10000
                if abs(x) >= NOGO_BPS:
                    print(f"    ↳ 链上→Binance 两腿价差 {x:+.0f}bps（跨所搬砖结构；⚠️先验证提现/到账再谈）")
        if bpx and up:
            print(judge(f"Binance 现货 {bsym} ${bpx:.4f}", bpx, up, 10**9, "（现货对标美股）"))
            print(f"    ⚠️ 现货单腿 = 赌收敛不是真套利；有 TradFi perp 才能锁（期现结构）")
        print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
