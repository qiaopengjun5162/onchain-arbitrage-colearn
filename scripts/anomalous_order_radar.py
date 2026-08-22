#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CEX 异常挂单雷达（错误单套利线 · 第 1 档）

逻辑：扫描 Bybit/Binance 主流币现货深盘（limit 500），找出「远离中价的大挂单」：
  - 卖单远低于中价（折价卖单）= 有人愿意便宜出货 → 买它的人白赚
  - 买单远高于中价（溢价买单）= 有人愿意高价接货 → 卖它的人白赚
  - 严格信号：偏离中价 >= 2%（--dev-bps 200）且单笔名义金额 >= $5K（--min-notional 5000）
  - 弱信号（只落盘不推送）：>= 1% 且 >= $10K

用法：
  python anomalous_order_radar.py                          # 全量输出（调试）
  python anomalous_order_radar.py --quiet                  # watchdog：有严格信号才输出
  python anomalous_order_radar.py --symbols BTC,ETH,SOL    # 自定义币种
  python anomalous_order_radar.py --out /tmp/radar.png     # 图表路径

数据源：
  - Bybit v5 公开 API（orderbook spot, limit 500，无需 key）
  - Binance data-api 镜像（/api/v3/depth，不封）
历史记录：每次扫描的弱信号以上异常追加到 data/anomalous_order_scan.jsonl（用于统计频率）

部署：cron 每 10-15 分钟跑一次 --quiet，有信号 stdout 非空即推送
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
DEV_BPS = int(os.environ.get("DEV_BPS", "200"))          # 严格：偏离中价 ≥2%
MIN_NOTIONAL = float(os.environ.get("MIN_NOTIONAL", "5000"))  # 严格：名义 ≥$5K
SOFT_BPS = 100                                          # 弱信号：≥1%
SOFT_NOTIONAL = 3000.0                                  # 弱信号：≥$3K（落盘供频率统计）
VOL_MIN = float(os.environ.get("VOL_MIN", "1000000"))   # 24h 成交额 ≥$1M 才扫

DEFAULT_SYMBOLS = [
    # 主流
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "DOT",
    "SUI", "PEPE", "TON", "TRX", "LTC", "BCH", "NEAR", "APT", "ARB", "OP",
    # 中盘（错误单常见栖息地：流动性够但盘口深位稀疏）
    "INJ", "SEI", "TIA", "WLD", "BONK", "SHIB", "FLOKI", "JUP", "JTO",
    "PYTH", "WIF", "FIL", "AAVE", "UNI", "MKR", "ENA", "1INCH", "CRV",
    "GRT", "RUNE",
]

# matplotlib 中文字体
for f in ["PingFang SC", "Heiti SC", "Arial Unicode MS", "Songti SC"]:
    try:
        plt.rcParams["font.sans-serif"] = [f] + plt.rcParams["font.sans-serif"]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False


