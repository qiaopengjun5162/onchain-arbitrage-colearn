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
    ap = argparse.ArgumentParser()
    ap.add_argument("--amount", type=float, default=0.01, help="SOL 数量（默认 0.01 极小）")
    ap.add_argument("--send", action="store_true", help="真实广播（需钱包 SOL）")
    args = ap.parse_args()

    # 1. 模拟报价
    sim = quote_price(args.amount)
    print(f"=== Execution Quality @ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC ===")
    print(f"模拟报价: {args.amount} SOL → {sim['out_usdc']:.4f} USDC（均价 {sim['sim_price']:.4f}）")
    print(f"路由: {sim['route']}")

    # 2. dry-run 构造
    dry = dry_run_swap(args.amount)
    print(f"交易构造: {'✅ 可执行（dry-run 签名成功）' if dry.get('dry_run') else '❌ ' + dry.get('error', '失败')}")

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
            w.writerow(["ts", "amount_sol", "sim_price", "sim_route", "build_ok", "exec_price", "fill_rate"])
        w.writerow([sim["sim_ts"], args.amount, round(sim["sim_price"], 6), sim["route"],
                    dry.get("dry_run", False), exec_price if exec_price else "", ""])
    print(f"\n已记录 → {LOG_PATH}")
    print("达成率 = exec_price / sim_price（实盘后回填；=1 完美，<1 有滑点/竞争损耗）")


if __name__ == "__main__":
    sys.exit(main())
