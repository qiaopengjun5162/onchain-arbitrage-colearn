#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CEX 异常挂单雷达 v2（错误单套利线 · 第 1 档）— 别人的错误单 = 我们的猎物

逻辑：拉 Bybit 永续(linear) + Binance 现货深盘（limit 500），分三级找异常：
  L1 穿价单：ask ≤ best_bid —— 挂着就是免费午餐，可瞬间成交套利（最稀有）
  L2 近中价偏离：卖单低于中价 / 买单高于中价（未穿价）—— 准免费午餐
     （1INCH 帖案例的静止版：有人愿意折价出货 / 溢价接货）
  L3 远墙（僵尸单）：|偏离中价| ≥ 2% 且 名义 ≥ $5K —— 常驻结构（鲸鱼墙），
     不是「错误」而是「触发燃料」：价格打过去时成批成交 → 只落盘不推送，供趋势分析

实测（2026-08-22）：L3 远墙常态存在（SOL $918K 卖墙@+5%、SUI $311K 卖墙@+5%、
  1INCH 多道 +44~96% 远墙）；L1/L2 平静市况几乎为 0 → 推送线 = L1/L2。

用法：
  python anomalous_order_radar.py                          # 全量输出（调试）
  python anomalous_order_radar.py --quiet                  # watchdog：L1/L2 才输出
  python anomalous_order_radar.py --symbols BTC,ETH,SOL    # 自定义币种
  python anomalous_order_radar.py --out /tmp/radar.png     # 图表路径

数据源：
  - Bybit v5 公开 API（category=linear 永续, limit 500，无需 key）
  - Binance data-api 镜像（/api/v3/depth，不封）；代理自动探测（先直连后代理）
历史落盘：L2/L3 → data/anomalous_order_scan.jsonl（频率统计）；L3 远墙另存
          data/anomalous_walls.jsonl（墙出现/消失趋势）

部署：cron 每 15 分钟 --quiet，wrapper 见 ~/.hermes/scripts/run_anomalous_order_radar.sh
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
WALL_DEV_PCT = float(os.environ.get("WALL_DEV_PCT", "2.0"))      # L3 远墙偏离 %
WALL_NOTIONAL = float(os.environ.get("WALL_NOTIONAL", "5000"))   # L3 远墙名义 $
L2_NOTIONAL = float(os.environ.get("L2_NOTIONAL", "3000"))       # L2 近中价名义 $
L1_NOTIONAL = float(os.environ.get("L1_NOTIONAL", "1000"))       # L1 穿价名义 $
VOL_MIN = float(os.environ.get("VOL_MIN", "1000000"))            # 24h 成交额 ≥$1M 才扫

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


def http_json(url, use_proxy=None, timeout=25):
    """GET JSON；use_proxy=None 时自动探测（先直连后代理）。"""
    seq = [use_proxy] if use_proxy is not None else [False, True]
    last_err = None
    for px in seq:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            if px:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
            else:
                opener = urllib.request.build_opener()
            return json.loads(opener.open(req, timeout=timeout).read())
        except Exception as e:
            last_err = e
    raise RuntimeError(f"HTTP 拉取失败: {last_err}")


def fetch_volumes(exchange):
    """{symbol: 24h quoteVolume}，失败返回空 dict（则不过滤）"""
    out = {}
    try:
        if exchange == "bybit":
            d = http_json("https://api.bybit.com/v5/market/tickers?category=linear",
                          use_proxy=True)
            for t in d.get("result", {}).get("list", []):
                sym = t["symbol"]
                if sym.endswith("USDT"):
                    out[sym[:-4]] = float(t.get("turnover24h", 0))
        else:
            for t in http_json("https://data-api.binance.vision/api/v3/ticker/24hr",
                               use_proxy=False):
                sym = t["symbol"]
                if sym.endswith("USDT"):
                    out[sym[:-4]] = float(t.get("quoteVolume", 0))
    except Exception as e:
        print(f"[!] {exchange} 24h成交量拉取失败: {str(e)[:100]}", file=sys.stderr)
    return out


def fetch_orderbook(exchange, symbol, limit=500):
    """返回 (bids, asks)，各为 [(price, qty)] 按价格排序（bids 降 / asks 升）"""
    sym = f"{symbol}USDT"
    if exchange == "bybit":
        d = http_json(f"https://api.bybit.com/v5/market/orderbook"
                      f"?category=linear&symbol={sym}&limit={limit}", use_proxy=True)
        if d.get("retCode") != 0:
            return None, None
        res = d["result"]
        bids = [(float(b[0]), float(b[1])) for b in (res.get("bids") or res.get("b", []))]
        asks = [(float(a[0]), float(a[1])) for a in (res.get("asks") or res.get("a", []))]
    else:
        d = http_json(f"https://data-api.binance.vision/api/v3/depth"
                      f"?symbol={sym}&limit={limit}", use_proxy=False)
        bids = [(float(b[0]), float(b[1])) for b in d.get("bids", [])]
        asks = [(float(a[0]), float(a[1])) for a in d.get("asks", [])]
    bids = [(p, q) for p, q in bids if q > 0]
    asks = [(p, q) for p, q in asks if q > 0]
    return bids, asks


