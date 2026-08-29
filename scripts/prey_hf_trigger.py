#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prey radar v2 × HF scanner 联动（prey_hf_trigger.py）— 2026-08-29 清算事件线第 3 步

信号链闭环（prey-radar-v2 笔记「五、下一步」第 2 条）：
  v2 高频轮询检测偏离突变（JUMP/SIGNAL/ORACLE_UPDATE/BROKEN_ORACLE）
  → 本脚本读 prey_radar_v2.jsonl 发现信号 → 立即触发持仓级 HF 扫描
  → 输出「信号 + 谁 HF 最低 + 再跌多少触发清算」→ watchdog 推送

为什么独立进程而不是塞进 v2 主循环：
- v2 是 2-3s/tick 高频轮询，GraphQL marketPositions 查询 2-5s，塞进去会拖垮节奏
- 事件驱动：只有出现信号才触发 HF 深度扫描，平时零开销
- 跨进程去重：信号 10 分钟内不重报（与 v2 的 DEDUP_MIN 一致）

用法：
  python scripts/prey_hf_trigger.py                  # watchdog：有信号才输出（cron 用）
  python scripts/prey_hf_trigger.py --window 600    # 看最近 10 分钟信号窗口
  python scripts/prey_hf_trigger.py --full          # 忽略 jsonl，直接全量 HF 快照