def http_json(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    return json.loads(opener.open(req, timeout=timeout).read())


def fetch_volumes(exchange):
    """{symbol: 24h quoteVolume}，失败返回空 dict（则不过滤）"""
    out = {}
    try:
        if exchange == "bybit":
            d = http_json("https://api.bybit.com/v5/market/tickers?category=spot")
            for t in d.get("result", {}).get("list", []):
                sym = t["symbol"]
                if sym.endswith("USDT"):
                    out[sym[:-4]] = float(t.get("turnover24h", 0))
        else:
            for t in http_json("https://data-api.binance.vision/api/v3/ticker/24hr"):
                sym = t["symbol"]
                if sym.endswith("USDT"):
                    out[sym[:-4]] = float(t.get("quoteVolume", 0))
    except Exception as e:
        print(f"[!] {exchange} 24h成交量拉取失败: {str(e)[:100]}", file=sys.stderr)
    return out


def fetch_orderbook(exchange, symbol, limit=500):
    """返回 (bids, asks)，各为 [(price, qty)]，按价格排序（bids 降序 / asks 升序）"""
    sym = f"{symbol}USDT"
    if exchange == "bybit":
        url = (f"https://api.bybit.com/v5/market/orderbook?category=spot"
               f"&symbol={sym}&limit={limit}")
        d = http_json(url)
        if d.get("retCode") != 0:
            return None, None
        res = d["result"]
        bids = [(float(b[0]), float(b[1])) for b in res.get("b", []) if float(b[1]) > 0]
        asks = [(float(a[0]), float(a[1])) for a in res.get("a", []) if float(a[1]) > 0]
    else:
        url = (f"https://data-api.binance.vision/api/v3/depth"
               f"?symbol={sym}&limit={limit}")
        d = http_json(url)
        bids = [(float(b[0]), float(b[1])) for b in d.get("bids", []) if float(b[1]) > 0]
        asks = [(float(a[0]), float(a[1])) for a in d.get("asks", []) if float(a[1]) > 0]
    return bids, asks


def scan_book(exchange, symbol, bids, asks):
    """扫一个订单簿，返回异常单列表 [{side, price, qty, notional, dev_bps}]"""
    if not bids or not asks:
        return []
    best_bid, best_ask = bids[0][0], asks[0][0]
    if best_bid >= best_ask:  # 交叉盘，跳过（另有信号价值，本轮不处理）
        return []
    mid = (best_bid + best_ask) / 2.0
    anomalies = []
    # 折价卖单：asks 中价格低于中价×(1-软阈值) 的挂单
    for price, qty in asks:
        dev = (mid - price) / mid * 1e4
        notional = price * qty
        if dev >= SOFT_BPS and notional >= SOFT_NOTIONAL:
            anomalies.append({
                "exchange": exchange, "symbol": symbol, "side": "ASK(折价卖单)",
                "price": price, "qty": qty, "notional": notional,
                "dev_bps": round(dev, 1),
                "signal": dev >= DEV_BPS and notional >= MIN_NOTIONAL,
            })
    # 溢价买单：bids 中价格高于中价×(1+软阈值) 的挂单
    for price, qty in bids:
        dev = (price - mid) / mid * 1e4
        notional = price * qty
        if dev >= SOFT_BPS and notional >= SOFT_NOTIONAL:
            anomalies.append({
                "exchange": exchange, "symbol": symbol, "side": "BID(溢价买单)",
                "price": price, "qty": qty, "notional": notional,
                "dev_bps": round(dev, 1),
                "signal": dev >= DEV_BPS and notional >= MIN_NOTIONAL,
            })
    return anomalies


def log_history(anomalies, path):
    """弱信号以上全部落盘，便于统计频率"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(path, "a") as f:
            for a in anomalies:
                a["ts"] = ts
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[!] 历史落盘失败: {e}", file=sys.stderr)


def draw_chart(anomalies, out_path):
    """散点图：x=币种, y=偏离bps, 点大小∝名义金额, 红=折价卖单 绿=溢价买单"""
    if not anomalies:
        return False
    fig, ax = plt.subplots(figsize=(12, 6))
    for a in anomalies:
        color = "#d64541" if a["side"].startswith("ASK") else "#27ae60"
        marker = "v" if a["side"].startswith("ASK") else "^"
        ax.scatter(a["symbol"], a["dev_bps"], s=min(a["notional"] / 100, 1500),
                   color=color, marker=marker, alpha=0.8,
                   edgecolors="white", linewidths=0.5, zorder=3)
        ax.annotate(f"{a['exchange']} {a['notional']:,.0f}U",
                    (a["symbol"], a["dev_bps"]),
                    textcoords="offset points", xytext=(0, 6), fontsize=8,
                    ha="center")
    ax.axhline(DEV_BPS, color="#e67e22", ls="--", lw=1)
    ax.text(0.01, DEV_BPS + 2, f"严格线 {DEV_BPS}bps", fontsize=9, color="#e67e22")
    ax.set_ylabel("偏离中价 (bps)")
    ax.set_title(f"CEX 异常挂单雷达 {dt.datetime.now():%m-%d %H:%M} UTC "
                 f"（红▽=折价卖单 绿△=溢价买单, 点越大金额越大）")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return True


def main():
    ap = argparse.ArgumentParser(description="CEX 异常挂单雷达")
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--depth", type=int, default=500)
    ap.add_argument("--dev-bps", type=int, default=DEV_BPS)
    ap.add_argument("--min-notional", type=float, default=MIN_NOTIONAL)
    ap.add_argument("--out", default="/tmp/anomalous_order_radar.png")
    ap.add_argument("--quiet", action="store_true",
                    help="watchdog：无严格信号则静默（空输出）")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    strict_bps, strict_notional = args.dev_bps, args.min_notional

    all_anomalies, errors = [], []
    for ex in ["bybit", "binance"]:
        vols = fetch_volumes(ex)
        for sym in symbols:
            if vols and vols.get(sym, 0) < VOL_MIN:
                continue  # 低流动性币不扫（除非 volume 数据缺失）
            try:
                bids, asks = fetch_orderbook(ex, sym, limit=args.depth)
                if bids is None:
                    errors.append(f"{ex}:{sym} 无订单簿")
                    continue
                all_anomalies.extend(scan_book(ex, sym, bids, asks))
            except Exception as e:
                errors.append(f"{ex}:{sym} {str(e)[:60]}")
    # 按偏离度排序
    all_anomalies.sort(key=lambda a: a["dev_bps"], reverse=True)

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "data", "anomalous_order_scan.jsonl")
    log_history(all_anomalies, log_path)

    strict = [a for a in all_anomalies if a["signal"]]
    soft_only = [a for a in all_anomalies if not a["signal"]]

    if args.quiet:
        # watchdog：只输出严格信号
        if strict:
            print(f"🔴 CEX异常挂单雷达: {len(strict)} 个严格信号 "
                 f"({len(symbols)}币×2所扫描, 弱信号{len(soft_only)}个)")
            for a in strict[:15]:
                print(f"  {a['exchange']:<8} {a['symbol']:<6} {a['side']:<10} "
                      f"偏离{a['dev_bps']:>6.1f}bps  名义{a['notional']:>10,.0f}U")
        return

    # 全量输出（调试）
    print(f"=== CEX 异常挂单雷达 {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC ===")
    print(f"扫描 {len(symbols)} 币 × 2 所（深度{args.depth}）| 24h成交额≥${VOL_MIN:,.0f} | "
          f"严格线: 偏离≥{strict_bps}bps & 名义≥${strict_notional:,.0f}")
    print(f"严格信号: {len(strict)} | 弱信号: {len(soft_only)} | 失败: {len(errors)}")
    if errors:
        print("失败:", "; ".join(errors[:5]))
    print()
    if strict:
        print("【严格信号】偏离≥2% 且 名义≥$5K —— 值得盯的猎物")
        for a in strict:
            print(f"  {a['exchange']:<8} {a['symbol']:<6} {a['side']:<10} "
                  f"价{a['price']:<14} 量{a['qty']:<14} 名义{a['notional']:>12,.0f}U "
                  f"偏离{a['dev_bps']:>6.1f}bps")
    elif soft_only:
        print("【弱信号】偏离≥1% 或 名义≥$10K —— 接近但未过线")
        for a in soft_only[:15]:
            print(f"  {a['exchange']:<8} {a['symbol']:<6} {a['side']:<10} "
                  f"价{a['price']:<14} 名义{a['notional']:>12,.0f}U "
                  f"偏离{a['dev_bps']:>6.1f}bps")
    else:
        print("无异常 —— 市场很干净，没有明显的错误挂单")

    if draw_chart(all_anomalies, args.out):
        print(f"\n图表已保存: {args.out}")
    print(f"\n历史已追加: {os.path.abspath(log_path)}")


if __name__ == "__main__":
    main()