def scan_book(exchange, symbol, bids, asks):
    """扫一个订单簿 → (anomalies, summary)。anomaly: {level, side, price, qty,
    notional, dev_pct, tag, signal}"""
    if not bids or not asks:
        return [], None
    best_bid, best_ask = bids[0][0], asks[0][0]
    mid = (best_bid + best_ask) / 2.0
    anomalies = []

    def add(level, side, px, qty, tag, signal):
        anomalies.append({
            "exchange": exchange, "symbol": symbol,
            "level": level, "side": side, "price": px, "qty": qty,
            "notional": px * qty, "dev_pct": (px - mid) / mid * 100.0,
            "tag": tag, "signal": signal,
        })

    # L1 穿价单：ask ≤ best_bid（挂着就是免费午餐）
    for px, qty in asks:
        if px <= best_bid and px * qty >= L1_NOTIONAL:
            add(1, "ASK", px, qty, "穿价卖单→瞬间可吃", True)
    # L2 近中价偏离：卖单低于中价 / 买单高于中价（未穿价，≥$3K）
    for px, qty in asks:
        if best_bid < px < mid and px * qty >= L2_NOTIONAL:
            add(2, "ASK", px, qty, "低于中价的卖单", True)
    for px, qty in bids:
        if mid < px < best_ask and px * qty >= L2_NOTIONAL:
            add(2, "BID", px, qty, "高于中价的买单", True)
    # L3 远墙：|偏离| ≥2% 且 ≥$5K（常驻结构，只落盘不推送）
    for px, qty in asks:
        if (px - mid) / mid * 100.0 >= WALL_DEV_PCT and px * qty >= WALL_NOTIONAL:
            add(3, "ASK", px, qty, "远价卖墙(触发燃料)", False)
    for px, qty in bids:
        if (mid - px) / mid * 100.0 >= WALL_DEV_PCT and px * qty >= WALL_NOTIONAL:
            add(3, "BID", px, qty, "远价买墙(触发燃料)", False)

    anomalies.sort(key=lambda a: (a["level"], -a["notional"]))
    summary = {"exchange": exchange, "symbol": symbol, "mid": mid,
               "best_bid": best_bid, "best_ask": best_ask,
               "spread_pct": (best_ask - best_bid) / mid * 100.0,
               "n_asks": len(asks), "n_bids": len(bids)}
    return anomalies, summary


def _rotate(path, max_lines=3000, keep=500):
    """防止 jsonl 无限膨胀：超过 max_lines 行时保留最近 keep 行。"""
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            with open(path, "w") as f:
                f.writelines(lines[-keep:])
    except FileNotFoundError:
        pass
    except Exception:
        pass


def log_history(anomalies, path):
    """L2 近中价偏离落盘 data/anomalous_order_scan.jsonl（错误单频率统计用）。
    L3 远墙不在此文件（数量巨大，走 anomalous_walls.jsonl 聚合）。"""
    l2 = [a for a in anomalies if a["level"] == 2]
    if not l2:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(path, "a") as f:
            for a in l2:
                row = dict(a)
                row["ts"] = ts
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        _rotate(path)
    except Exception as e:
        print(f"[!] 历史落盘失败: {e}", file=sys.stderr)


def log_walls(all_anomalies, path):
    """L3 远墙按 (币,所) 聚合 → data/anomalous_walls.jsonl，每币每所一行 top10。
    供「墙出现/消失/移动」趋势分析（墙=触发燃料，价格打过去时成批成交）。"""
    groups = {}
    for a in all_anomalies:
        if a["level"] != 3:
            continue
        groups.setdefault((a["exchange"], a["symbol"]), []).append(a)
    if not groups:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(path, "a") as f:
            for (ex, sym), walls in groups.items():
                walls.sort(key=lambda w: -w["notional"])
                f.write(json.dumps({
                    "ts": ts, "symbol": sym, "exchange": ex,
                    "n_walls": len(walls),
                    "mid": walls[0].get("mid"),
                    "walls": [{"side": w["side"], "px": w["price"], "qty": w["qty"],
                               "notional": w["notional"],
                               "dev_pct": round(w["dev_pct"], 2)}
                              for w in walls[:10]],
                }, ensure_ascii=False) + "\n")
        _rotate(path, max_lines=5000, keep=800)
    except Exception as e:
        print(f"[!] 远墙落盘失败: {e}", file=sys.stderr)


def fmt(a):
    side = "卖" if a["side"] == "ASK" else "买"
    return (f"  L{a['level']} {a['exchange']:<7} {a['symbol']:<6} {side}单 "
            f"{a['price']:.6g} × {a['qty']:g} = ${a['notional']:,.0f}  "
            f"(偏离中价 {a['dev_pct']:+.2f}%)  {a['tag']}")


