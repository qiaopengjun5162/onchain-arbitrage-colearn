#!/usr/bin/env python3
"""Execution Quality Tracker：模拟 vs 实际成交达成率（只读框架）。

对应 notes/solana/README.md 研究线四阶段「execution quality tracker」：
- roadmap 核心问题：「Paper Trading 里哪些收益会在实盘中消失？」
- 达成率 = 实际成交价 / 模拟报价（1.0 = 完美执行，<1.0 = 滑点/竞争损耗）
- 这是连接「模拟验证」与「实盘执行」的最后一环

框架（四步）：
1. quote：Jupiter 报价（模拟期望价）
2. build：solana-rs swap 构造交易（dry-run 签名成功 = 可执行性）
3. execute：--send 广播（真实成交）
4. compare：实际成交价 vs 模拟报价 → 达成率 → 落 CSV

当前：quote + dry-run 自动化；--send 需真实 SOL（用户决定），达成率记录结构就绪。

用法：
    python scripts/execution_quality_tracker.py --amount 0.01         # quote + dry-run 记录
    python scripts/execution_quality_tracker.py --amount 0.01 --send  # 真实广播（需钱包 SOL）

依赖：hermes venv python3.11（requests）+ solana-rs cargo build
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 20
QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "execution_quality.csv"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# 门槛公式参数（132 笔记 + Bruce 期望利润公式完整版）：
#   expectedSurplus > successGas + 失败摊派(每次成功) + 资金机会成本 + 缓冲
# 数据来源：125 笔记（Jito bundle P99 tip 0.002 SOL）；888BMM 实测失败率 78.5%（068）
SUCCESS_GAS_SOL = 0.002          # 成功单笔：Jito tip P99 + 基础费（Solana 套利语境）
FAIL_RATE = 0.4                  # 失败概率（可调；888BMM 实测 0.785，普通 swap 更低）
FAIL_GAS_SOL = 0.00001           # 失败单笔烧的 gas（低于成功 tip）
OPPORTUNITY_COST_USDC = 0.0      # 资金机会成本（默认 0，实盘可传 --opp-cost）
BUFFER = 0.2                     # 20% 缓冲（笔记008 同款）


def gate_decision(surplus_usdc, sim_price):
    """132+Bruce 门槛公式：expectedSurplus > successGas + 失败摊派 + 机会成本 + 缓冲。

    返回 (decision, threshold_usdc, breakdown)。
    """
    success_gas = SUCCESS_GAS_SOL * sim_price                       # USD
    fail_alloc = FAIL_GAS_SOL * sim_price * FAIL_RATE / (1 - FAIL_RATE)  # 每次成功摊派的失败 Gas
    threshold = (success_gas + fail_alloc + OPPORTUNITY_COST_USDC) * (1 + BUFFER)
    if surplus_usdc > threshold:
        decision = "GO"
    elif surplus_usdc > threshold * 0.5:
        decision = "WATCH"
    else:
        decision = "NO-GO"
    breakdown = {"success_gas": round(success_gas, 4), "fail_alloc": round(fail_alloc, 4),
                 "opp_cost": OPPORTUNITY_COST_USDC, "buffer": BUFFER}
    return decision, round(threshold, 4), breakdown


def quote_price(amount_sol: float) -> dict:
    """模拟报价：SOL → USDC。返回期望价 + 路由。"""
    amount = int(amount_sol * 1e9)
    params = {"inputMint": SOL_MINT, "outputMint": USDC_MINT, "amount": amount, "slippageBps": 100}
    r = requests.get(QUOTE_URL, params=params, timeout=TIMEOUT, proxies=PROXIES)
    r.raise_for_status()
    q = r.json()
    out_usdc = int(q["outAmount"]) / 1e6
    route = "→".join(p.get("swapInfo", {}).get("label", "?") for p in q.get("routePlan", []))
    return {"sim_price": out_usdc / amount_sol, "out_usdc": out_usdc, "route": route,
            "sim_ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def dry_run_swap(amount_sol: float) -> dict:
    """solana-rs swap dry-run：验证交易可构造（不广播）。"""
    bin_path = Path(__file__).resolve().parent.parent / "scripts" / "solana-rs" / "target" / "debug" / "solana-rs"
    if not bin_path.exists():
        return {"dry_run": False, "error": "solana-rs 未编译（cargo build 一次）"}
    r = subprocess.run([str(bin_path), "swap", "--amount", str(amount_sol)],
                       capture_output=True, text=True, timeout=60)
    ok = "dry-run" in r.stdout and "已签名" in r.stdout
    return {"dry_run": ok, "build_ok": ok, "output_tail": r.stdout[-120:].replace("\n", " | ")}


def main():
    global OPPORTUNITY_COST_USDC
    ap = argparse.ArgumentParser()
    ap.add_argument("--amount", type=float, default=0.01, help="SOL 数量（默认 0.01 极小）")
    ap.add_argument("--send", action="store_true", help="真实广播（需钱包 SOL）")
    ap.add_argument("--surplus", type=float, default=0.0,
                    help="候选机会的期望毛利润 USDC（132 门槛公式判据；0 = 纯 swap 测量模式）")
    ap.add_argument("--opp-cost", type=float, default=OPPORTUNITY_COST_USDC,
                    help="资金机会成本 USDC（Bruce 公式：资金占用成本）")
    args = ap.parse_args()
    OPPORTUNITY_COST_USDC = args.opp_cost

    # 1. 模拟报价
    sim = quote_price(args.amount)
    print(f"=== Execution Quality @ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC ===")
    print(f"模拟报价: {args.amount} SOL → {sim['out_usdc']:.4f} USDC（均价 {sim['sim_price']:.4f}）")
    print(f"路由: {sim['route']}")

    # 2. dry-run 构造
    dry = dry_run_swap(args.amount)
    print(f"交易构造: {'✅ 可执行（dry-run 签名成功）' if dry.get('dry_run') else '❌ ' + dry.get('error', '失败')}")

    # 2.5 门槛公式（132 + Bruce 完整版）
    decision, threshold, bd = gate_decision(args.surplus, sim["sim_price"])
    print(f"\n候选评估（门槛公式）：期望毛利润 ${args.surplus:,.2f}")
    print(f"  门槛 = ${threshold:,.2f}（成功Gas ${bd['success_gas']:.4f} + 失败摊派 ${bd['fail_alloc']:.4f} "
          f"+ 机会成本 ${bd['opp_cost']:.2f}）× {1 + bd['buffer']:.1f} 缓冲")
    print(f"  决策：{'✅ GO（期望利润过门槛）' if decision == 'GO' else '👁 WATCH（介于 0.5-1× 门槛）' if decision == 'WATCH' else '❌ NO-GO（期望利润 < 0.5× 门槛）'}")

    # 3. 真实执行（可选）
    exec_price = None
    if args.send:
        # TODO: 实际广播后从链上拿成交价（getTransaction 解析）
        print("⚠️ --send 需要真实广播 + 链上成交价解析（待接入）")
    else:
        print("（dry-run 模式：未广播，成交价无）")

    # 4. 落盘（达成率结构就绪，--send 后填实际值）
    new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "amount_sol", "sim_price", "sim_route", "build_ok", "exec_price", "fill_rate",
                        "surplus_usdc", "threshold_usdc", "decision"])
        w.writerow([sim["sim_ts"], args.amount, round(sim["sim_price"], 6), sim["route"],
                    dry.get("dry_run", False), exec_price if exec_price else "", "",
                    args.surplus, threshold, decision])
    print(f"\n已记录 → {LOG_PATH}")
    print("达成率 = exec_price / sim_price（实盘后回填；=1 完美，<1 有滑点/竞争损耗）")


if __name__ == "__main__":
    sys.exit(main())
