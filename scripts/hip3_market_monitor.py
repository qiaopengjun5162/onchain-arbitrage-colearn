#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HIP-3 市场监控（hip3_market_monitor.py）— 2026-08-23 D19
========================================================
币股线 P0 新战场：Hyperliquid HIP-3 builder-deployed perps 市场列表 + 快照。

背景（D19 对比表 / hip3-preipo-perps-entropy-20260821 笔记）：
- HIP-3 = Hyperliquid permissionless perp 部署框架（2025-10 起），累计成交量 $120B
- vntl 部署了 SPACEX/OPENAI/ANTHROPIC pre-IPO perps；xyz/flx/cash/mkts/km 部署股票/商品/指数
- 价值：链上 pre-IPO 定价距开盘 <3%（Cerebras 案例）→ 与 CEX tokenized 股（bStock）可能
  存在市场隔离价差；HIP-3 是币股闭市漂移线的第 3 个数据源（tvscreener 美股 + 链上池 + HIP-3）

数据源：api.hyperliquid.xyz/info（公开无 key）
  - perpDexs: HIP-3 DEX 列表
  - metaAndAssetCtxs + dex: 每 DEX 的市场元数据 + 上下文（mark/oracle/funding/OI）
产出：
  - data/hip3_markets.csv — 全市场最新快照（cron 每次覆盖写，用于查询）
  - data/hip3_markets_history.jsonl — 追加历史（供趋势分析）

用法：
  python scripts/hip3_market_monitor.py                # 全量快照 + 落盘 + 表格
  python scripts/hip3_market_monitor.py --quiet        # watchdog：仅输出 stock-like 且 funding 极端
  python scripts/hip3_market_monitor.py --top 20       # 只看 stock-like TOP 市值/成交

依赖：hermes venv python3.11（urllib 即可，无需 ccxt）
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "hip3_markets.csv"
HIST_PATH = DATA_DIR / "hip3_markets_history.jsonl"

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
HL_URL = "https://api.hyperliquid.xyz/info"

# stock-like 关键词（HIP-3 里非 crypto 的市场）
STOCK_KEYWORDS = [
    "TSLA", "NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOG", "GOOGL", "COIN", "HOOD",
    "INTC", "ORCL", "PLTR", "CRCL", "SNDK", "ANTH", "OAI", "SPACEX", "OPENAI",
    "ANTHROPIC", "BABA", "AVGO", "LRCX", "NET", "IREN", "MAG7", "SEMIS", "ROBOT",
    "INFOTECH", "NUCLEAR", "DEFENSE", "ENERGY", "BIOTECH", "GOLD", "SILVER", "OIL",
    "GAS", "COPPER", "PALLADIUM", "XAU", "XAG", "US500", "USA500", "USTECH",
    "USENERGY", "USOIL", "USBOND", "SMALL2000", "TOTAL2", "OTHERS", "H100", "BTCD",
    "EUR", "EWY", "NFLX", "AMD", "MSTR", "UBER", "DIS", "PEP", "KO", "WMT", "NATGAS",
    "BRENTOIL", "WHEAT", "SOYBEAN", "CORN", "LIGHTER",
]
# 明确排除的 meme/crypto 名字（防误伤）
EXCLUDE_KEYWORDS = ["PEPE", "FARTCOIN", "PUMP", "MOODENG", "GOAT", "PENGU", "TURBO", "BRETT"]


def hl_info(payload):
    req = urllib.request.Request(
        HL_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    return json.loads(opener.open(req, timeout=30).read())


def fetch_all():
    """返回 [{dex, name, mark, oracle, funding, oi, is_stock}]"""
    dexs = [d for d in hl_info({"type": "perpDexs"}) if isinstance(d, dict)]
    rows = []
    for d in dexs:
        dex = d.get("name", "")
        try:
            meta, ctxs = hl_info({"type": "metaAndAssetCtxs", "dex": dex})
        except Exception:
            continue
        universe = meta.get("universe", [])
        for i, u in enumerate(universe):
            name = u.get("name", "")
            ctx = ctxs[i] if i < len(ctxs) else {}
            rows.append({
                "dex": dex,
                "name": name,
                "mark": float(ctx.get("markPx", 0) or 0),
                "oracle": float(ctx.get("oraclePx", 0) or 0),
                "funding": float(ctx.get("funding", 0) or 0),
                "oi": float(ctx.get("openInterest", 0) or 0),
                "is_stock": (any(k in name.split(":")[-1].upper() for k in STOCK_KEYWORDS)
                             and not any(k in name.split(":")[-1].upper() for k in EXCLUDE_KEYWORDS)),
            })
    return rows


def save(rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # CSV 覆盖写（查询用）
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dex", "name", "mark", "oracle", "funding", "oi", "is_stock"])
        w.writeheader()
        w.writerows(rows)
    # JSONL 追加（历史）
    ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(HIST_PATH, "a") as f:
        f.write(json.dumps({"ts": ts, "rows": rows}, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description="HIP-3 市场监控（HL builder perps）")
    ap.add_argument("--quiet", action="store_true", help="watchdog：仅 stock-like 且 |funding|≥1%/8h 才输出")
    ap.add_argument("--top", type=int, default=0, help="只看 stock-like 前 N（按 OI 排序）")
    args = ap.parse_args()

    rows = fetch_all()
    save(rows)

    stock = [r for r in rows if r["is_stock"]]
    stock.sort(key=lambda r: r["oi"], reverse=True)

    if args.quiet:
        # watchdog：stock-like 且 funding 极端（≥1%/8h 或 ≤-1%/8h）
        hot = [r for r in stock if abs(r["funding"]) >= 0.01]
        if hot:
            print(f"🔴 HIP-3 极端费率: {len(hot)} 个 stock-like 市场")
            for r in hot[:10]:
                print(f"  {r['name']:<18} funding {r['funding']*100:+.2f}%/8h  mark {r['mark']:,.2f}  OI ${r['oi']:,.0f}")
        return

    print(f"=== HIP-3 市场快照 {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC ===")
    print(f"总市场: {len(rows)} | stock-like: {len(stock)}")
    print(f"落盘: {CSV_PATH} (+history jsonl)")

    if args.top:
        print(f"\n--- stock-like TOP {args.top}（按 OI）---")
        for r in stock[:args.top]:
            ann = r["funding"] * 3 * 365 * 100  # 8h 费率 → 年化 %
            print(f"  {r['name']:<18} mark {r['mark']:>12,.2f}  funding {r['funding']*100:+6.2f}%/8h"
                  f" (年化 {ann:+7.1f}%)  OI ${r['oi']:>12,.0f}")
    else:
        # 默认：打印所有 stock-like（紧凑）
        for r in stock:
            print(f"  {r['name']:<18} mark {r['mark']:>12,.2f}  funding {r['funding']*100:+6.2f}%/8h  OI ${r['oi']:>12,.0f}")


if __name__ == "__main__":
    main()
