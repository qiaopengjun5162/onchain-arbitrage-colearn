#!/usr/bin/env python3
"""Jito bundle 监控：MEV 活跃度指标（只读）。

对应 notes/solana/README.md 研究线「Jito / MEV / bundle / block engine」：
- bundles.jito.wtf/api/v1/bundles/recent：最近待处理 bundle 队列
- landedTipLamports：bundle 支付的小费（lamports）——MEV 竞争强度直接指标
- tip 分布（P50/P99.9）+ bundle 吞吐 = 链上 MEV 活跃度仪表盘

意义：
- priority fee 高 = 区块空间竞价激烈（普通交易通道）
- Jito tip 高 = 套利/抢跑 bundle 竞争激烈（专用通道）
- 两者对照 = Solana 执行层竞争全景（呼应 notes/solana/README.md 三论点：链快→速度游戏）

用法：
    python scripts/jito_bundle_monitor.py             # 单次
    python scripts/jito_bundle_monitor.py --watch 3600
    python scripts/jito_bundle_monitor.py --watchdog  # cron：静默，只有 tip 异常才报

依赖：hermes venv python3.11（requests）
"""

import argparse
import csv
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 15
URL = "https://bundles.jito.wtf/api/v1/bundles/recent"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "jito_bundle_history.csv"

# 阈值（lamports tip；1 SOL = 1e9 lamports）
WARN_TIP_P99 = 1_000_000     # P99.9 tip >= 0.001 SOL 黄色（MEV 活跃）
ALERT_TIP_P99 = 10_000_000   # P99.9 tip >= 0.01 SOL 红色（抢跑潮）


def collect() -> dict:
    r = requests.get(URL, timeout=TIMEOUT, proxies=PROXIES)
    r.raise_for_status()
    bundles = r.json()
    if not bundles:
        return {"error": "空结果"}

    tips = [b.get("landedTipLamports", 0) for b in bundles]
    landed = [b for b in bundles if b.get("landedTipLamports", 0) > 0]
    txs_count = sum(len(b.get("transactions", [])) for b in bundles)

    def pct(lst, p):
        if not lst:
            return 0
        lst = sorted(lst)
        return lst[min(len(lst) - 1, int(len(lst) * p))]

    return {
        "n_bundles": len(bundles),
        "n_with_tip": len(landed),
        "n_txs": txs_count,
        "p50_tip": pct(tips, 0.5),
        "p99_tip": pct(tips, 0.99),
        "max_tip": max(tips) if tips else 0,
        "mean_tip": statistics.mean(tips) if tips else 0,
        "std_tip": statistics.stdev(tips) if len(tips) > 1 else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--watchdog", action="store_true")
    args = ap.parse_args()

    def tick():
        try:
            s = collect()
        except Exception as e:
            if not args.watchdog:
                print(f"[err] {e}")
            return 1
        if "error" in s:
            if not args.watchdog:
                print(f"[err] {s['error']}")
            return 1

        hot = s["p99_tip"] >= WARN_TIP_P99
        extreme = s["p99_tip"] >= ALERT_TIP_P99
        status = "🔴 MEV 抢跑潮" if extreme else ("🟡 MEV 活跃" if hot else "🟢 平静")

        # 落盘
        try:
            new = not LOG_PATH.exists()
            with open(LOG_PATH, "a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["ts", "n_bundles", "n_with_tip", "n_txs", "p50_tip", "p99_tip", "max_tip", "mean_tip", "std_tip"])
                w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), s["n_bundles"],
                            s["n_with_tip"], s["n_txs"], s["p50_tip"], s["p99_tip"], s["max_tip"],
                            round(s["mean_tip"], 1), round(s["std_tip"], 1)])
        except Exception:
            pass

        if args.watchdog:
            if extreme or hot:
                print(f"⚠️ Jito {status} @ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC："
                      f"P99 tip {s['p99_tip']/1e9:.6f} SOL / {s['n_bundles']} bundles")
            return 0

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n=== Jito Bundle 监控 @ {ts} ===")
        print(f"状态: {status}")
        print(f"待处理 bundle: {s['n_bundles']} | 带 tip: {s['n_with_tip']} | 含交易: {s['n_txs']}")
        print(f"\n{'指标':<22}{'值':>14}")
        print(f"{'P50 tip (lamports)':<22}{s['p50_tip']:>14,.0f}")
        print(f"{'P99 tip (lamports)':<22}{s['p99_tip']:>14,.0f}")
        print(f"{'max tip (lamports)':<22}{s['max_tip']:>14,.0f}")
        print(f"{'均值 tip (lamports)':<22}{s['mean_tip']:>14,.0f}")
        print(f"{'标准差':<22}{s['std_tip']:>14,.0f}")
        print(f"\n解读: tip 是 MEV 竞争强度直接指标（1 SOL = 1e9 lamports）")
        print(f"      P99 >= {WARN_TIP_P99/1e9:.3f} SOL = MEV 活跃；>= {ALERT_TIP_P99/1e9:.3f} SOL = 抢跑潮")
        print(f"      与 priority_fee_monitor 对照 = 普通通道 vs bundle 通道竞争全景")
        return 0

    code = tick()
    if args.watch and not args.watchdog:
        while True:
            time.sleep(args.watch)
            tick()
    return code


if __name__ == "__main__":
    sys.exit(main())
