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

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "oi_history.db"

# 可调参数
# 可用性实测（2026-08-07，走 Clash 代理）：okx/bitget/kucoin ✅；
# binance 451（地区限制）、bybit 403（CloudFront 地区限制）→ 换代理节点后再启用；
# gate 的 fetchOpenInterest 未实现；hyperliquid 需先 load_markets。
# 2026-08-15 重构：ccxt fetch_open_interest 会触发 load_markets（OKX 拉全量 OPTION 极慢，拖死 watchdog）
# → 改直接 REST 端点，单次采样 <2s
EXCHANGES = ["okx", "bitget", "kucoin"]
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "DOGE/USDT:USDT"]
OI_SURGE_RATIO = 1.25     # 当前 OI / 基线均值 > 1.25 触发"放大"告警
PRICE_STABLE = 0.01       # 同期价格变动 < 1% 才算"价格没动"
STEP_SURGE = 1.15         # 相邻两次采样跳增 15% 触发"跳增"告警
BASE_WINDOW_HOURS = 24    # 基线窗口
MIN_BASE_SAMPLES = 6      # 至少 6 个采样才建立基线（约 3 小时 @30min）

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

PROXY = os.environ.get("PROXY", "")
PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
SESSION = requests.Session()
if PROXIES:
    SESSION.proxies.update(PROXIES)
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})


def fmt_num(v, suffix=""):
    """None 安全格式化：数值转千分位，None/NaN 显示 '-'。"""
    try:
        if v is None or v != v:  # NaN 自不等
            return "-"
        return f"{v:,.0f}{suffix}"
    except (TypeError, ValueError):
        return "-"


# ---- REST 直连层（替代 ccxt，2026-08-15 重构） ----
# 每所一个快照函数：返回 {oi_contracts, oi_usd, price, funding_rate}，失败抛异常

def _okx_snapshot(symbol):
    """OKX: /api/v5/public/open-interest + ticker + funding-rate"""
    base = symbol.split("/")[0] + "-USDT-SWAP"
    oi = SESSION.get(f"https://www.okx.com/api/v5/public/open-interest?instId={base}", timeout=15).json()
    oi_row = (oi.get("data") or [{}])[0]
    t = SESSION.get(f"https://www.okx.com/api/v5/market/ticker?instId={base}", timeout=15).json()
    t_row = (t.get("data") or [{}])[0]
    fr = SESSION.get(f"https://www.okx.com/api/v5/public/funding-rate?instId={base}", timeout=15).json()
    fr_row = (fr.get("data") or [{}])[0]
    return {
        "oi_contracts": float(oi_row.get("oi") or 0),
        "oi_usd": None,
        "price": float(t_row.get("last") or 0),
        "funding_rate": float(fr_row.get("fundingRate")) if fr_row.get("fundingRate") else None,
    }


def _bitget_snapshot(symbol):
    """Bitget: /api/v2/mix/market/open-interest + ticker + current-fund-rate"""
    sym = symbol.split("/")[0] + "USDT"

    def _first(data):
        # Bitget 部分端点 data 是 list（[{...}]），部分是 dict —— 统一取第一个
        if isinstance(data, list):
            return (data or [{}])[0]
        return data or {}

    oi = SESSION.get(f"https://api.bitget.com/api/v2/mix/market/open-interest?symbol={sym}&productType=USDT-FUTURES", timeout=15).json()
    oi_row = _first(oi.get("data"))
    # Bitget openInterestList[0].size 是张数（8/15 实测），不是 openInterest 字段
    oi_list = oi_row.get("openInterestList") or []
    oi_contracts = float(oi_list[0].get("size")) if oi_list and oi_list[0].get("size") else 0
    t = SESSION.get(f"https://api.bitget.com/api/v2/mix/market/ticker?symbol={sym}&productType=USDT-FUTURES", timeout=15).json()
    t_row = _first(t.get("data"))
    fr = SESSION.get(f"https://api.bitget.com/api/v2/mix/market/current-fund-rate?symbol={sym}&productType=USDT-FUTURES", timeout=15).json()
    fr_row = _first(fr.get("data"))
    return {
        "oi_contracts": oi_contracts,
        "oi_usd": float(oi_row.get("openInterestValue")) if oi_row.get("openInterestValue") else None,
        "price": float(t_row.get("lastPr") or 0),
        "funding_rate": float(fr_row.get("fundingRate")) if fr_row.get("fundingRate") else None,
    }


def _kucoin_snapshot(symbol):
    """KuCoin: /api/v1/contracts/active 一次拿全量 OI + ticker + funding"""
    map_ = {"BTC": "XBT", "ETH": "ETH", "SOL": "SOL", "DOGE": "DOGE"}
    base = symbol.split("/")[0]
    sym = map_.get(base, base) + "USDTM"
    active = SESSION.get("https://api-futures.kucoin.com/api/v1/contracts/active", timeout=15).json()
    row = next((c for c in (active.get("data") or []) if c.get("symbol") == sym), {})
    t = SESSION.get(f"https://api-futures.kucoin.com/api/v1/ticker?symbol={sym}", timeout=15).json()
    t_data = (t.get("data") or {})
    return {
        "oi_contracts": float(row.get("openInterest") or 0),
        "oi_usd": float(row.get("openInterestValue")) if row.get("openInterestValue") else None,
        "price": float(t_data.get("price") or t_data.get("last") or 0),
        "funding_rate": float(row.get("fundingRate")) if row.get("fundingRate") else None,
    }


SNAPSHOT_FN = {"okx": _okx_snapshot, "bitget": _bitget_snapshot, "kucoin": _kucoin_snapshot}


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
    # busy_timeout：多 Agent/多进程并发写同一 db 时防 `database is locked`（8/15 实测根因）
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.execute("PRAGMA busy_timeout=5000")
    init_db(conn)

    ts = int(time.time())
    all_alerts = []
    # 全局 deadline：3 所×4 币 ccxt 限速 sleep 可能拖到 150s+，cron watchdog 需要 90s 内完成
    deadline = time.time() + 90
    for name in EXCHANGES:
        if time.time() > deadline:
            print("[warn] 全局 90s deadline 到，剩余交易所跳过", file=sys.stderr)
            break
        try:
            fn = SNAPSHOT_FN[name]
        except KeyError:
            print(f"[skip] {name} 无快照函数")
            continue
        for symbol in SYMBOLS:
            if time.time() > deadline:
                print("[warn] 全局 90s deadline 到，剩余采样跳过", file=sys.stderr)
                break
            try:
                snap = fn(symbol)
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