def draw_chart(anomalies, out_path, top_walls_per_sym=5):
    """散点图：x=币种, y=偏离%, 点大小∝名义。画 L1/L2 全部 + 每币每所 top5 远墙。"""
    alerts = [a for a in anomalies if a["level"] <= 2]
    walls = [a for a in anomalies if a["level"] == 3]
    walls.sort(key=lambda w: -w["notional"])
    seen, picked = {}, []
    for w in walls:
        k = (w["exchange"], w["symbol"])
        if seen.get(k, 0) >= top_walls_per_sym:
            continue
        seen[k] = seen.get(k, 0) + 1
        picked.append(w)
    pts = alerts + picked
    if not pts:
        return False
    fig, ax = plt.subplots(figsize=(12, 6))
    for a in pts:
        if a["level"] == 1:
            color = "#8e44ad"
        elif a["level"] == 2:
            color = "#d64541" if a["side"] == "ASK" else "#27ae60"
        else:
            color = "#95a5a6"
        marker = "v" if a["side"] == "ASK" else "^"
        ax.scatter(a["symbol"], a["dev_pct"], s=min(a["notional"] / 80, 1500),
                   color=color, marker=marker, alpha=0.8,
                   edgecolors="white", linewidths=0.5, zorder=3)
        ax.annotate(f"{a['exchange'][:3]} {a['notional']:,.0f}U",
                    (a["symbol"], a["dev_pct"]),
                    textcoords="offset points", xytext=(0, 6), fontsize=8,
                    ha="center")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_ylabel("偏离中价 (%)")
    ax.set_title(f"CEX 异常挂单雷达 {dt.datetime.now():%m-%d %H:%M} UTC "
                 f"（紫▽=L1穿价 红▽/绿△=L2错误单 灰=远墙top5, 点越大金额越大）")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return True


def main():
    ap = argparse.ArgumentParser(description="CEX 异常挂单雷达 v2")
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--depth", type=int, default=500)
    ap.add_argument("--out", default="/tmp/anomalous_order_radar.png")
    ap.add_argument("--quiet", action="store_true",
                    help="watchdog：仅 L1/L2 真错误单才输出（静默=无信号）")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    all_anomalies, summaries, errors = [], {}, []
    for ex in ["bybit", "binance"]:
        vols = fetch_volumes(ex)
        for sym in symbols:
            if vols and vols.get(sym, 0) < VOL_MIN:
                continue
            try:
                bids, asks = fetch_orderbook(ex, sym, limit=args.depth)
                if bids is None:
                    errors.append(f"{ex}:{sym} 无订单簿")
                    continue
                anom, sm = scan_book(ex, sym, bids, asks)
                all_anomalies.extend(anom)
                if sm:
                    summaries[(ex, sym)] = sm
            except Exception as e:
                errors.append(f"{ex}:{sym} {str(e)[:60]}")

    base = os.path.dirname(os.path.abspath(__file__))
    log_history(all_anomalies, os.path.join(base, "..", "data", "anomalous_order_scan.jsonl"))
    log_walls(all_anomalies, os.path.join(base, "..", "data", "anomalous_walls.jsonl"))

    alerts = [a for a in all_anomalies if a["signal"]]
    walls = [a for a in all_anomalies if a["level"] == 3]
    wall_syms = sorted({(a["exchange"], a["symbol"]) for a in walls})

    if args.quiet:
        if alerts:
            print(f"🔴 CEX异常挂单雷达: {len(alerts)} 个错误单信号 "
                 f"(扫{len(symbols)}币×2所, 远墙{len(walls)}道已落盘)")
            for a in alerts[:20]:
                print(fmt(a))
        return

    print(f"=== CEX 异常挂单雷达 v2 {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC ===")
    print(f"扫描 {len(symbols)} 币 × 2 所（深度{args.depth}）| 24h成交额≥${VOL_MIN:,.0f} | "
          f"推送线 L1穿价≥${L1_NOTIONAL:,.0f} / L2近中价≥${L2_NOTIONAL:,.0f} | "
          f"L3远墙≥{WALL_DEV_PCT}%/${WALL_NOTIONAL:,.0f} 只落盘")
    print(f"L1/L2 错误单: {len(alerts)} | 远墙币种×所: {len(wall_syms)} | 失败: {len(errors)}")
    if errors:
        print("失败:", "; ".join(errors[:5]))
    print()
    if alerts:
        print("【错误单信号】L1 穿价 / L2 近中价偏离 —— 值得盯的猎物")
        for a in alerts[:20]:
            print(fmt(a))
    else:
        print("无 L1/L2 错误单 —— 市场干净，没有明显的错误挂单")
    if walls:
        print(f"\n【L3 远墙】覆盖 {len(wall_syms)} 个币×所（常驻结构，仅落盘供趋势分析）top 12：")
        top_walls = sorted(walls, key=lambda w: -w["notional"])[:12]
        for a in top_walls:
            print(fmt(a))
    if draw_chart(all_anomalies, args.out):
        print(f"\n图表已保存: {args.out}")
    print(f"\n历史已追加: data/anomalous_order_scan.jsonl + data/anomalous_walls.jsonl")


if __name__ == "__main__":
    main()
