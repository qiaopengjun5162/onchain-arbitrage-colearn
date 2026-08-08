#!/usr/bin/env python3
"""停运协议（"捡尸体"）监控：DefiLlama TVL 骤降 + 僵尸化检测。

背景：Paxon 群内想法（2026-08-07）——老项目暂停运营后残留的清算/赎回机会。
方法论：DefiLlama 按 TVL 筛借贷类协议；"TVL 骤降" = 死亡信号；
首跑建立本地基线（SQLite），之后每次对比上次快照。

用法：
    uv run --with requests python scripts/dead_protocol_screener.py            # 采样 + 检测
    uv run --with requests python scripts/dead_protocol_screener.py --backfill # 只落库（首跑）

环境变量：
    PROXY    http://127.0.0.1:7890   # DefiLlama 需代理
    TG_TOKEN / TG_CHAT_ID            # 可选：Telegram 推送

数据：data/protocol_snapshots.db
"""

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "protocol_snapshots.db"
API = "https://api.llama.fi/protocols"

# 告警阈值
DROP_RATIO = 0.5        # 相对上次快照 TVL 下降 >50% 告警
ZOMBIE_FROM = 1_000_000  # 上次 >100万
ZOMBIE_TO = 100_000      # 本次 <10万 → "僵尸化"告警
# 关注分类：清算/借贷相关
WATCH_CATEGORIES = {
    "Lending", "CDP", "Liquidations", "NFT Lending",
    "Uncollateralized Lending", "RWA Lending",
}

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")


def get_proxy():
    p = os.environ.get("PROXY", "")
    return {"http": p, "https": p} if p else None


def fetch_protocols():
    r = requests.get(API, proxies=get_proxy(), timeout=60)
    r.raise_for_status()
    return r.json()


def tvl_of(p):
    v = p.get("tvl")
    return v if isinstance(v, (int, float)) else 0.0


def watch_protocols(prots):
    return [p for p in prots if p.get("category") in WATCH_CATEGORIES]


def init_db(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS protocol_snapshots (
            ts INTEGER NOT NULL,
            slug TEXT NOT NULL,
            name TEXT,
            category TEXT,
            tvl REAL,
            chains TEXT,
            PRIMARY KEY (ts, slug)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_slug ON protocol_snapshots(slug, ts)")
    conn.commit()


def last_tvl(conn, slug):
    row = conn.execute(
        "SELECT tvl, ts FROM protocol_snapshots WHERE slug=? ORDER BY ts DESC LIMIT 1",
        (slug,),
    ).fetchone()
    return row


def detect(conn, p):
    slug, name, tvl = p["slug"], p["name"], tvl_of(p)
    prev = last_tvl(conn, slug)
    alerts = []
    if prev:
        prev_tvl, prev_ts = prev
        if prev_tvl > 0 and tvl < prev_tvl * (1 - DROP_RATIO):
            days = (time.time() - prev_ts) / 86400
            alerts.append(
                f"[TVL 骤降 {1 - tvl / prev_tvl:.0%}] {name} (借贷类/{p.get('category')}) "
                f"TVL ${prev_tvl:,.0f} -> ${tvl:,.0f}（{days:.0f} 天内）—— 疑似停运/死亡信号，人工复核残留清算！"
            )
        if prev_tvl > ZOMBIE_FROM and tvl < ZOMBIE_TO:
            alerts.append(
                f"[僵尸化] {name} TVL 从 ${prev_tvl:,.0f} 跌至 ${tvl:,.0f} —— 进入\"捡尸体\"候选清单"
            )
    return alerts


def tg_push(text):
    if not (TG_TOKEN and TG_CHAT_ID):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text},
            timeout=15,
        )
    except Exception as e:
        print(f"[warn] Telegram 推送失败: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="停运协议监控（DefiLlama TVL 骤降检测）")
    ap.add_argument("--backfill", action="store_true", help="只落库不检测（首跑建基线）")
    ap.add_argument("--quiet", action="store_true",
                    help="无异动时静默（供 cron watchdog）")
    ap.add_argument("--top", type=int, default=8,
                    help="非 quiet 模式打印的僵尸候选数量")
    args = ap.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    try:
        prots = fetch_protocols()
    except Exception as e:
        print(f"[error] DefiLlama 拉取失败: {e}", file=sys.stderr)
        return 1

    watch = watch_protocols(prots)
    if not args.quiet:
        print(f"[info] 拉取 {len(prots)} 个协议，关注分类 {len(watch)} 个 "
              f"({','.join(sorted(WATCH_CATEGORIES))})")

    ts = int(time.time())
    all_alerts = []
    for p in watch:
        conn.execute(
            "INSERT OR REPLACE INTO protocol_snapshots (ts, slug, name, category, tvl, chains) VALUES (?,?,?,?,?,?)",
            (ts, p["slug"], p.get("name"), p.get("category"), tvl_of(p),
             ",".join(p.get("chains", [])[:4])),
        )
        if not args.backfill:
            all_alerts += detect(conn, p)
    conn.commit()

    if all_alerts:
        print("\n" + "=" * 60)
        print("⚠️ 死亡/僵尸信号：")
        for a in all_alerts:
            print(a)
            tg_push(a)
        print("=" * 60)
    elif not args.quiet:
        # 僵尸候选总览（按 TVL 升序，最小的是最接近尸体的）
        cur = conn.execute(
            "SELECT name, category, tvl, ts FROM protocol_snapshots WHERE ts=? "
            "ORDER BY tvl ASC LIMIT ?", (ts, args.top)).fetchall()
        print(f"\n[info] 关注类中 TVL 最低的 {len(cur)} 个（越接近 0 越像尸体）：")
        for name, cat, tvl, _ in cur:
            print(f"  {name[:32]:<34} {cat:<22} ${tvl:>13,.0f}")
        n_samples = conn.execute("SELECT COUNT(DISTINCT ts) FROM protocol_snapshots").fetchone()[0]
        print(f"\n基线轮次: {n_samples}（对比检测需 ≥2 轮，建议每天跑一次）")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
