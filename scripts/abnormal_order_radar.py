#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CEX 异常挂单雷达（watchdog 模式）— 别人的错误单 = 我们的猎物

逻辑：拉主流币 Bybit/Binance 深盘（limit=500），找三类异常：
  1. 穿价单（crossed）：ask ≤ best_bid —— 挂着就是免费午餐，可瞬间成交套利
  2. 低于中价的卖单 / 高于中价的买单：偏离 mid 但没穿价 —— 准免费午餐（帖子 1INCH 案例的静止版）
  3. 远价大单（僵尸单）：|偏离中价| ≥ 阈值 且 金额 ≥ 阈值 —— 未来暴涨/暴跌的触发燃料
--quiet 模式（watchdog）：无异常 → 空输出（静默）；有异常 → 输出候选清单

用法：
  python abnormal_order_radar.py                           # 全量输出（调试）
  python abnormal_order_radar.py --quiet                   # watchdog：有信号才输出
  python abnormal_order_radar.py --chart /tmp/radar.png    # 附带深盘图示（top 4 异常）
  python abnormal_order_radar.py --symbols BTC,ETH,SOL     # 只扫指定币

部署：cron 每 15-30 分钟 --quiet，wrapper 见 run_abnormal_radar.sh
数据源：Bybit v5 public API（linear 永续）+ Binance data-api 镜像（现货）
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
MIN_DEV_PCT = float(os.environ.get("MIN_DEV_PCT", "2.0"))      # 远价阈值 %
MIN_NOTIONAL = float(os.environ.get("MIN_NOTIONAL", "5000"))   # 金额阈值 USDT
WALLS_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "data", "abnormal_walls.jsonl")

SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX",
           "LINK", "PEPE", "WIF", "TON", "TRX", "SHIB", "ARB", "OP",
           "LTC", "ATOM", "SUI", "1INCH"]


def http_json(url, use_proxy=None, timeout=20):
    """GET JSON，proxy 为 None 时自动探测（先直连后代理 / 先代理后直连）。"""
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


def fetch_bybit_book(sym: str):
    """Bybit linear 永续深盘。返回 {"bids": [(px, qty)], "asks": [(px, qty)]}。"""
    url = (f"https://api.bybit.com/v5/market/orderbook?category=linear"
           f"&symbol={sym}USDT&limit=500")
    d = http_json(url, use_proxy=True)
    if d.get("retCode") != 0:
        raise RuntimeError(f"bybit retCode={d.get('retCode')} {d.get('retMsg')}")
    r = d["result"]
    # Bybit v5 orderbook 返回键是 b/a（旧文档写法 bids/asks 也兼容处理）
    bids = r.get("bids") or r.get("b", [])
    asks = r.get("asks") or r.get("a", [])
    return {
        "bids": [(float(b[0]), float(b[1])) for b in bids],
        "asks": [(float(a[0]), float(a[1])) for a in asks],
    }


def fetch_binance_book(sym: str):
    """Binance 现货深盘（data-api 镜像，不封）。"""
    url = f"https://data-api.binance.vision/api/v3/depth?symbol={sym}USDT&limit=500"
    d = http_json(url, use_proxy=False)
    return {
        "bids": [(float(b[0]), float(b[1])) for b in d["bids"]],
        "asks": [(float(a[0]), float(a[1])) for a in d["asks"]],
    }


