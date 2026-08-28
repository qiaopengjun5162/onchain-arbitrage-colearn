#!/usr/bin/env python3
"""
费率档位跳变检测（watchdog 模式）
=================================
触发：HL/GT 案例（2026-08-28 归档）——Gate 两次改费率 0.02%→0.5%→1%（8h），
      每次跳变 = 事件窗口：改到高位 = 正向建仓（做空收高费率），改到低位/转负 = 反向建仓（做多收负费率）。

数据源：data/funding_spread_scan.jsonl（funding_spread_scanner 每次扫描落盘的全量 rows，8h/次）
检测：
1. 跨快照跳变：同一 base+exchange 的 8h 费率，相邻两次扫描 |Δ| ≥ JUMP_BPS → 报警
2. 快照内跳变：top_ex 的 history（近 6 期）里 |最后两期差| ≥ JUMP_BPS → 报警（同一结算周期的参数变更）

用法：
  python3 scripts/funding_rate_jump_watch.py            # watchdog：有跳变才输出
  python3 scripts/funding_rate_jump_watch.py --debug    # 全量输出

接入：run_funding_spread.sh 第 3 步（cron e5c61dedb11b 每 8h 扫描后顺带跑）
"""
import json
import sys
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "funding_spread_scan.jsonl"
JUMP_BPS = 30        # |Δ费率| ≥ 30bps/8h（0.3%）视为档位跳变（Gate 案例 0.02→0.5% = 48bps）
DEBUG = "--debug" in sys.argv


def load_last2():
    lines = [l for l in LOG_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(lines) < 2:
        return None, None
    return json.loads(lines[-2]), json.loads(lines[-1])


def rates_of(snap):
    """{base: {exchange: rate_decimal}}"""
    out = {}
    for r in (snap or {}).get("rows", []):
        out[r["base"]] = r.get("rates") or {}
    return out


def fmt(pct):
    return f"{pct:+.2f}%"


def main():
    prev, cur = load_last2()
    if prev is None or cur is None:
        if DEBUG:
            print("⚠️ 快照不足 2 次，无法检测")
        return
    prev_r, cur_r = rates_of(prev), rates_of(cur)

    alerts = []
    seen = set()

    # 1. 跨快照跳变（同 base+ex 相邻两次扫描）
    for base, rates_c in cur_r.items():
        rates_p = prev_r.get(base)
        if not rates_p:
            continue
        for ex, r_new in rates_c.items():
            if ex not in rates_p:
                continue
            r_old = rates_p[ex]
            if r_old is None or r_new is None:
                continue
            jump = abs(r_new - r_old) * 10_000
            if jump < JUMP_BPS:
                continue
            key = (base, ex)
            if key in seen:
                continue
            seen.add(key)
            direction = "正向建仓窗口(做空收高费率)" if r_new > r_old else "反向建仓窗口(做多收负费率)"
            alerts.append(
                f"🚨 费率档位跳变: {base} [{ex}] {fmt(r_old*100)}→{fmt(r_new*100)} "
                f"(8h) Δ{jump:.0f}bps — {direction}")

    # 2. 快照内 top_ex history 跳变（同一结算周期的参数变更）
    for r in (cur or {}).get("rows", []):
        hist = r.get("history") or []
        base, ex = r["base"], r.get("top_ex")
        if len(hist) >= 2 and ex:
            jump = abs(hist[-1] - hist[-2]) * 10_000
            if jump >= JUMP_BPS and (base, ex) not in seen:
                seen.add((base, ex))
                direction = "正向建仓窗口(做空收高费率)" if hist[-1] > hist[-2] else "反向建仓窗口(做多收负费率)"
                alerts.append(
                    f"🚨 费率档位跳变: {base} [{ex}] {fmt(hist[-2]*100)}→{fmt(hist[-1]*100)} "
                    f"(8h) Δ{jump:.0f}bps — {direction}")

    if DEBUG:
        print(f"[debug] 快照 {cur.get('ts')} | 候选 {len(cur_r)} | 跳变 {len(alerts)}")
        for a in alerts:
            print(a)
    else:
        if alerts:
            print("费率档位跳变 @ 每 8h 扫描")
            for a in alerts[:15]:
                print(a)


if __name__ == "__main__":
    main()
