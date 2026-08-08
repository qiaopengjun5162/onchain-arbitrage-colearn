#!/usr/bin/env python3
"""CEX 跨所现货价差监控 v0.1（只读，不下单）。

学习目标（D4，2026-08-08）：
- 多交易所同一资产价差 = 最简单的套利形态（API 健全、无链上风险）
- 跨所搬砖真实成本 = 买入所手续费 + 卖出所手续费 + 提币费 + 滑点
  （提币不是即时的，有确认时间 → 价格波动风险，这是"先手动跑"的原因）
- 只做发现与告警：watchdog + human decision，绝不自动下单

v0.1 新增（2026-08-08 实测结论）：
- xStocks 币股（NVDAX/TSLAX/COINX/...）只有 gate 一家有 → 跨所价差无对手盘
- 正确方向 = gate 币股 vs 真实美股（yfinance）：闭市漂移 → 开盘收敛的时钟差结构
- 主流币跨所价差已被磨平（毛价差 <2bps，净收益恒负）→ 监控重心转向新上币/币股

用法：
  python cex_spread_monitor.py --once          # 跑一次
  python cex_spread_monitor.py --watch 60      # 每 60 秒轮询
  python cex_spread_monitor.py --symbols BTC,ETH --once
  python cex_spread_monitor.py --stocks        # 币股 vs 美股模式
  python cex_spread_monitor.py --quiet         # 无信号时静默（cron 用）

依赖：.venv/bin/python（ccxt 4.5.71）+ yfinance（已装 python3.11 venv）
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

# CN 网络：多数交易所 API 需要代理（Clash 默认 127.0.0.1:7890）。gate 可直连，okx/bitget/kucoin 需代理。
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")

# ---------------------------------------------------------------- 配置
EXCHANGES = ["okx", "bitget", "kucoin", "gate"]   # 已实测 CN 网络直连可用；binance/bybit 限地区
SYMBOLS = ["BTC", "ETH", "SOL"]                    # 主流通证，各所均有现货

# 成本模型（bps，1bps = 0.01%）
TAKER_FEE_BPS = {   # 各所现货 taker 费率（约数，以官方为准）
    "okx": 10, "bitget": 10, "kucoin": 10, "gate": 20,
}
WITHDRAW_FEE = {    # 提币费（USDT 计价约数，按币种）。未配置的币=0 → 结果偏乐观！
    "BTC": 0.0004,  # ~$26 @ $65k
    "ETH": 0.001,   # ~$1.9 @ $1900
    "SOL": 0.01,    # ~$1.6 @ $160
}
WITHDRAW_FEE_USDT = 0.8  # 提币网络费按 USDT 折算的兜底值（多数所稳定币提币费 ~$0.5-1）

THRESHOLD_BPS = 30       # 净收益 ≥ 30bps 才报信号（低阈值先看数据）
SLIPPAGE_BPS = 5         # 滑点保守估算（bid-ask 一半）
MIN_LIQUIDITY_USDT = 50000  # 池子太小不报（防止报价不可执行）

# xStocks 币股：gate 独有交易对 → 真实美股代码映射（时钟差套利：闭市漂移→开盘收敛）
STOCKS = {   # gate 交易对 → yfinance 美股代码
    "NVDAX/USDT": "NVDA", "TSLAX/USDT": "TSLA", "COINX/USDT": "COIN",
    "MSTRX/USDT": "MSTR", "AAPLX/USDT": "AAPL", "AMZNX/USDT": "AMZN",
    "GOOGLX/USDT": "GOOGL", "QQQX/USDT": "QQQ",
    "SPYX/USDT": "SPY", "MCDX/USDT": "MCD", "AVGOX/USDT": "AVGO",
    # NFLXX 已剔除：2026-08-08 实测 yfinance NFLX $74.14 vs gate 744.29（10 倍差，数据源异常）
}
STOCK_DEVIATION_BPS = 30  # 币股 vs 美股偏离 ≥30bps 报信号（实测闭市漂移普遍 20-100bps）
STOCK_LOG_PATH = Path(__file__).parent.parent / "data" / "stock_vs_us_stock_log.csv"

LOG_PATH = Path(__file__).parent.parent / "data" / "cex_spread_log.csv"

# ---------------------------------------------------------------- 数据
def build_exchange(name: str):
    cls = getattr(ccxt, name)
    ex = cls({
        "enableRateLimit": True,
        "timeout": 15000,
        "options": {"defaultType": "spot"},
    })
    if os.environ.get("NO_PROXY") != "1":
        ex.proxies = {"http": PROXY, "https": PROXY}
    return ex


def fetch_all(exchanges, symbols) -> dict:
    """返回 {symbol: {ex: {"bid","ask","vol24h_usd"}}}"""
    out = {s: {} for s in symbols}
    for name in exchanges:
        try:
            ex = build_exchange(name)
            markets = ex.load_markets()
            for sym in symbols:
                pair = f"{sym}/USDT"
                if pair not in markets:
                    continue
                t = ex.fetch_ticker(pair)
                bid, ask = t.get("bid"), t.get("ask")
                if not bid or not ask:
                    continue
                # 24h 成交额（USDT）≈ quoteVolume
                vol = t.get("quoteVolume") or 0
                out[sym][name] = {"bid": bid, "ask": ask, "vol24h": vol}
        except Exception as e:
            print(f"  [!] {name} 拉取失败: {str(e)[:100]}", file=sys.stderr)
    return out


# ---------------------------------------------------------------- 成本
def net_bps(sym: str, buy_ex: str, buy_ask: float, sell_ex: str, sell_bid: float) -> dict:
    """跨所搬砖净收益：买@A → 提币到 B → 卖@B。
    毛价差 = (sell_bid - buy_ask) / buy_ask
    成本   = A 手续费 + B 手续费 + 提币费 + 滑点
    """
    gross_bps = (sell_bid - buy_ask) / buy_ask * 10000
    fee_bps = TAKER_FEE_BPS.get(buy_ex, 10) + TAKER_FEE_BPS.get(sell_ex, 10)
    wd = WITHDRAW_FEE.get(sym, 0)
    wd_bps = wd / buy_ask * 10000 if wd else 0
    net = gross_bps - fee_bps - wd_bps - SLIPPAGE_BPS
    return {"gross_bps": round(gross_bps, 2), "fee_bps": fee_bps,
            "wd_bps": round(wd_bps, 2), "net_bps": round(net, 2)}


def analyze(data: dict, threshold_bps: float = THRESHOLD_BPS) -> list:
    signals = []
    for sym, exs in data.items():
        pairs = [(a, exs[a], b, exs[b]) for a in exs for b in exs if a != b]
        for buy_ex, buy_d, sell_ex, sell_d in pairs:
            if buy_d["vol24h"] < MIN_LIQUIDITY_USDT or sell_d["vol24h"] < MIN_LIQUIDITY_USDT:
                continue
            c = net_bps(sym, buy_ex, buy_d["ask"], sell_ex, sell_d["bid"])
            if c["net_bps"] >= threshold_bps:
                signals.append({
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "symbol": sym,
                    "buy_at": buy_ex, "buy_ask": buy_d["ask"],
                    "sell_at": sell_ex, "sell_bid": sell_d["bid"],
                    **c,
                })
    signals.sort(key=lambda x: -x["net_bps"])
    return signals


def log_signals(signals: list):
    if not signals:
        return
    new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(signals[0].keys()))
        if new:
            w.writeheader()
        for s in signals:
            w.writerow(s)


# ---------------------------------------------------------------- 币股监控
def fetch_stock_chain_price(exchange: str = "gate") -> dict:
    """拉 gate 币股 ticker，返回 {pair: {"bid","ask","vol24h"}}"""
    out = {}
    try:
        ex = build_exchange(exchange)
        ex.load_markets()
        for pair in STOCKS:
            try:
                t = ex.fetch_ticker(pair)
                bid, ask = t.get("bid"), t.get("ask")
                if bid and ask:
                    out[pair] = {"bid": bid, "ask": ask, "vol24h": t.get("quoteVolume") or 0}
            except Exception:
                continue
    except Exception as e:
        print(f"  [!] {exchange} 币股拉取失败: {str(e)[:100]}", file=sys.stderr)
    return out


def fetch_us_stock_price() -> dict:
    """拉真实美股收盘/最新价（yfinance）。美股闭市时 = 最近收盘价。"""
    import yfinance as yf
    # yfinance 走环境变量代理（CN 网络必需）
    if os.environ.get("NO_PROXY") != "1":
        os.environ.setdefault("HTTPS_PROXY", PROXY)
        os.environ.setdefault("HTTP_PROXY", PROXY)
    out = {}
    for pair, us_sym in STOCKS.items():
        try:
            h = yf.Ticker(us_sym).history(period="1d")
            if len(h):
                out[pair] = {"us_price": float(h["Close"].iloc[-1]),
                             "us_ts": h.index[-1].strftime("%m-%d %H:%M")}
        except Exception:
            continue
    return out


def analyze_stocks() -> list:
    """币股 vs 真实美股偏离。正 = 币股溢价（gate 贵），负 = 折价（gate 便宜）。"""
    chain = fetch_stock_chain_price()
    us = fetch_us_stock_price()
    signals = []
    for pair, c in chain.items():
        if pair not in us:
            continue
        us_p = us[pair]["us_price"]
        # 用中间价对比美股，避免 bid/ask 制造假偏离
        mid = (c["bid"] + c["ask"]) / 2
        dev_bps = (mid - us_p) / us_p * 10000
        row = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pair": pair, "us_sym": STOCKS[pair],
            "chain_mid": round(mid, 2), "us_price": us_p,
            "dev_bps": round(dev_bps, 1),
            "us_ts": us[pair]["us_ts"],
            "vol24h": round(c["vol24h"]),
        }
        if abs(dev_bps) >= STOCK_DEVIATION_BPS:
            signals.append(row)
    signals.sort(key=lambda x: -abs(x["dev_bps"]))
    return signals


def log_stock_signals(signals: list):
    if not signals:
        return
    new = not STOCK_LOG_PATH.exists()
    with open(STOCK_LOG_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(signals[0].keys()))
        if new:
            w.writeheader()
        for s in signals:
            w.writerow(s)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="跑一次后退出")
    ap.add_argument("--watch", type=int, default=0, help="轮询间隔秒数（默认 0=单次）")
    ap.add_argument("--symbols", default=",".join(SYMBOLS), help="逗号分隔的币种")
    ap.add_argument("--threshold", type=float, default=THRESHOLD_BPS, help="净收益阈值 bps")
    ap.add_argument("--stocks", action="store_true", help="币股 vs 美股模式（gate xStocks vs yfinance）")
    ap.add_argument("--quiet", action="store_true", help="无信号时静默（cron watchdog 用）")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    threshold = args.threshold

    def tick():
        if args.stocks:
            signals = analyze_stocks()
            log_stock_signals(signals)
            if signals:
                print(f"\n=== {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC 币股 vs 美股偏离 ===")
                print(f"{'交易对':<14}{'gate中间价':>10}{'美股':>10}{'偏离bps':>9}  美股时点")
                for s in signals:
                    side = "溢价" if s["dev_bps"] > 0 else "折价"
                    print(f"{s['pair']:<14}{s['chain_mid']:>10.2f}{s['us_price']:>10.2f}"
                          f"{s['dev_bps']:>9.1f}  {s['us_ts']} ({side} {s['vol24h']:,}U)")
            elif not args.quiet:
                print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] 无 ≥{STOCK_DEVIATION_BPS}bps 币股偏离 "
                      f"({len(STOCKS)} 只)")
            return
        data = fetch_all(EXCHANGES, symbols)
        signals = analyze(data, threshold)
        log_signals(signals)
        if signals:
            print(f"\n=== {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC 跨所价差信号 ===")
            for s in signals:
                print(f"  {s['symbol']:<6} 买 {s['buy_at']:<8}@{s['buy_ask']:<12} → "
                      f"卖 {s['sell_at']:<8}@{s['sell_bid']:<12} "
                      f"毛利{s['gross_bps']}bps 净{s['net_bps']}bps "
                      f"(费{s['fee_bps']}+提币{s['wd_bps']}+滑点{SLIPPAGE_BPS})")
        elif not args.quiet:
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] 无 ≥{threshold}bps 信号 "
                  f"({len(symbols)} 币 × {len(EXCHANGES)} 所)")

    tick()
    if args.watch and not args.once:
        while True:
            time.sleep(args.watch)
            tick()


if __name__ == "__main__":
    main()