def scan_book(sym: str, venue: str, book: dict, min_dev_pct: float, min_notional: float):
    """扫描单个深盘，返回 (anomalies, summary)。"""
    bids, asks = book["bids"], book["asks"]
    if not bids or not asks:
        return [], None
    best_bid, best_ask = bids[0][0], asks[0][0]
    mid = (best_bid + best_ask) / 2.0
    anomalies = []  # (level, side, px, qty, notional, dev_pct, tag)

    def dev_pct(px, mid):
        return (px - mid) / mid * 100.0

    # 1) 穿价：ask ≤ best_bid
    for px, qty in asks:
        if px <= best_bid:
            notional = px * qty
            anomalies.append((1, "ASK", px, qty, notional,
                              dev_pct(px, mid), "穿价卖单→瞬间可吃"))
    # 2) 低于中价的卖单 / 高于中价的买单（未穿价）
    for px, qty in asks:
        if best_bid < px < mid and px * qty >= min_notional:
            anomalies.append((2, "ASK", px, qty, px * qty,
                              dev_pct(px, mid), "低于中价的卖单"))
    for px, qty in bids:
        if mid < px < best_ask and px * qty >= min_notional:
            anomalies.append((2, "BID", px, qty, px * qty,
                              dev_pct(px, mid), "高于中价的买单"))
    # 3) 远价大单（僵尸单）
    for px, qty in asks:
        d = abs(dev_pct(px, mid))
        if d >= min_dev_pct and px * qty >= min_notional:
            anomalies.append((3, "ASK", px, qty, px * qty, dev_pct(px, mid),
                              "远价卖墙(触发燃料)"))
    for px, qty in bids:
        d = abs(dev_pct(px, mid))
        if d >= min_dev_pct and px * qty >= min_notional:
            anomalies.append((3, "BID", px, qty, px * qty, dev_pct(px, mid),
                              "远价买墙(触发燃料)"))

    anomalies.sort(key=lambda a: (-a[0], -a[4]))
    summary = {"sym": sym, "venue": venue, "mid": mid, "best_bid": best_bid,
               "best_ask": best_ask, "spread_pct": (best_ask - best_bid) / mid * 100.0,
               "n_asks": len(asks), "n_bids": len(bids), "anomalies": anomalies}
    return anomalies, summary


def format_anomaly(a, mid):
    level, side, px, qty, notional, dev, tag = a
    side_cn = "卖" if side == "ASK" else "买"
    return (f"  L{level} {side_cn}单 {px:.6g} × {qty:g} = ${notional:,.0f}"
            f"  (偏离中价 {dev:+.2f}%)  {tag}")


def has_alert(anomalies):
    """quiet 模式的告警判定：只报 L1/L2 真错误单（穿价/低于中价）。
    L3 远墙是常驻结构（鲸鱼墙），每次都在 ≠ 信号，只落盘不做推送。"""
    return any(a[0] <= 2 for a in anomalies)


