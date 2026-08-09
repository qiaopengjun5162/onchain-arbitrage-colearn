#!/usr/bin/env python3
"""DeFi Sphere 清算监控（接"捡尸体/清算套利"方向）。

数据源：sphere.data.blockanalitica.com（app.defi-sphere.com 背后的公开 API，2026-08-07 实测可用，走 Clash 代理）
逻辑：拉最新清算 → 按 liquidation_order_index 去重落库 → 超阈值告警（watchdog：非空即推送）。

告警阈值（可调）：
- MIN_COLLATERAL_USD：单笔抵押品 >= 5 万美元
- MIN_BONUS_USD：单笔清算奖励 >= 5000 美元（奖励 ≈ 套利者毛利）

用法：
    python scripts/liquidation_monitor.py            # 拉取+检测
    python scripts/liquidation_monitor.py --backfill # 只落库
环境变量：PROXY（默认 http://127.0.0.1:7890）
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "liquidations.db"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")

API = "https://sphere.data.blockanalitica.com/liquidations"
NETWORKS = ["ethereum", "arbitrum", "base", "optimism", "polygon"]  # 实测 options 支持多网络
LOOKBACK_HOURS = 24  # 拉最近 24h 的清算（够覆盖 cron 间隔）

MIN_COLLATERAL_USD = 50_000   # 抵押品 >= $50K
MIN_BONUS_USD = 5_000         # 清算奖励 >= $5K

# morpho 优先（D4 分析 + 2026-08-09 DB 实测：morpho 76%，base 77%）
# morpho 平均奖励仅 $363（max $10K），aave_v3 奖励 ~$0 → morpho 用更低阈值才能抓得到
MORPHO_MIN_BONUS_USD = 1_000       # morpho 奖励 >= $1K 即报
MORPHO_MIN_COLLATERAL_USD = 10_000 # morpho 抵押品 >= $10K
PRIORITY_NETWORKS = ["base"]        # base 优先（morpho 主战场）


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def fetch_liquidations(session, network: str, hours: int) -> list:
    fd = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    td = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    params = {
        "sort": "-datetime", "page": 1, "limit": 100,
        "networks": network, "from_date": fd, "to_date": td,
    }
    url = f"{API}/?{urlencode(params)}"
    r = session.get(url, timeout=20)
    r.raise_for_status()
    d = r.json()
    data = d.get("data") or {}
    return data.get("results") or []


def init_db(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS liquidations (
        order_id TEXT PRIMARY KEY,
        network TEXT,
        protocol TEXT,
        wallet TEXT,
        tx_hash TEXT,
        datetime TEXT,
        loan_token TEXT,
        debt_repaid_usd REAL,
        collateral_seized_usd REAL,
        bonus_usd REAL,
        seen_at TEXT
    )""")


def main():
    ap = argparse.ArgumentParser(description="DeFi Sphere 清算监控")
    ap.add_argument("--backfill", action="store_true", help="只落库不检测")
    ap.add_argument("--quiet", action="store_true", help="无异动静默（cron watchdog）")
    args = ap.parse_args()

    session = requests.Session()
    session.proxies.update({"http": PROXY, "https": PROXY})
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    new_alerts = []
    errors = []
    for net in NETWORKS:
        try:
            items = fetch_liquidations(session, net, LOOKBACK_HOURS)
            for it in items:
                oid = it.get("liquidation_order_index") or it.get("tx_hash")
                if not oid:
                    continue
                cur = conn.execute("SELECT 1 FROM liquidations WHERE order_id=?", (oid,)).fetchone()
                if cur:
                    continue
                bonus = float(it.get("liquidation_bonus_usd") or 0)
                collat = float(it.get("collateral_seized_usd") or 0)
                debt = float(it.get("debt_repaid_usd") or 0)
                conn.execute(
                    "INSERT OR REPLACE INTO liquidations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (oid, it.get("network"), (it.get("protocol") or {}).get("name", "") if isinstance(it.get("protocol"), dict) else str(it.get("protocol", "")),
                     it.get("wallet_address"), it.get("tx_hash"), it.get("datetime"),
                     it.get("loan_token_symbol"), debt, collat, bonus, now_iso()),
                )
                if collat >= MIN_COLLATERAL_USD or bonus >= MIN_BONUS_USD:
                    new_alerts.append({
                        "net": net, "protocol": it.get("protocol"), "wallet": it.get("wallet_address"),
                        "tx": it.get("tx_hash"), "dt": it.get("datetime"),
                        "debt": debt, "collat": collat, "bonus": bonus,
                        "loan": it.get("loan_token_symbol"),
                    })
                else:
                    # morpho 优先：低阈值单独判断（morpho 奖励天然小，通用阈值抓不到）
                    proto = (it.get("protocol") or {}).get("name", "") if isinstance(it.get("protocol"), dict) else str(it.get("protocol", ""))
                    if "morpho" in proto.lower() and (collat >= MORPHO_MIN_COLLATERAL_USD or bonus >= MORPHO_MIN_BONUS_USD):
                        new_alerts.append({
                            "net": net, "protocol": it.get("protocol"), "wallet": it.get("wallet_address"),
                            "tx": it.get("tx_hash"), "dt": it.get("datetime"),
                            "debt": debt, "collat": collat, "bonus": bonus,
                            "loan": it.get("loan_token_symbol"),
                        })
        except Exception as e:
            errors.append(f"{net}: {e}")

    conn.commit()
    conn.close()

    for e in errors:
        print(f"[err] {e}", file=sys.stderr)

    if new_alerts:
        print(f"⚡ 清算告警（{now_iso()}，共 {len(new_alerts)} 笔超阈值）：")
        # 排序：优先网络在前（base 优先），同网络按抵押品降序
        new_alerts.sort(key=lambda a: (a["net"] not in PRIORITY_NETWORKS, -a["collat"]))
        for a in new_alerts:
            tag = "⭐" if a["net"] in PRIORITY_NETWORKS else ""
            print(f"{tag} 🔴 [{a['net']}] {a['protocol']} | 抵押品 ${a['collat']:,.0f} | "
                  f"债务 ${a['debt']:,.0f} ({a['loan']}) | 奖励 ${a['bonus']:,.0f}")
            print(f"   {a['dt']} | 钱包 {a['wallet'][:10]}...{a['wallet'][-6:]}")
            print(f"   tx: https://etherscan.io/tx/{a['tx']}")
    elif not args.quiet:
        print(f"近 24h 无超阈值清算（{now_iso()}）")


if __name__ == "__main__":
    main()