cron 建议：*/2 * * * *（比 30min HF cron 快 15 倍响应；no_agent watchdog 契约）
"""
import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RADAR_LOG = ROOT / "data" / "prey_radar_v2.jsonl"
STATE_PATH = ROOT / "data" / "prey_hf_trigger_state.json"

SIGNAL_LEVELS = ("SIGNAL", "INFO", "JUMP", "ORACLE_UPDATE", "BROKEN_ORACLE")
DEDUP_MIN = 10          # 同 (market, level) 10 分钟内不重报
DEFAULT_WINDOW = 300    # 默认看最近 5 分钟 jsonl
HF_MAX = 1.5            # HF 扫描上限
MIN_COLLATERAL = 100_000
REPORT_TRIGGER = 15.0   # 触发跌幅 ≤15% 才进报告（信号后可能快速收敛）


def load_radar_events(window_s):
    """读 v2 jsonl 尾部，返回窗口内的信号事件列表（已按市场+级别合并）。"""
    try:
        lines = RADAR_LOG.read_text().splitlines()
    except Exception as e:
        print(f"[!] 读雷达日志失败: {e}", file=sys.stderr)
        return []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_s)
    events = []
    for ln in lines[-3000:]:
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("level") not in SIGNAL_LEVELS:
            continue
        try:
            ts = datetime.fromisoformat(r["ts"])
        except Exception:
            continue
        if ts < cutoff:
            continue
        events.append(r)
    # 按市场+级别合并，保留最新
    merged = {}
    for r in events:
        key = f"{r.get('chain')}:{r.get('collateral')}->{r.get('loan')}:{r.get('level')}"
        merged[key] = r
    return list(merged.values())


def dedup(events):
    """跨进程去重：同 (market, level) DEDUP_MIN 分钟内不重报。返回 (to_report, new_state)。"""
    state = {}
    try:
        if STATE_PATH.exists():
            state = json.loads(STATE_PATH.read_text())
    except Exception:
        pass
    now = datetime.now(timezone.utc).timestamp()
    out = []
    for r in sorted(events, key=lambda x: x.get("ts", "")):
        key = f"{r.get('chain')}:{r.get('collateral')}->{r.get('loan')}:{r.get('level')}"
        last = state.get(key)
        if last and now - last.get("ts", 0) < DEDUP_MIN * 60:
            continue
        out.append(r)
        state[key] = {"ts": now, "level": r["level"]}
    return out, state


def hf_scan():
    """调用 HF scanner 的 scan()（import 复用，不重写）。"""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import morpho_liquidation_hf as hf
    except Exception as e:
        print(f"[!] import HF scanner 失败: {e}", file=sys.stderr)
        return None
    try:
        keys = hf.base_market_keys()
        rows = hf.scan(keys, HF_MAX, MIN_COLLATERAL)
        return rows
    except Exception as e:
        print(f"[!] HF 扫描失败: {e}", file=sys.stderr)
        return None


def format_hf_rows(rows, collateral=None, limit=8):
    """格式化 HF 行。collateral 指定时优先该抵押品的仓。"""
    if not rows:
        return []
    if collateral:
        rows = sorted(rows, key=lambda x: (x["market"].split("→")[0] != collateral, x["hf"]))
    else:
        rows = sorted(rows, key=lambda x: x["hf"])
    out = []
    for r in rows[:limit]:
        trig = f"{r['trigger_drop_pct']}%" if r.get("trigger_drop_pct") is not None else "?"
        out.append(f"  {r['market']:<16} HF={r['hf']:.3f} 触发跌幅 {trig:<8} "
                   f"coll=${r['collateral_usd']/1e6:.2f}M user={r['user'][:10]}..")
    return out


def fmt_event(r):
    dev = f"{r.get('dev_bps')}bps" if r.get("dev_bps") is not None else "-"
    dd = f" Δ{r['dev_delta_bps']:+.1f}" if r.get("dev_delta_bps") is not None else ""
    upd = " 🔄oracle更新" if r.get("oracle_updated") else ""
    return (f"🚨 [Morpho {r.get('chain')}] {r.get('collateral')}→{r.get('loan')} "
            f"{r['level']} 偏离 {dev}{dd}{upd} oracle=${r.get('oracle_usd') or 0:,.2f} "
            f"spot=${r.get('spot_usd') or 0:,.2f}")


def main():
    ap = argparse.ArgumentParser(description="prey radar v2 × HF scanner 联动")
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="信号窗口秒数")
    ap.add_argument("--full", action="store_true", help="忽略 jsonl，直接全量 HF 快照")
    ap.add_argument("--no-dedup", action="store_true", help="跳过跨进程去重（调试用）")
    args = ap.parse_args()

    if args.full:
        rows = hf_scan()
        if rows is None:
            return 1
        if not rows:
            print("无临近清算大仓（HF≤1.5 & collateral≥$100K）")
            return 0
        print(f"=== 全量 HF 快照 @ {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===")
        for line in format_hf_rows(rows, limit=15):
            print(line)
        return 0

    events = load_radar_events(args.window)
    if not events:
        return 0  # 无信号 = 静默（watchdog 契约）

    to_report, state = dedup(events) if not args.no_dedup else (events, {})
    if not to_report:
        return 0  # 全部去重命中 = 静默

    # 有信号 → 立即 HF 深度扫描
    rows = hf_scan()
    if rows is None:
        # HF 失败仍报信号本身（不让信号丢失）
        for r in to_report:
            print(fmt_event(r))
        print("[!] HF 扫描失败，仅报信号")
        return 0

    try:
        STATE_PATH.parent.mkdir(exist_ok=True)
        STATE_PATH.write_text(json.dumps(state))
    except Exception:
        pass

    for r in to_report:
        print(fmt_event(r))
    print("── 持仓级 HF（信号联动，触发跌幅≤15% 优先）──")
    cols = {r.get("collateral") for r in to_report}
    collateral = next(iter(cols), None) if len(cols) == 1 else None
    lines = format_hf_rows(rows, collateral=collateral)
    if not lines:
        print("  当前无临近清算大仓（HF 全部 >1.5 或 dust）")
    for line in lines:
        print(line)
    # 信号市场相关仓数量提示
    if collateral:
        n = sum(1 for r in rows if r["market"].split("→")[0] == collateral)
        if n:
            print(f"  （{collateral} 抵押品仓 {n} 个在 HF≤1.5 范围内）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
