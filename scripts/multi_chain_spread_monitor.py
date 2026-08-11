#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多链币价差监控 v0 (multi_chain_spread_monitor.py)
==================================================
思路（Paxon 2026-08-11）：找多链币 → 监控多链价格 → 判断价差搬砖。

读取：
- DEX：BSC PancakeSwap V3 / ETH Uniswap V3 池 slot0（sqrtPriceX96 → 价格，Decimals 自动换算）
- CEX：Gate/OKX/Bitget 公开 ticker API（ccxt 可选）

输出：
- 每币每市场价格 + 两两价差 bps（对链上最优买/卖腿）
- 净收益判断：价差 − 桥费 − gas − 手续费（≥ MIN_NET_BPS 才报，watchdog 静默）
- 落盘 data/multichain_spread_series.csv（时间序列，可再生不入库）

用法：
  python multi_chain_spread_monitor.py            # 单次扫描
  python multi_chain_spread_monitor.py --watch 60 # 循环
  python multi_chain_spread_monitor.py --watchdog # cron 静默，净价差达标才报
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
import ssl
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 12

ETH_RPCS = ["https://1rpc.io/eth", "https://eth.drpc.org", "https://rpc.flashbots.net"]
BSC_RPC = "https://bsc-dataseed1.binance.org"
Q96 = Decimal(2) ** 96

# ---- 币表配置（多链币：同代币跨链，BSC/ETH 各有官方池） ----
# 每项：symbol -> {BSC: [(pool, token0_dec, token1_dec, flip)], ETH: [...], cex_symbol}
# flip=True 表示 token0=USDT token1=币，价格=1/raw；False 表示 token0=币 token1=USDT/ETH
COINS = {
    "DOS": {
        "BSC": [("0xCbeAad783FFD2CeA125E9D9B2Ec21E639d20Fa59", 18, 18, True)],   # PancakeSwap V3 0.01%
        "ETH": [("0x47A853718Cf0d9E1506f01e666780B899B193214", 18, 6, False)],  # Uniswap V3 USDT 1%
        "cex": ["DOS_USDT"],
    },
    # 候选扩展（OFT 多链币，BSC/ETH 官方池待逐个验证后启用）
    # "ZRO": {"BSC": [...], "ETH": [...], "cex": ["ZRO_USDT"]},
}

MIN_NET_BPS = 300    # 净价差 ≥3% 才算可搬砖（成本已扣）
MAX_SINGLE_USD = 500 # 单笔上限（纸面约束）
SERIES_PATH = Path(__file__).resolve().parent.parent / "data" / "multichain_spread_series.csv"

# 桥费（USD 近似，PDF 实测：ETH→BSC ~$0.02，BSC→ETH ~$0.69；随 gas 波动）
BRIDGE_FEE_USD = {"BSC_TO_ETH": 0.69, "ETH_TO_BSC": 0.02}
GAS_LEG_USD = {"BSC": 0.05, "ETH": 1.0}
DEX_FEE_BPS = {"BSC": 1, "ETH": 100}  # 0.01% / 1% 池


