#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快讯层哨兵 v1（news_sentinel.py）— 2026-08-13
================================================
信息差速度分层：公告层（listing_monitor，一手）✅ → 快讯层（本脚本，二手更快）→ 推特层（最慢）。
数据源：The Block RSS（机构数据/市场结构，2026-08-13 探测唯一可用 RSS）。
行为：watchdog 模式——仅「新条目 + 关键词命中」才输出；重复/无关静默。

用法：
  python3 scripts/news_sentinel.py --watchdog    # cron 模式（静默，有命中才报）
  python3 scripts/news_sentinel.py               # 手动看最近快讯
"""

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SEEN_PATH = BASE_DIR / "data" / "news_sentinel_seen.json"
RSS_URL = "https://www.theblock.co/rss.xml"
PROXY = "http://127.0.0.1:7890"

# 与研究线相关的关键词（中英双语；命中=潜在事件窗口）
KEYWORDS = [
    "listing", "delisting", "launch", "new contract", "spot", "perp", "futures",
    "hack", "exploit", "liquidation", "depeg", "stablecoin", "listing on",
    "上线", "上币", "下架", "新合约", "事故", "清算", "脱锚", "上市", "永续",
    "bStock", "RWA", "Polymarket", "prediction market", "OFT", "LayerZero",
]

def fetch_rss():
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with opener.open(req, timeout=30) as r:
        return r.read().decode(errors="replace")

def parse_items(xml_text):
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter("item"):
        def g(tag):
            e = it.find(tag)
            return e.text.strip() if e is not None and e.text else ""
        items.append({"title": g("title"), "link": g("link"),
                      "guid": g("guid") or g("link"),
                      "pubDate": g("pubDate"), "desc": g("description")[:300]})
    return items

def load_seen():
    try:
        return set(json.loads(SEEN_PATH.read_text()))
    except Exception:
        return set()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watchdog", action="store_true")
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args()

    try:
        items = parse_items(fetch_rss())
    except Exception as e:
        if args.watchdog:
            print(f"快讯层抓取失败: {str(e)[:100]}")  # watchdog 也报（故障可见）
        return 1

    seen = load_seen()
    hits, new = [], 0
    for it in items:
        is_new = it["guid"] not in seen
        if is_new:
            new += 1
        text = (it["title"] + " " + it["desc"]).lower()
        matched = [k for k in KEYWORDS if k.lower() in text]
        if matched and (is_new or not args.watchdog):
            hits.append((it, matched))
    # 记录本次所有 guid（去重）
    for it in items[:50]:
        seen.add(it["guid"])
    try:
        SEEN_PATH.write_text(json.dumps(list(seen)[-500:]))
    except Exception:
        pass

    if args.watchdog:
        if hits:
            print(f"=== 快讯层命中 @ {datetime.now(timezone.utc).strftime('%m-%d %H:%M')} ===")
            for it, matched in hits[:5]:
                print(f"• {it['title'][:90]}  [{','.join(matched[:3])}] {it['link']}")
        return 0

    print(f"=== The Block RSS 最近 {args.limit} 条（新 {new} 条，命中 {len(hits)}）===")
    for it, matched in hits[:args.limit]:
        print(f"⚡ {it['title'][:90]}  [{','.join(matched[:3])}]")
        print(f"   {it['link']}")
    if not hits:
        print("（无关键词命中）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
