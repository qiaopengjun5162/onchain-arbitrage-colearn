#!/usr/bin/env python3
"""OI（未平仓合约）快照记录 + 异动检测。

背景：老孙《金融终端系统 4：套利监控模块设计思路》（2026-08-07 归档）——
"价格没明显变化但 OI 显著放大，是最明显的庄家入场特征；其他都可以造假，OI 变化无法造假。"

第一阶段只做记录 + 告警：不接私钥、不下单、不写任何执行逻辑。

用法：
    uv run --with ccxt python scripts/oi_monitor.py                # 拉一次快照 + 异动检测
    uv run --with ccxt python scripts/oi_monitor.py --backfill    # 只落库（用于冷启动攒基线，不检测）

环境变量：
    PROXY    http://127.0.0.1:7890   # binance 等境外 API 需要代理
    TG_TOKEN / TG_CHAT_ID            # 可选：推送到 Telegram，缺省只打印

数据：data/oi_history.db（SQLite，主键 ts+exchange+symbol 防重复）
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import ccxt

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "oi_history.db"

# 可调参数
# 可用性实测（2026-08-07，走 Clash 代理）：okx/bitget/kucoin ✅；
# binance 451（地区限制）、bybit 403（CloudFront 地区限制）→ 换代理节点后再启用；
# gate 的 fetchOpenInterest 未实现；hyperliquid 需先 load_markets。
EXCHANGES = ["okx", "bitget", "kucoin"]
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "DOGE/USDT:USDT"]
OI_SURGE_RATIO = 1.25     # 当前 OI / 基线均值 > 1.25 触发"放大"告警
PRICE_STABLE = 0.01       # 同期价格变动 < 1% 才算"价格没动"
STEP_SURGE = 1.15         # 相邻两次采样跳增 15% 触发"跳增"告警
BASE_WINDOW_HOURS = 24    # 基线窗口
MIN_BASE_SAMPLES = 6      # 至少 6 个采样才建立基线（约 3 小时 @30min）

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")


def fmt_num(v, suffix=""):
    """None 安全格式化：数值转千分位，None/NaN 显示 '-'。"""
    try:
        if v is None or v != v:  # NaN 自不等
            return "-"
        return f"{v:,.0f}{suffix}"
    except (TypeError, ValueError):
        return "-"


def get_exchange(name: str):
    ex_cls = getattr(ccxt, name)
    ex = ex_cls({"enableRateLimit": True, "timeout": 20000})
    proxy = os.environ.get("PROXY", "")
    if proxy:
        ex.proxies = {"http": proxy, "https": proxy}
    return ex


def fetch_snapshot(ex, symbol: str):
    oi = ex.fetch_open_interest(symbol)
    ticker = ex.fetch_ticker(symbol)
    fr = None
    try:
        fr = ex.fetch_funding_rate(symbol)
    except Exception:
        pass
    return {
        "oi_contracts": oi.get("openInterestAmount"),
        "oi_usd": oi.get("openInterestValue"),
        "price": ticker.get("last"),
        "funding_rate": fr.get("fundingRate") if fr else None,
    }


def init_db(conn: sqlite3.Connection):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS oi_snapshots (
            ts INTEGER NOT NULL,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            oi_contracts REAL,
            oi_usd REAL,
            price REAL,
            funding_rate REAL,
            PRIMARY KEY (ts, exchange, symbol)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_exch_sym ON oi_snapshots(exchange, symbol, ts)"
    )
    conn.commit()


def baseline(conn, exchange: str, symbol: str):
    """返回 (窗口内 OI 均值, 窗口内价格均值, 采样数)。无足够样本返回 None。"""
    cutoff = int(time.time()) - BASE_WINDOW_HOURS * 3600
    row = conn.execute(
        """SELECT AVG(oi_contracts), AVG(price), COUNT(*)
           FROM oi_snapshots WHERE exchange=? AND symbol=? AND ts>=?""",
        (exchange, symbol, cutoff),
    ).fetchone()
    avg_oi, avg_price, n = row
    if n < MIN_BASE_SAMPLES:
        return None
    return avg_oi, avg_price, n


def last_snapshot(conn, exchange: str, symbol: str):
    row = conn.execute(
        """SELECT oi_contracts, price, ts FROM oi_snapshots
           WHERE exchange=? AND symbol=? ORDER BY ts DESC LIMIT 1""",
        (exchange, symbol),
    ).fetchone()
    return row


def detect(conn, exchange: str, symbol: str, snap: dict) -> list[str]:
    alerts = []
    if not snap["oi_contracts"]:
        return alerts
    b = baseline(conn, exchange, symbol)
    if b:
        avg_oi, avg_price, n = b
        ratio = snap["oi_contracts"] / avg_oi if avg_oi else 0
        price_move = abs(snap["price"] - avg_price) / avg_price if avg_price else 1
        if ratio > OI_SURGE_RATIO and price_move < PRICE_STABLE:
            alerts.append(
                f"[OI 放大·价格未动] {exchange} {symbol} OI={fmt_num(snap['oi_contracts'])} "
                f"(基线均值 {fmt_num(avg_oi)}，放大 {ratio:.1%}，价格变动 {price_move:.2%}，"
                f"基线样本 {n}) —— 疑似庄家建仓，人工复核！"
            )
    prev = last_snapshot(conn, exchange, symbol)
    if prev and prev[0]:
        prev_oi, prev_price, prev_ts = prev
        if snap["oi_contracts"] > prev_oi * STEP_SURGE:
            gap_min = (time.time() - prev_ts) / 60
            alerts.append(
                f"[OI 跳增] {exchange} {symbol} OI={fmt_num(snap['oi_contracts'])} "
                f"较上次（{fmt_num(prev_oi)}，{gap_min:.0f} 分钟前）跳增 "
                f"{snap['oi_contracts']/prev_oi - 1:.1%}，价格 {prev_price:.6g} -> {snap['price']:.6g}"
            )
    return alerts


def tg_push(text: str):
    if not (TG_TOKEN and TG_CHAT_ID):
        return
    import requests

    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text},
            timeout=15,
        )
    except Exception as e:
        print(f"[warn] Telegram 推送失败: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="OI 快照记录 + 异动检测")
    ap.add_argument("--backfill", action="store_true", help="只落库不检测（冷启动攒基线）")
    ap.add_argument("--quiet", action="store_true",
                    help="无异动时静默（供 cron watchdog 用：有告警才有输出）")
    args = ap.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    ts = int(time.time())
    all_alerts = []
    for name in EXCHANGES:
        try:
            ex = get_exchange(name)
        except Exception as e:
            print(f"[skip] {name} 初始化失败: {e}")
            continue
        for symbol in SYMBOLS:
            try:
                snap = fetch_snapshot(ex, symbol)
            except Exception as e:
                print(f"[skip] {name} {symbol} 拉取失败: {e}")
                continue
            conn.execute(
                """INSERT OR REPLACE INTO oi_snapshots
                   (ts, exchange, symbol, oi_contracts, oi_usd, price, funding_rate)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    ts,
                    name,
                    symbol,
                    snap["oi_contracts"],
                    snap["oi_usd"],
                    snap["price"],
                    snap["funding_rate"],
                ),
            )
            if not args.quiet:
                print(
                    f"[ok] {name} {symbol} OI={fmt_num(snap['oi_contracts'])} "
                    f"({fmt_num(snap['oi_usd'])} USDT) price={fmt_num(snap['price'])} "
                    f"funding={snap['funding_rate'] or '-'}"
                )
            if not args.backfill:
                all_alerts += detect(conn, name, symbol, snap)
    conn.commit()

    if all_alerts:
        print("\n" + "=" * 60)
        print("⚠️ 异动告警：")
        for a in all_alerts:
            print(a)
            tg_push(a)
    elif not args.quiet:
        print("\n无异动。基线建立中（需要至少 %d 个采样，约 %d 小时 @30min 采样）。"
              % (MIN_BASE_SAMPLES, MIN_BASE_SAMPLES // 2))

    conn.close()


if __name__ == "__main__":
    main()