def _req(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode()


def rpc(url, method, params, retries=3):
    for i in range(retries):
        try:
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
            req = urllib.request.Request(url, data=body,
                                         headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode()).get("result")
        except Exception:
            time.sleep(0.5 * (i + 1))
    return None


def pool_price(url, pool, t0_dec, t1_dec, flip):
    slot = rpc(url, "eth_call", [{"to": pool, "data": "0x3850c7bd"}, "latest"])
    if not slot:
        return None
    s = Decimal(int(slot[2:66], 16))
    raw = (s / Q96) ** 2                     # token1/token0 raw
    price = raw * Decimal(10) ** (t0_dec - t1_dec)  # 调整 decimals
    return float(1 / price if flip else price)


def read_dex(symbol, cfg):
    prices = {}
    for chain, pools in [("BSC", cfg.get("BSC", [])), ("ETH", cfg.get("ETH", []))]:
        url = BSC_RPC if chain == "BSC" else ETH_RPCS[0]
        best = None
        for pool, d0, d1, flip in pools:
            p = pool_price(url, pool, d0, d1, flip)
            if p and (best is None or abs(p - 1) < abs(best - 1)):  # 取最接近 1 的？不，取全部记录
                best = p
        if best:
            prices[chain] = best
    return prices


def read_cex(symbol):
    """Gate/OKX/Bitget 公开 ticker（ccxt 失败时的轻量替代）"""
    prices = {}
    try:
        d = json.loads(_req("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=" + symbol))
        if d:
            prices["Gate"] = float(d[0]["last"])
    except Exception:
        pass
    try:
        d = json.loads(_req("https://api.bitget.com/api/v2/spot/market/tickers?symbol=" + symbol.replace("_", "")))
        for t in d.get("data", []):
            if t.get("symbol") == symbol.replace("_", ""):
                prices["Bitget"] = float(t["last"])
                break
    except Exception:
        pass
    return prices


def spread_bps(a, b):
    return (b - a) / a * 10000 if a else None


def estimate_net(chain_buy, chain_sell, price_buy, price_sell, dex_fee_bps, bridge_usd, gas_usd, notional=500):
    """净收益估算（USD）：价差 − DEX 手续费 − 桥费 − 两链 gas − 滑点（简化按价差 10% 计提）"""
    gross = (price_sell - price_buy) / price_buy * notional
    fee = notional * dex_fee_bps / 10000
    slippage = gross * 0.10
    net = gross - fee - bridge_usd - gas_usd - slippage
    net_bps = net / notional * 10000
    return net, net_bps


def tick(watchdog=False):
    rows = []
    alerts = []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    for symbol, cfg in COINS.items():
        dex = read_dex(symbol, cfg)
        cex = read_cex(symbol)
        markets = {**dex, **cex}
        if len(markets) < 2:
            continue
        # 两两价差
        names = list(markets.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                sp = spread_bps(markets[a], markets[b])
                if sp is None:
                    continue
                # 方向：买低卖高。判断桥方向
                if markets[a] < markets[b]:
                    low_name, high_name = a, b
                else:
                    low_name, high_name = b, a
                # 桥费：低→高 跨链方向（BSC↔ETH）
                low_chain = "BSC" if low_name == "BSC" else "ETH"
                bridge = BRIDGE_FEE_USD["BSC_TO_ETH"] if (low_name == "BSC" and high_name == "ETH") else BRIDGE_FEE_USD["ETH_TO_BSC"]
                net, net_bps = estimate_net(low_name, high_name, markets[low_name], markets[high_name],
                                            DEX_FEE_BPS[high_name if high_name in DEX_FEE_BPS else "BSC"],
                                            bridge, GAS_LEG_USD[low_chain])
                row = {"ts": ts, "symbol": symbol, "pair": f"{a}↔{b}", "spread_bps": round(sp, 1),
                       "net_bps": round(net_bps, 1), "low": low_name, "high": high_name,
                       "price_low": round(markets[low_name], 6), "price_high": round(markets[high_name], 6)}
                rows.append(row)
                if net_bps >= MIN_NET_BPS:
                    alerts.append(f"🚨 {symbol} {low_name}→{high_name} 净价差 {net_bps:.0f}bps（毛 {sp:.0f}bps）："
                                  f"{markets[low_name]:.4f} 买 → 桥 → {markets[high_name]:.4f} 卖")
    # 落盘
    try:
        SERIES_PATH.parent.mkdir(exist_ok=True)
        new = not SERIES_PATH.exists()
        with open(SERIES_PATH, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["ts", "symbol", "pair", "spread_bps", "net_bps", "low", "high", "price_low", "price_high"])
            if new:
                w.writeheader()
            w.writerows(rows)
    except Exception:
        pass
    if watchdog:
        for a in alerts:
            print(a)
        return 0
    print(f"\n=== 多链价差监控 @ {ts} ===")
    print(f"{'币':<6}{'配对':<14}{'毛价差bps':>10}{'净价差bps':>10}  买→卖")
    for r in sorted(rows, key=lambda x: -x["net_bps"]):
        mark = " ⚠️" if r["net_bps"] >= MIN_NET_BPS else ""
        print(f"{r['symbol']:<6}{r['pair']:<14}{r['spread_bps']:>10.1f}{r['net_bps']:>10.1f}  {r['low']}→{r['high']}{mark}")
    if not rows:
        print("（无可用价格对）")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--watchdog", action="store_true")
    args = ap.parse_args()
    code = tick(watchdog=args.watchdog)
    if args.watch:
        while True:
            time.sleep(args.watch)
            tick(watchdog=args.watchdog)
    sys.exit(code)
