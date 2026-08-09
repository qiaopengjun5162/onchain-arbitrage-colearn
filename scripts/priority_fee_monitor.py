#!/usr/bin/env python3
"""Priority fee / CU 监控哨兵：Solana 执行质量数据（只读）。

对应 notes/solana/README.md 研究线二阶段「数据：priority fee / 失败交易」：
- getRecentPrioritizationFees：最近 N 区块的 priority fee 分布（P50/P99.9，沿用 infra 方法论拒 Mean）
- 高 priority fee = 竞争激烈信号（Jito bundle / 套利机器人抢跑）
- 同区块内 priority fee 离散度 = 竞价乱象指标

用法：
    python scripts/priority_fee_monitor.py            # 单次
    python scripts/priority_fee_monitor.py --watch 3600
    python scripts/priority_fee_monitor.py --watchdog # cron：静默，只有 fee 异常才报

退出码：0 = 正常；1 = 异常（cron watchdog 用）

依赖：hermes venv python3.11；HELIUS_API_KEY 从 ~/.hermes/.env 读（export 前缀需 strip）
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
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "priority_fee_history.csv"

# 阈值（lamports/compute-unit，Solana 常规 <0.001；剧烈行情 >0.01）
WARN_FEE_P99 = 0.01     # P99.9 >= 0.01 lamports/CU 黄色警告（竞争激烈）
ALERT_FEE_P99 = 0.05    # P99.9 >= 0.05 红色（极端竞争/抢跑潮）
RECENT_SLOTS = 20       # 采样最近 N 个区块


def load_helius_key() -> str:
    """从 ~/.hermes/.env 读 HELIUS_API_KEY（处理 export 前缀）。"""
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return os.environ.get("HELIUS_API_KEY", "")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("HELIUS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("HELIUS_API_KEY", "")


def rpc_call(url: str, method: str, params=None) -> dict:
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    r = requests.post(url, json=body, timeout=TIMEOUT, proxies=PROXIES)
    r.raise_for_status()
    return r.json()


def collect(url: str, slots: int = RECENT_SLOTS) -> dict:
    """拉最近 N 个区块的 priority fee + 观察 CU 消耗。"""
    # 1. getRecentPrioritizationFees（无参数 = 最近 20 个区块）
    fees = rpc_call(url, "getRecentPrioritizationFees")
    result = fees.get("result", [])
    if not result:
        return {"error": "空结果"}

    per_slot = {}  # slot -> [fees]
    for item in result:
        slot = item.get("slot")
        fee = item.get("prioritizationFee", 0)  # lamports（绝对额）
        # 转 lamports/CU：用 1.4M CU 近似（实际因交易而异；绝对值也能看趋势）
        per_slot.setdefault(slot, []).append(fee)

    # 每 slot 取 max（该区块竞价上限）
    slot_max = [max(v) for v in per_slot.values()]
    all_fees = [f for v in per_slot.values() for f in v]

    def pct(lst, p):
        if not lst:
            return 0.0
        lst = sorted(lst)
        idx = min(len(lst) - 1, int(len(lst) * p))
        return lst[idx]

    stats = {
        "n_slots": len(per_slot),
        "n_fees": len(all_fees),
        "p50_lamports": pct(all_fees, 0.5),
        "p99_lamports": pct(all_fees, 0.99),
        "max_lamports": max(all_fees) if all_fees else 0,
        "slot_p50_lamports": pct(slot_max, 0.5),
        "slot_p99_lamports": pct(slot_max, 0.99),
        "mean_lamports": statistics.mean(all_fees) if all_fees else 0,
        "std_lamports": statistics.stdev(all_fees) if len(all_fees) > 1 else 0,
    }
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--watchdog", action="store_true", help="cron：静默，仅异常才报")
    ap.add_argument("--slots", type=int, default=RECENT_SLOTS)
    args = ap.parse_args()

    key = load_helius_key()
    if not key:
        print("ERROR: 未找到 HELIUS_API_KEY", file=sys.stderr)
        return 1
    url = f"https://mainnet.helius-rpc.com/?api-key={key}"

    def tick():
        try:
            s = collect(url, args.slots)
        except Exception as e:
            if not args.watchdog:
                print(f"[err] {e}")
            return 1
        if "error" in s:
            if not args.watchdog:
                print(f"[err] {s['error']}")
            return 1

        # 判定（用 lamports 绝对值，1.4M CU 满预算参考：0.01 lamports/CU ≈ 14K lamports 竞价）
        hot = s["slot_p99_lamports"] >= WARN_FEE_P99 * 1_400_000
        extreme = s["slot_p99_lamports"] >= ALERT_FEE_P99 * 1_400_000
        status = "🔴 极端竞争" if extreme else ("🟡 竞争激烈" if hot else "🟢 正常")

        # 落盘历史（趋势对比用，与 funding_basis_history 同模式）
        try:
            new = not LOG_PATH.exists()
            with open(LOG_PATH, "a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["ts", "n_slots", "p50_lamports", "p99_lamports", "mean_lamports", "std_lamports", "slot_p99_lamports", "max_lamports"])
                w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), s["n_slots"],
                            s["p50_lamports"], s["p99_lamports"], round(s["mean_lamports"], 1), round(s["std_lamports"], 1),
                            s["slot_p99_lamports"], s["max_lamports"]])
            # 读历史算分位（≥20 条才有效，沿用 basis 分位规则）
            hist_p99 = []
            if LOG_PATH.exists():
                with open(LOG_PATH) as f:
                    rows = list(csv.reader(f))[1:]
                hist_p99 = [float(r[6]) for r in rows if len(r) > 6 and r[6]]
            s["hist_n"] = len(hist_p99)
            if len(hist_p99) >= 20:
                sorted_p99 = sorted(hist_p99)
                cur = s["slot_p99_lamports"]
                s["cur_pctile"] = round(sum(1 for x in sorted_p99 if x <= cur) / len(sorted_p99), 2)
            else:
                s["cur_pctile"] = None
        except Exception:
            s["hist_n"] = 0
            s["cur_pctile"] = None

        if args.watchdog:
            if extreme or hot:
                print(f"⚠️ Solana priority fee {status} @ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC："
                      f"P99 {s['slot_p99_lamports']:,.0f} lamports / 区块竞价上限 {s['max_lamports']:,.0f}")
            return 0

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n=== Priority Fee 监控 @ {ts} ===")
        print(f"状态: {status}")
        print(f"采样: {s['n_slots']} 区块 / {s['n_fees']} 笔 fee")
        print(f"\n{'指标':<24}{'值':>16}")
        print(f"{'P50 (lamports)':<24}{s['p50_lamports']:>16,.0f}")
        print(f"{'P99 (lamports)':<24}{s['p99_lamports']:>16,.0f}")
        print(f"{'均值 (lamports)':<24}{s['mean_lamports']:>16,.0f}")
        print(f"{'标准差 (lamports)':<24}{s['std_lamports']:>16,.0f}")
        print(f"{'区块竞价 P50':<24}{s['slot_p50_lamports']:>16,.0f}")
        print(f"{'区块竞价 P99':<24}{s['slot_p99_lamports']:>16,.0f}")
        print(f"{'区块竞价 max':<24}{s['max_lamports']:>16,.0f}")
        pctile_str = f"{s['cur_pctile']:.0%}" if s.get("cur_pctile") is not None else "-"
        print(f"{'历史 P99 分位':<24}{pctile_str:>16}（{s['hist_n']} 条快照）")
        print("\n解读: P50 是常态成本，P99 是极端行情下的确定性（沿用拒 Mean 方法论）")
        print("      高 P99 + 高标准差 = 竞价乱象/抢跑潮，套利执行成本上升")
        print("      历史分位 ≥0.8 = 当前竞价处高位（与 funding basis 分位同规则）")
        return 0

    code = tick()
    if args.watch and not args.watchdog:
        while True:
            time.sleep(args.watch)
            tick()
    return code


if __name__ == "__main__":
    sys.exit(main())