def log_walls(results, path):
    """把 L3 远墙快照落盘（jsonl），供未来的「墙出现/消失」趋势分析。"""
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = dt.datetime.now().isoformat(timespec="seconds")
    with open(path, "a") as f:
        for sym, venue, anomalies, sm in results:
            walls = [{"side": a[1], "px": a[2], "qty": a[3], "notional": a[4],
                      "dev_pct": round(a[5], 2), "tag": a[6]}
                     for a in anomalies if a[0] == 3][:10]
            if walls:
                f.write(json.dumps({"ts": ts, "sym": sym, "venue": venue,
                                    "mid": sm["mid"], "walls": walls},
                                   ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    ap.add_argument("--exchanges", default="bybit,binance",
                    help="逗号分隔：bybit/binance")
    ap.add_argument("--min-dev", type=float, default=MIN_DEV_PCT)
    ap.add_argument("--min-notional", type=float, default=MIN_NOTIONAL)
    ap.add_argument("--quiet", action="store_true", help="watchdog：无异常则空输出")
    ap.add_argument("--chart", default=None, help="输出图示路径（top 4 异常币）")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    exs = [e.strip().lower() for e in args.exchanges.split(",") if e.strip()]
    fetchers = {"bybit": fetch_bybit_book, "binance": fetch_binance_book}

    results = []  # (sym, venue, anomalies, summary)
    errors = []
    for sym in symbols:
        for ex in exs:
            try:
                book = fetchers[ex](sym)
                anomalies, summary = scan_book(sym, ex.upper(), book,
                                               args.min_dev, args.min_notional)
                if summary:
                    results.append((sym, ex.upper(), anomalies, summary))
            except Exception as e:
                errors.append(f"{sym}@{ex}: {str(e)[:80]}")

    # 排序：严重度优先（L1 穿价 > L2 低价单 > L3 远墙），再按异常数量/金额
    results.sort(key=lambda r: (-max((a[0] for a in r[2]), default=0),
                                -len(r[2]), -sum(a[4] for a in r[2])))

    # L3 远墙快照落盘（趋势分析用），不推送
    log_walls(results, WALLS_LOG)

    alerts = [(s, v, a, sm) for s, v, a, sm in results if has_alert(a)]

    if args.quiet:
        if not alerts:
            return  # watchdog 静默
        print(f"🚨 CEX 异常挂单雷达 · {dt.datetime.now():%m-%d %H:%M}\n")
    else:
        print(f"=== CEX 异常挂单雷达 · {dt.datetime.now():%m-%d %H:%M} ===")
        print(f"扫描 {len(symbols)} 币 × {len(exs)} 所 | 阈值: 偏离≥{args.min_dev}% 且 ≥${args.min_notional:,.0f}\n")
        print("（无异常币：", end="")
        clean = [f"{s}({v})" for s, v, a, _ in results if not a]
        print("、".join(clean[:24]) if clean else "无", end="）\n\n")

    for sym, venue, anomalies, sm in (alerts if args.quiet else results):
        if not anomalies:
            continue
        print(f"◆ {sym} @ {venue}  中价 {sm['mid']:.6g} | 买一 {sm['best_bid']:.6g}"
              f" 卖一 {sm['best_ask']:.6g} | 点差 {sm['spread_pct']:.3f}%"
              f" | 深盘 {sm['n_bids']}+{sm['n_asks']} 档")
        shown = anomalies[:10]
        for a in shown:
            print(format_anomaly(a, sm["mid"]))
        if len(anomalies) > 10:
            print(f"  …另有 {len(anomalies) - 10} 条")
        print()

    if errors and not args.quiet:
        print("[!] 拉取失败：", "; ".join(errors[:8]))

    if not args.quiet:
        n_wall = sum(1 for _, _, a, _ in results if any(x[0] == 3 for x in a))
        print(f"[i] L3 远墙快照：{n_wall} 个币 → data/abnormal_walls.jsonl（趋势分析用，不推送）")

    if args.chart and results:
        make_chart(results[:4], args.chart)


def make_chart(results, out_path):
    """深盘剖面图：x=偏离中价%，y=档位金额，异常档标红。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for f in ["PingFang SC", "Heiti SC", "Arial Unicode MS", "Songti SC"]:
        try:
            plt.rcParams["font.sans-serif"] = [f] + plt.rcParams["font.sans-serif"]
            break
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False

    n = len(results)
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    axes = axes.flatten()
    for i, (sym, venue, anomalies, sm) in enumerate(results[:4]):
        ax = axes[i]
        mid = sm["mid"]
        bids, asks = sm.get("_book", (None, None))
        # 用 summary 里没有的原始盘口——重新拉一次最简单（只画 top4，开销小）
        if bids is None:
            bids, asks = [], []
        # 拉盘口画图
        try:
            if venue == "BYBIT":
                b = fetch_bybit_book(sym)
            else:
                b = fetch_binance_book(sym)
            bids, asks = b["bids"], b["asks"]
        except Exception:
            pass
        ax.axvline(0, color="gray", lw=0.8)
        for side, levels, color, label in [("bid", bids, "tab:blue", "买盘"),
                                           ("ask", asks, "tab:orange", "卖盘")]:
            xs = [(p - mid) / mid * 100.0 for p, _ in levels]
            ys = [p * q for p, q in levels]
            ax.scatter(xs, ys, s=6, color=color, alpha=0.5, label=label)
        for a in anomalies:
            px = a[2]
            ax.scatter([(px - mid) / mid * 100.0], [a[4]], s=60,
                       facecolors="none", edgecolors="red", linewidths=1.5,
                       label="异常" if i == 0 else None)
        ax.set_title(f"{sym} @ {venue}  中价 {mid:.6g}", fontsize=11)
        ax.set_xlabel("偏离中价 %")
        ax.set_ylabel("档位金额 USDT")
        ax.grid(alpha=0.3)
        if i == 0:
            ax.legend(fontsize=8)
    for j in range(len(results), 4):
        axes[j].axis("off")
    fig.suptitle(f"CEX 异常挂单深盘剖面 · {dt.datetime.now():%m-%d %H:%M}", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
