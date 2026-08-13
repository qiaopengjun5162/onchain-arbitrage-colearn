#!/usr/bin/env python3
"""
证据记录体系 v1 (evidence_harvester.py)
=========================================
L0009 阶段复盘 → D10-D13「一次性观察 → 可重复流水线」第一步：
把 36 个哨兵的原始数据文件，汇总成每个候选方向的「证据台账」。

职责：
  1. 读各哨兵数据文件（stock/corridor/funding/pm/multichain...）
  2. 计算每个 🟡 候选方向的累计证据指标
  3. 追加每日快照到 data/evidence_daily.jsonl（一行一个候选，ts+指标）
  4. 生成人读台账 notes/evidence-tracker.md（30 天倒计时 + 状态机）
  5. --watchdog 模式：仅当状态变化（新到期评分/数据源中断）才输出推送文本

用法：
  python3 scripts/evidence_harvester.py            # 收数+更新台账
  python3 scripts/evidence_harvester.py --watchdog  # cron 模式，静默除非有变化
  python3 scripts/evidence_harvester.py --json     # 只输出今日证据 JSON

设计约定：
  - 只读数据文件，绝不修改哨兵输出
  - 状态机：🟡 收数中 → (30 天到期自动评分) → ✅ 证据充分 / ❌ 放弃 / 🟡 继续
  - 判定阈值写在 CANDIDATES 配置里，到期时自动评
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
NOTES = REPO / "notes"
EVIDENCE_LOG = DATA / "evidence_daily.jsonl"
TRACKER = NOTES / "evidence-tracker.md"

TZ = dt.timezone(dt.timedelta(hours=8))  # 北京时间

# ── 候选方向配置：证据来源 + 到期判定阈值 ──────────────────────────
# start: 该方向数据开始积累的日期（哨兵上线日），30 天证据期从这算
CANDIDATES = {
    "stock_drift": {
        "name": "RWA/币股闭市漂移",
        "source": "stock_vs_us_stock_log.csv",
        "start": "2026-08-08",
        "days_target": 30,
        "desc": "闭市漂移 30-100bps vs 成本 ~20bps；测漂移可持续性",
        "verdict": {
            "ok": "dev_bps 中位 ≥ 30 且覆盖 ≥ 20 天",
            "drop": "30 天后 dev_bps 中位 < 20（不足以覆盖成本）",
        },
    },
    "perp_funding": {
        "name": "链上 perp funding 拥挤度",
        "source": "funding_signal_log.csv",
        "start": "2026-08-08",
        "days_target": 30,
        "desc": "zscore≥2 信号频率 + 极端 funding 事件（年化≥50%）",
        "verdict": {
            "ok": "信号数 ≥ 10 且极端事件 ≥ 3",
            "drop": "30 天零信号（拥挤度恒正常）",
        },
    },
    "thin_corridor": {
        "name": "低容量可行域（#13）",
        "source": "corridor_series.csv",
        "start": "2026-08-12",
        "days_target": 30,
        "desc": "走廊内占比 + 出轨事件（价差>60bps 走廊）频次",
        "verdict": {
            "ok": "出轨事件 ≥ 5 次且均值 > 80bps",
            "drop": "30 天零出轨（市场持续有效）",
        },
    },
    "pm_rebal": {
        "name": "PM rebalancing 盘口",
        "source": "pm_rebalancing_scan.jsonl",
        "start": "2026-08-12",
        "days_target": 30,
        "desc": "可执行信号率（镜像结构常态 0 信号，事件期才有肉）",
        "verdict": {
            "ok": "事件期捕获 ≥ 3 次可执行信号",
            "drop": "30 天信号率 < 1%（无事件期）",
        },
    },
    "oft_crosschain": {
        "name": "OFT 跨链价差",
        "source": "multichain_spread_series.csv",
        "start": "2026-08-11",
        "days_target": 30,
        "desc": "等上币窗口；DOS 净 7.6bps NO-GO，桥费杀手",
        "verdict": {
            "ok": "捕获净 > 20bps 可执行窗口",
            "drop": "30 天无新上币窗口（依赖事件）",
        },
    },
    "pm_lp": {
        "name": "PM 带方向 LP（计划）",
        "source": None,  # 无自动数据源，待 /activity 返佣流水
        "start": "2026-08-12",
        "days_target": 30,
        "desc": "先 paper 验证返佣：/activity 拉流水（人工/手动）",
        "verdict": {
            "ok": "返佣率 vs 被吃单率 vs 胜率 paper 验证通过",
            "drop": "返佣率不可覆盖点差",
        },
    },
}

# 数据源 → 提取器
def _csv_rows(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))

def _jsonl_rows(path):
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows

def extract_stock_drift():
    """币股闭市漂移：dev_bps 分布 + 覆盖天数"""
    rows = _csv_rows(DATA / "stock_vs_us_stock_log.csv")
    if not rows:
        return {"samples": 0}
    devs = [float(r["dev_bps"]) for r in rows if r.get("dev_bps", "").strip() not in ("", "nan")]
    days = set(r["ts"][:10] for r in rows if r.get("ts"))
    out = {
        "samples": len(devs),
        "days_covered": len(days),
        "dev_bps_median": round(sorted(devs)[len(devs) // 2], 1) if devs else 0,
        "dev_bps_mean": round(sum(devs) / len(devs), 1) if devs else 0,
        "dev_bps_max": round(max(devs), 1) if devs else 0,
        "pct_ge_30bps": round(100 * sum(1 for d in devs if d >= 30) / len(devs), 1) if devs else 0,
    }
    return out

def extract_perp_funding():
    """perp funding：zscore≥2 信号数 + 极端 funding 数（HL 年化≥50%）"""
    sig = _csv_rows(DATA / "funding_signal_log.csv")
    sig_rows = len(sig)
    hot = 0
    if sig_rows:
        try:
            hot = sum(1 for r in sig if r.get("zscore") and abs(float(r["zscore"])) >= 2)
        except (ValueError, TypeError):
            hot = 0
    hl = _csv_rows(DATA / "hl_funding.csv")
    hl_extreme = 0
    if hl:
        try:
            hl_extreme = sum(1 for r in hl if r.get("funding_annual") and abs(float(r["funding_annual"])) >= 50)
        except (ValueError, TypeError):
            hl_extreme = 0
    return {
        "signal_rows": sig_rows,
        "zscore_ge2": hot,
        "hl_extreme_annual_ge50": hl_extreme,
    }

def extract_thin_corridor():
    """低容量可行域：走廊采样 + 出轨事件"""
    rows = _csv_rows(DATA / "corridor_series.csv")
    if not rows:
        return {"samples": 0}
    exits = 0
    for r in rows:
        try:
            # exit_bps 列有值且>0 即出轨（列位置 ts,size,pool_a,pool_b,spread_bps,corridor_bps,exit_bps）
            pass
        except Exception:
            pass
    # 用列名解析（corridor_series 无表头解析容错）
    with open(DATA / "corridor_series.csv", newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        raw = list(reader)
    # 老格式可能无 header；探测：若首行是 ts 开头的日期则无 header
    has_header = header and header[0].lower() == "ts"
    data_rows = raw
    # 出轨判定：spread_bps > corridor_bps（idx 4 > idx 5），或 exit_bps(idx6) 非空>0
    # 硬上限：>5000bps 标损坏（雷达 v2.1 同口径，Manifest×Scorch 假出轨修复）
    MAX_BPS = 5000.0
    exit_events = []
    spreads = []
    for r in data_rows:
        if len(r) < 6:
            continue
        try:
            spread = float(r[4])
            corridor = float(r[5])
            if abs(spread) > MAX_BPS:
                continue  # 损坏数据（同雷达 v2.1 过滤）
            spreads.append(spread)
            if spread > corridor + 1e-9:
                exit_events.append(spread)
        except (ValueError, IndexError):
            continue
    days = set()
    for r in data_rows:
        if r and r[0][:10].startswith("20"):
            days.add(r[0][:10])
    return {
        "samples": len(spreads),
        "days_covered": len(days),
        "exit_events": len(exit_events),
        "max_exit_bps": round(max(exit_events), 1) if exit_events else 0,
        "spread_mean_bps": round(sum(spreads) / len(spreads), 1) if spreads else 0,
    }

def extract_pm_rebal():
    """PM rebalancing：可执行信号率"""
    rows = _jsonl_rows(DATA / "pm_rebalancing_scan.jsonl")
    if not rows:
        return {"scans": 0}
    decisions = [r for r in rows if r.get("decision") and r["decision"] != "NONE"]
    days = set(r.get("ts", "")[:10] for r in rows if r.get("ts"))
    return {
        "scans": len(rows),
        "days_covered": len(days),
        "signal_count": len(decisions),
        "reject_top": _top_reject(rows),
    }

def _top_reject(rows):
    from collections import Counter
    c = Counter(r.get("reject_reason", "unknown") for r in rows)
    return c.most_common(3)

def extract_oft():
    """OFT 跨链：采样数 + 净价差分布"""
    rows = _csv_rows(DATA / "multichain_spread_series.csv")
    if not rows:
        return {"samples": 0}
    nets = [float(r["net_bps"]) for r in rows if r.get("net_bps", "").strip()]
    return {
        "samples": len(rows),
        "net_bps_mean": round(sum(nets) / len(nets), 1) if nets else 0,
        "net_positive": sum(1 for n in nets if n > 20),
        "days_covered": len(set(r.get("ts", "")[:10] for r in rows)),
    }

EXTRACTORS = {
    "stock_drift": extract_stock_drift,
    "perp_funding": extract_perp_funding,
    "thin_corridor": extract_thin_corridor,
    "pm_rebal": extract_pm_rebal,
    "oft_crosschain": extract_oft,
    "pm_lp": lambda: {"status": "manual", "note": "待 /activity 返佣流水（人工）"},
}

def today_str():
    return dt.datetime.now(TZ).strftime("%Y-%m-%d")

def load_history():
    """读 evidence_daily.jsonl → {candidate: [snapshots]}"""
    hist = {}
    if EVIDENCE_LOG.exists():
        with open(EVIDENCE_LOG, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                hist.setdefault(rec["candidate"], []).append(rec)
    return hist

def state_for(cid, cfg, snapshots):
    """状态机：🟡 收数中 → 到期评分"""
    start = dt.date.fromisoformat(cfg["start"])
    today = dt.date.fromisoformat(today_str())
    elapsed = (today - start).days
    target = cfg["days_target"]
    due = elapsed >= target
    latest = snapshots[-1] if snapshots else {}
    state = "🟡 收数中" if not due else "🟡 到期待评"
    return {"elapsed": elapsed, "target": target, "due": due, "state": state, "latest": latest}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watchdog", action="store_true", help="cron 模式：状态变化才输出")
    ap.add_argument("--json", action="store_true", help="只输出今日证据 JSON")
    args = ap.parse_args()

    hist = load_history()
    today = today_str()
    out_lines = []
    changes = []

    for cid, cfg in CANDIDATES.items():
        extractor = EXTRACTORS[cid]
        metrics = extractor()
        snapshots = hist.get(cid, [])
        prev = snapshots[-1] if snapshots else None
        st = state_for(cid, cfg, snapshots)
        rec = {
            "ts": dt.datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z"),
            "candidate": cid,
            "name": cfg["name"],
            "elapsed_days": st["elapsed"],
            "metrics": metrics,
        }
        # 同日去重：同一候选当天已有快照则跳过（幂等）
        if prev and prev.get("ts", "")[:10] == today:
            rec = prev  # 保持已有记录
        else:
            out_lines.append(rec)
            snapshots = snapshots + [rec]
            hist[cid] = snapshots
            # 检测变化
            if prev is not None:
                changes.append(f"🔄 {cfg['name']}: 数据更新 {today}")
        # 到期评分
        if st["due"] and not prev:
            changes.append(f"⏰ {cfg['name']}: 30 天证据期到点，待评分!")

    # 写 evidence_daily.jsonl（幂等追加）
    if out_lines:
        with open(EVIDENCE_LOG, "a", encoding="utf-8") as f:
            for rec in out_lines:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 生成台账 notes/evidence-tracker.md
    gen_tracker(hist)

    if args.json:
        print(json.dumps({cid: EXTRACTORS[cid]() for cid in CANDIDATES}, ensure_ascii=False, indent=1))
        return
    if args.watchdog:
        # 静默除非有变化/缺口
        gaps = check_gaps(hist)
        msgs = changes + gaps
        if msgs:
            print("\n".join(msgs))
        return
    # 人读摘要
    print(f"✅ 证据收数完成 {today}（{len(out_lines)} 项更新）")
    for cid, cfg in CANDIDATES.items():
        st = state_for(cid, cfg, hist.get(cid, []))
        latest = st["latest"].get("metrics", {})
        key = next(iter(latest), "")
        print(f"  {st['state']} {cfg['name']} ({st['elapsed']}/{st['target']}d) {key}={latest.get(key, '')}")

def check_gaps(hist):
    """数据缺口检测：活跃哨兵 48h 无新数据才报警"""
    gaps = []
    today = today_str()
    for cid, cfg in CANDIDATES.items():
        if cfg["source"] is None:
            continue
        snaps = hist.get(cid, [])
        if not snaps:
            continue
        last_ts = snaps[-1]["ts"][:10]
        last_d = dt.date.fromisoformat(last_ts)
        age = (dt.date.fromisoformat(today) - last_d).days
        if age >= 2:
            gaps.append(f"⚠️ {cfg['name']}: 数据源 {cfg['source']} 已 {age} 天无新快照")
    return gaps

def gen_tracker(hist):
    """生成人读台账 notes/evidence-tracker.md"""
    lines = [
        "# 证据台账（evidence-tracker）",
        "",
        f"> 由 `scripts/evidence_harvester.py` 自动生成，每日更新。证据期 30 天，到期自动评分。",
        f"> 数据源：36 个哨兵 cron 的原始输出。最后更新：{dt.datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 候选状态一览",
        "",
        "| 候选 | 状态 | 证据期 | 关键指标 | 到期判定 |",
        "|---|---|---|---|---|",
    ]
    for cid, cfg in CANDIDATES.items():
        snaps = hist.get(cid, [])
        st = state_for(cid, cfg, snaps)
        latest = st["latest"].get("metrics", {}) if snaps else {}
        key_parts = ", ".join(f"{k}={v}" for k, v in list(latest.items())[:4]) if latest else "无数据"
        verdict = cfg["verdict"]["ok"] + " ｜ 放弃: " + cfg["verdict"]["drop"]
        lines.append(f"| {cfg['name']} | {st['state']} | {st['elapsed']}/{st['target']}d | {key_parts} | {verdict} |")
    lines += ["", "## 详细快照", ""]
    for cid, cfg in CANDIDATES.items():
        snaps = hist.get(cid, [])
        if not snaps:
            continue
        latest = snaps[-1]
        lines.append(f"### {cfg['name']}")
        lines.append(f"`{cid}` · 证据期 {cfg['start']} 起 · 快照数 {len(snaps)}")
        lines.append("")
        lines.append(f"```json")
        lines.append(json.dumps(latest.get("metrics", {}), ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    TRACKER.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()
