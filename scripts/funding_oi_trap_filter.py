#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funding × OI 陷阱过滤器（funding_oi_trap_filter.py）— digest 062 落地（2026-08-17）
====================================================================================
规则（@zhanglianzhong Day12 笔记，Bitget 4000万→200万 95% 对倒教训）：
  - funding 达标 + OI 平稳      = 可记录信号
  - funding 诱人 + OI 短期陡增   = 🚨 野庄对倒陷阱 → 排除（价格可画、深度可挂假单，
                                    OI 变化速率骗不了人）
  - OI 骤降                      = 拥挤出清观察

数据：data/oi_history.db（表 oi_snapshots：ts/exchange/symbol/oi_contracts/price/funding_rate）
      oi_monitor cron 每 30 分钟落库；4 币（BTC/ETH/SOL/DOGE）× 3 所（okx/bitget/kucoin）
      ⚠️ oi_contracts 各所单位不同 → 只做同所相对判断
产出：stdout 人话表格 + data/funding_oi_trap_log.jsonl（append）

用法：
  python scripts/funding_oi_trap_filter.py            # 跑一次，人话表格
  python scripts/funding_oi_trap_filter.py --json     # JSON 行（cron watchdog 用）

依赖：hermes venv python3.11（sqlite3/urllib 标准库即可）
"""
import argparse
import json
import sqlite3
import statistics
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "oi_history.db"
LOG_PATH = BASE_DIR / "data" / "funding_oi_trap_log.jsonl"

SYMBOLS = ["BTC", "ETH", "SOL", "DOGE"]
EXCHANGES = ["okx", "bitget", "kucoin"]

# 阈值（对齐 oi_monitor 的 OI_SURGE_RATIO=1.25 + 062 笔记语义）
SURGE_RATIO = 1.25          # 短期 OI / 基线 > 1.25 = 陡增（对倒特征）
DUMP_RATIO = 0.80           # 短期 OI / 基线 < 0.80 = 骤降（出清）
SHORT_WIN = 2               # 短期窗口 = 最近 N 个采样
BASE_WIN = 8                # 基线窗口 = 之前 N 个采样
FUNDING_HIGH = 0.0001       # |funding| ≥ 0.01%/期 视为显著（okx 8h 结算口径）


def load_series(conn, symbol):
    """读某币所有所的 (ts, oi) 序列，按所分组、按时间排序。"""
    rows = conn.execute(
        "SELECT ts, exchange, oi_contracts, funding_rate FROM oi_snapshots "
        "WHERE symbol=? ORDER BY exchange, ts", (f"{symbol}/USDT:USDT",)).fetchall()
    by_ex = {}
    for ts, ex, oi, fr in rows:
        by_ex.setdefault(ex, []).append((ts, oi, fr))
    return by_ex


def change_ratio(series):
    """短期均值 / 基线均值。返回 (ratio, short_avg, base_avg, n_short, n_base)。"""
    if len(series) < SHORT_WIN + 3:
        return None
    short = [oi for _, oi, _ in series[-SHORT_WIN:]]
    base = [oi for _, oi, _ in series[-(SHORT_WIN + BASE_WIN):-SHORT_WIN]]
    base = [x for x in base if x is not None]
    short = [x for x in short if x is not None]
    if not base or not short or min(base) <= 0:
        return None
    return (statistics.mean(short) / statistics.mean(base),
            statistics.mean(short), statistics.mean(base), len(short), len(base))


def latest_funding(series):
    """最近一个非 None funding_rate。"""
    for _, _, fr in reversed(series):
        if fr is not None:
            return fr
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="JSON 行输出（cron watchdog）")
    ap.add_argument("--hours", type=int, default=24, help="只看最近 N 小时（默认 24）")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    now = datetime.now().timestamp()
    cutoff = now - args.hours * 3600

    out = []
    for sym in SYMBOLS:
        by_ex = load_series(conn, sym)
        per_ex = {}
        for ex in EXCHANGES:
            series = [(ts, oi, fr) for ts, oi, fr in by_ex.get(ex, []) if ts >= cutoff]
            if len(series) < SHORT_WIN + 3:
                continue
            r = change_ratio(series)
            if not r:
                continue
            ratio, short_avg, base_avg, n_short, n_base = r
            funding = latest_funding(series)
            flag = "🟢 平稳" if 0.80 <= ratio <= 1.25 else ("🚨 陡增" if ratio > SURGE_RATIO else "📉 骤降")
            trap = (funding is not None and abs(funding) >= FUNDING_HIGH and ratio > SURGE_RATIO)
            if trap:
                flag += " ⚠️陷阱嫌疑(对倒)"
            per_ex[ex] = {"ratio": round(ratio, 3), "flag": flag, "funding": funding, "trap": trap}
            out.append({"ts": datetime.now().isoformat(timespec="seconds"), "symbol": sym,
                        "exchange": ex, "oi_ratio": round(ratio, 3), "short_avg": round(short_avg, 1),
                        "base_avg": round(base_avg, 1), "funding": funding, "trap": trap})
    conn.close()

    # 日志落盘（可审计，JSONL append）
    if out:
        with open(LOG_PATH, "a") as f:
            for rec in out:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if args.json:
        for rec in out:
            print(json.dumps(rec, ensure_ascii=False))
        return

    # 人话表格
    print(f"Funding × OI 陷阱过滤器（近 {args.hours}h，digest 062 规则）")
    print(f"{'币':<6}{'所':<8}{'OI短期/基线':>10}{'判定':<26}{'funding/期':>10}")
    print("-" * 66)
    for sym in SYMBOLS:
        by_ex = {}
        for rec in out:
            if rec["symbol"] == sym:
                by_ex[rec["exchange"]] = rec
        for ex in EXCHANGES:
            if ex not in by_ex:
                continue
            rec = by_ex[ex]
            fr = f"{rec['funding']*100:.4f}%" if rec["funding"] is not None else "-"
            flag = "🚨 陡增" if rec["oi_ratio"] > SURGE_RATIO else ("📉 骤降" if rec["oi_ratio"] < DUMP_RATIO else "🟢 平稳")
            if rec["trap"]:
                flag += " ⚠️陷阱嫌疑(对倒)"
            print(f"{sym:<6}{ex:<8}{rec['oi_ratio']:>10.3f}{flag:<26}{fr:>10}")
    traps = [r for r in out if r["trap"]]
    if traps:
        print("\n🚨 陷阱嫌疑（funding 高 + OI 陡增，062 规则应排除）:")
        for r in traps:
            print(f"  {r['symbol']}/{r['exchange']}  OI比 {r['oi_ratio']}  funding {r['funding']*100:.4f}%")
    else:
        print("\n→ 无陷阱信号（funding 高 + OI 陡增组合未出现）")


if __name__ == "__main__":
    sys.exit(main())
