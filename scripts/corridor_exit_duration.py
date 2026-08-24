#!/usr/bin/env python3
"""小池价差持续性分析（research-backlog #9 待办落地，2026-08-24）。

假设验证：薄池价差持续更久（竞争者少 → 价差修复慢）。
数据：corridor_series.csv.v3.bak（历史 08-10~08-24 2931 行，v3 无 dev/suspect 列）
     + corridor_series.csv（v4 新增，含 state 列）
方法：
1. 深度代理 = 每池 100 SOL 报价档出现频次（薄池探测结论：100 SOL 档频次 = 接大单能力）
2. 出轨事件 = exit_bps >= 20（价差超出两腿费率走廊 ≥20bps），排除 |spread|>5000 损坏
3. 持续时间 = 同一配对（池名排序归一 + 金额档）连续出轨样本的 ts 跨度
4. 按深度分层比较持续时间分布

用法：python3 scripts/corridor_exit_duration.py [--min-exit 20]
输出：事件表 + 分层统计 + 结论
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
FILES = ["corridor_series.csv.v3.bak", "corridor_series.csv"]


def parse_ts(s: str):
    for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def load_rows():
    rows = []
    for f in FILES:
        p = DATA / f
        if not p.exists():
            continue
        with open(p) as fh:
            for r in csv.DictReader(fh):
                try:
                    spread = float(r.get("spread_bps") or 0)
                    exit_bps = float(r.get("exit_bps") or 0)
                except (TypeError, ValueError):
                    continue
                rows.append({
                    "ts": r["ts"], "ts_dt": parse_ts(r["ts"]),
                    "size": r.get("size", ""), "a": r["pool_a"], "b": r["pool_b"],
                    "spread": spread, "exit": exit_bps,
                    "state": r.get("state", "n/a"),
                })
    return [r for r in rows if r["ts_dt"]]


def key_of(r):
    a, b = sorted([r["a"], r["b"]])
    return f"{r['size']}:{a}<->{b}"


def depth_ladder(rows):
    """100 SOL 报价档出现频次 = 接大单能力代理。"""
    cnt = defaultdict(int)
    for r in rows:
        if r["size"] == "100":
            cnt[r["a"]] += 1
            cnt[r["b"]] += 1
    return cnt


def tier_of(pool, ladder, anchor_pool="Raydium"):
    if pool == anchor_pool:
        return "深(锚点)"
    n = ladder.get(pool, 0)
    if n >= 100:
        return "深"
    if n >= 40:
        return "中"
    if n >= 1:
        return "薄"
    return "未知"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-exit", type=float, default=20.0)
    args = ap.parse_args()

    rows = load_rows()
    rows = [r for r in rows if abs(r["spread"]) <= 5000]  # 清损坏报价
    rows.sort(key=lambda r: r["ts_dt"])

    ladder = depth_ladder(rows)
    print(f"深度阶梯（100 SOL 档频次，共 {len(ladder)} 池）:")
    for pool, n in sorted(ladder.items(), key=lambda x: -x[1]):
        print(f"  {pool}: {n}")

    # 出轨事件 = exit >= min；按配对 key 连续样本聚合成事件
    exits = [r for r in rows if r["exit"] >= args.min_exit]
    print(f"\n出轨样本（exit≥{args.min_exit:.0f}bps）：{len(exits)} 条 / 总样本 {len(rows)} 条")

    by_key = defaultdict(list)
    for r in exits:
        by_key[key_of(r)].append(r)
    # 每个 key 内部按时间排序，相邻样本间隔 < 90min 视为同一事件
    events = []
    for k, rs in by_key.items():
        rs.sort(key=lambda r: r["ts_dt"])
        cur = [rs[0]]
        for r in rs[1:]:
            gap = (r["ts_dt"] - cur[-1]["ts_dt"]).total_seconds() / 60
            if gap <= 90:
                cur.append(r)
            else:
                events.append(cur)
                cur = [r]
        events.append(cur)

    print(f"出轨事件（连续样本合并，间隔>90min 断事件）：{len(events)} 个\n")
    print(f"{'配对':<34}{'档':<6}{'池B档':<8}{'样本数':>5}{'跨度h':>7}{'max exit':>9}")
    stats = defaultdict(list)
    for ev in events:
        a, b = sorted([ev[0]["a"], ev[0]["b"]])
        other = b if a == "Raydium" else a
        tier = tier_of(other, ladder)
        span_h = (ev[-1]["ts_dt"] - ev[0]["ts_dt"]).total_seconds() / 3600
        if len(ev) == 1:
            span_h = 0.5  # 单样本 = 至少一个采样间隔
        mx = max(r["exit"] for r in ev)
        stats[tier].append(span_h)
        print(f"{a}↔{b:<18}{ev[0]['size']:<6}{tier:<8}{len(ev):>5}{span_h:>7.1f}{mx:>9.1f}")

    print("\n按深度分层持续时间（h）:")
    print(f"{'层':<10}{'事件数':>6}{'中位h':>8}{'均值h':>8}{'最大h':>8}")
    for tier in ["深(锚点)", "深", "中", "薄", "未知"]:
        if tier not in stats:
            continue
        v = sorted(stats[tier])
        med = v[len(v) // 2]
        mean = sum(v) / len(v)
        print(f"{tier:<10}{len(v):>6}{med:>8.1f}{mean:>8.1f}{max(v):>8.1f}")

    # 结论
    print("\n结论:")
    if len(events) < 30:
        print("  14 天出轨事件过少 → 持续时间分层统计不具显著性；")
        print("  「薄池价差持续更久」无法用现有数据验证（事件样本不足，非假设错误）；")
        print("  与 D17/D18 一致：常驻出轨几乎不存在，机会只在事件窗口。")
    else:
        print("  事件样本足够，按上表分层结论为准。")


if __name__ == "__main__":
    main()
