#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史资金费率 + 基差可视化工具（直观判断当前处于什么位置）

用法：
  python funding_basis_viz.py --symbols BTC,ETH,SOL --days 30 --out /tmp/funding_viz.png
  python funding_basis_viz.py --symbols BTC --days 90          # 长窗口看体制

数据源：
  - 资金费率历史：Bybit 公开 API（无需 key，最多 ~500 条，8h 结算 ≈ 160 天）
  - 基差历史：由永续/现货 OHLCV 收盘价计算（basis = perp/spot - 1）

输出：
  - 图（上=费率历史+当前标注+分位带；下=基差历史）
  - 文字摘要：当前费率/均值/分位/历史区间 + 基差当前值/分位
"""
import argparse
import datetime as dt
import os
import sys
import urllib.request
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")

# matplotlib 中文字体
for f in ["PingFang SC", "Heiti SC", "Arial Unicode MS", "Songti SC"]:
    try:
        plt.rcParams["font.sans-serif"] = [f] + plt.rcParams["font.sans-serif"]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False


def http_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    return json.loads(opener.open(req, timeout=timeout).read())


def fetch_okx_funding(symbol: str, limit: int = 500):
    """OKX 永续历史资金费率。返回 [(ts, rate_8h)] 升序。"""
    inst = f"{symbol}-USDT-SWAP"
    out = []
    before = None
    while len(out) < limit:
        url = "https://www.okx.com/api/v5/public/funding-rate-history?instId=" + inst + "&limit=100"
        if before:
            url += f"&before={before}"
        try:
            d = http_json(url)
        except Exception:
            break
        if d.get("code") != "0":
            break
        rows = d.get("data", [])
        if not rows:
            break
        for r in rows:
            out.append((int(r["fundingTime"]) / 1000, float(r["realizedRate"])))
        before = rows[-1]["fundingTime"]
        if len(rows) < 100:
            break
    out.sort()
    return out[-limit:]


def fetch_okx_klines(symbol: str, interval: str = "1H", limit: int = 720):
    """OKX K线（SWAP 永续 / SPOT 现货）。返回 [(ts, close)] 升序。"""
    def one(inst):
        url = (f"https://www.okx.com/api/v5/market/candles?instId={inst}"
               f"&bar={interval}&limit={limit}")
        d = http_json(url)
        if d.get("code") != "0":
            return []
        # OKX 返回倒序 [ts, o, h, l, c, ...]
        rows = d.get("data", [])
        return [(int(r[0]) / 1000, float(r[4])) for r in rows]
    return one(f"{symbol}-USDT-SWAP"), one(f"{symbol}-USDT")


def percentile(v, series):
    """v 在 series 里的分位（0-100）。"""
    if not series:
        return None
    below = sum(1 for x in series if x < v)
    return below / len(series) * 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="BTC", help="逗号分隔，如 BTC,ETH,SOL")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default="/tmp/funding_basis_viz.png")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    fig, axes = plt.subplots(2, len(symbols), figsize=(6 * len(symbols), 9),
                             squeeze=False)

    summary_lines = []
    for col, sym in enumerate(symbols):
        ax_f, ax_b = axes[0][col], axes[1][col]

        # ---- 费率历史 ----
        rates = fetch_okx_funding(sym, limit=max(90, args.days * 3))
        if not rates:
            summary_lines.append(f"{sym}: 费率历史拉取失败")
            ax_f.set_title(f"{sym}（无数据）")
            continue
        ts_f = [dt.datetime.fromtimestamp(t, tz=dt.timezone.utc) for t, _ in rates]
        r_f = [r * 100 for _, r in rates]  # % 每 8h
        cur_f = r_f[-1]
        ax_f.plot(ts_f, r_f, lw=1.2, color="#d62728")
        ax_f.axhline(0, color="gray", lw=0.6)
        ax_f.axhline(0.05, color="green", lw=0.8, ls="--", label="进场线 0.05%/8h")
        ax_f.axhline(0.10, color="orange", lw=0.8, ls=":", label="过热线 0.10%/8h")
        # 当前点标注
        ax_f.scatter([ts_f[-1]], [cur_f], color="#d62728", zorder=5, s=40)
        ax_f.annotate(f"{cur_f:+.4f}%", (ts_f[-1], cur_f), textcoords="offset points",
                      xytext=(8, 8), fontsize=10, color="#d62728")
        ax_f.set_title(f"{sym} 资金费率历史（8h结算）", fontsize=12)
        ax_f.legend(fontsize=8, loc="upper left")
        ax_f.grid(alpha=0.3)
        ax_f.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax_f.tick_params(labelsize=9)

        # ---- 基差历史 ----
        perp, spot = fetch_okx_klines(sym)
        if perp and spot:
            common_ts = {p[0] for p in perp} & {s[0] for s in spot}
            pp = {t: c for t, c in perp if t in common_ts}
            sp = {t: c for t, c in spot if t in common_ts}
            ts_b = sorted(common_ts)
            if len(ts_b) > 1:
                basis = [(pp[t] / sp[t] - 1) * 100 for t in ts_b]
                cur_b = basis[-1]
                tsb = [dt.datetime.fromtimestamp(t, tz=dt.timezone.utc) for t in ts_b]
                ax_b.plot(tsb, basis, lw=1.2, color="#1f77b4")
                ax_b.axhline(0, color="gray", lw=0.6)
                ax_b.scatter([tsb[-1]], [cur_b], color="#1f77b4", zorder=5, s=40)
                ax_b.annotate(f"{cur_b:+.3f}%", (tsb[-1], cur_b),
                              textcoords="offset points", xytext=(8, 8),
                              fontsize=10, color="#1f77b4")
                pct_b = percentile(cur_b, basis)
                summary_lines.append(
                    f"{sym} 基差: 当前 {cur_b:+.3f}% | 区间 [{min(basis):+.3f}, {max(basis):+.3f}]% | 分位 {pct_b:.0f}%")
            else:
                summary_lines.append(f"{sym}: 基差数据不足")
        else:
            summary_lines.append(f"{sym}: 基差拉取失败")
        ax_b.set_title(f"{sym} 基差历史（永续/现货-1）", fontsize=12)
        ax_b.grid(alpha=0.3)
        ax_b.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax_b.tick_params(labelsize=9)

        # ---- 费率摘要 ----
        pct_f = percentile(cur_f, r_f)
        ann = cur_f * 3 * 365
        summary_lines.append(
            f"{sym} 费率: 当前 {cur_f:+.4f}%/8h ≈ 年化 {ann:+.0f}% | "
            f"区间 [{min(r_f):+.4f}, {max(r_f):+.4f}]%/8h | 分位 {pct_f:.0f}% | "
            f"观测 {len(r_f)} 期")

    fig.suptitle(f"历史费率×基差面板（OKX，截至 {dt.datetime.now(tz=dt.timezone.utc):%Y-%m-%d %H:%M} UTC）",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fig.savefig(args.out, dpi=130)
    plt.close(fig)

    print("=== 费率/基差历史摘要 ===")
    for l in summary_lines:
        print(" " + l)
    print(f"\n图已保存: {args.out}")
    if any("当前" in l and "分位 90%" in l for l in summary_lines):
        print("⚠️ 存在 90%+ 高分位信号，人工复核后再决策")


if __name__ == "__main__":
    main()
