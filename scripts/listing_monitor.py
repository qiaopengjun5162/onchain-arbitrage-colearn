#!/usr/bin/env python3
"""大所上币公告监控（信息差机会源）。

源（2026-08-07 实测可用，需 Clash 代理）：
- Binance catalogId=48 新币上市目录（bapi.composite 域，不走行情端点，无 451）
- Bybit /v5/announcements/index（type.key 过滤新币/新交易对公告）

逻辑：新公告（按 exchange+code 去重）→ 输出（cron watchdog：非空即推送）；无新公告 → 静默。
告警级别：现货上市 = 最高（价格发现窗口），合约/活动 = 参考。

用法：
    uv run --with requests python scripts/listing_monitor.py            # 拉取+检测
    uv run --with requests python scripts/listing_monitor.py --backfill # 只落库不检测
环境变量：PROXY（默认 http://127.0.0.1:7890）
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "announcements.db"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")

BINANCE_CATALOGS = {
    48: "新币上市(Spot/Futures)",
    50: "新币挖矿(Launchpool)",
    51: "活动",
    52: "交易市场更新",
    53: "系统维护",
    61: "产品更新",
}
BYBIT_KEYWORDS = ["listing", "list ", "launch", "上新", "上架", "现货", "futures will list", "delist", "下架", "will remove"]

BINANCE_LISTING_KW = ["will list", "will launch", "new listing", "launchpool", "futures will launch"]
BINANCE_DELIST_KW = ["will delist", "delisting", "will remove", "下架", "settlement", "settle"]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def fetch_binance(session) -> list:
    """Binance 新币上市目录（catalogId=48）"""
    out = []
    params = {"type": 1, "pageNo": 1, "pageSize": 20, "catalogId": 48}
    url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?" + urlencode(params)
    r = session.get(url, timeout=20)
    r.raise_for_status()
    d = r.json()
    catalogs = (d.get("data") or {}).get("catalogs") or []
    for cat in catalogs:
        for a in cat.get("articles") or []:
            title = a.get("title", "")
            ts = a.get("releaseDate") or 0
            out.append({
                "exchange": "binance",
                "code": str(a.get("code", a.get("id", ""))),
                "title": title,
                "ts": int(ts) / 1000 if ts else 0,
                "url": f"https://www.binance.com/en/support/announcement/{a.get('code')}",
                "catalog": BINANCE_CATALOGS.get(48, ""),
            })
    return out


def fetch_binance_delist(session) -> list:
    """Binance 交易市场更新目录（catalogId=52）→ 过滤下架/结算公告（套利信号源）。

    下架合约价差套利（notes/binance-delisting-arb-verified-20260809.md）：
    公告日 → reduce-only → 强制平仓 → 合约/现货价差放大（实测 HFT 4.4%）。
    本函数就是那个「公告即信号」的入口。
    """
    out = []
    params = {"type": 1, "pageNo": 1, "pageSize": 20, "catalogId": 52}
    url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?" + urlencode(params)
    try:
        r = session.get(url, timeout=20)
        r.raise_for_status()
        d = r.json()
    except Exception:
        return out
    catalogs = (d.get("data") or {}).get("catalogs") or []
    for cat in catalogs:
        for a in cat.get("articles") or []:
            title = a.get("title", "")
            tl = title.lower()
            if not any(k in tl for k in BINANCE_DELIST_KW):
                continue
            ts = a.get("releaseDate") or 0
            out.append({
                "exchange": "binance",
                "code": f"delist-{a.get('code', a.get('id', ''))}",
                "title": title,
                "ts": int(ts) / 1000 if ts else 0,
                "url": f"https://www.binance.com/en/support/announcement/{a.get('code')}",
                "catalog": "下架/结算公告(套利信号)",
            })
    return out


def fetch_bybit(session) -> list:
    """Bybit 公告（过滤新币/新交易对）"""
    out = []
    url = "https://api.bybit.com/v5/announcements/index?locale=en-US&limit=50"
    r = session.get(url, timeout=20)
    r.raise_for_status()
    d = r.json()
    if d.get("retCode") != 0:
        return out
    for it in d.get("result", {}).get("list", []):
        tkey = (it.get("type") or {}).get("key", "")
        title = it.get("title", "")
        # 只留新币/交易对相关类型
        if tkey not in ("new_crypto_listing", "new_trading_pair"):
            tl = title.lower()
            if not any(k in tl for k in ("list", "launch")):
                continue
        out.append({
            "exchange": "bybit",
            "code": it.get("url", "").split("/")[-1][:60],
            "title": title,
            "ts": (it.get("publishTime") or 0) / 1000,
            "url": it.get("url", ""),
            "catalog": (it.get("type") or {}).get("title", ""),
        })
    return out


def init_db(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS announcements (
        exchange TEXT NOT NULL,
        code TEXT NOT NULL,
        title TEXT,
        ts REAL,
        url TEXT,
        catalog TEXT,
        seen_at TEXT,
        PRIMARY KEY (exchange, code)
    )""")


def main():
    ap = argparse.ArgumentParser(description="大所上币公告监控")
    ap.add_argument("--backfill", action="store_true", help="只落库不检测")
    ap.add_argument("--quiet", action="store_true", help="无异动静默（cron watchdog）")
    args = ap.parse_args()

    proxies = {"http": PROXY, "https": PROXY}
    session = requests.Session()
    session.proxies.update(proxies)
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    new_items = []
    fetch_errs = []
    for name, fn in (("binance", fetch_binance), ("binance-delist", fetch_binance_delist), ("bybit", fetch_bybit)):
        try:
            items = fn(session)
            for it in items:
                cur = conn.execute(
                    "SELECT 1 FROM announcements WHERE exchange=? AND code=?",
                    (it["exchange"], it["code"]),
                ).fetchone()
                if cur:
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO announcements (exchange, code, title, ts, url, catalog, seen_at) VALUES (?,?,?,?,?,?,?)",
                    (it["exchange"], it["code"], it["title"], it["ts"], it["url"], it["catalog"], now_iso()),
                )
                new_items.append(it)
        except Exception as e:
            fetch_errs.append(f"{name}: {e}")

    conn.commit()
    conn.close()

    # 输出
    for e in fetch_errs:
        print(f"[err] {e}", file=sys.stderr)
    if new_items:
        print(f"📢 检测到 {len(new_items)} 条新公告（{now_iso()}）：")
        for it in sorted(new_items, key=lambda x: -x["ts"]):
            kind = "🔴" if ("list" in it["title"].lower() or "上新" in it["title"] or "现货" in it["title"]) else "🟡"
            print(f"{kind} [{it['exchange']}/{it['catalog']}] {it['title']}")
            print(f"    {it['url']}")
    elif not args.quiet:
        print(f"无新公告（{now_iso()}）")


if __name__ == "__main__":
    main()
