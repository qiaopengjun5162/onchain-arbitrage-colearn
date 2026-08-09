#!/usr/bin/env python3
"""Solana DEX 真实滑点验证 v0（Day 5 主线，只读）。

目标：回答「17-20bps 池间价差在真实执行后还剩多少？」
方法（假滑点 → 真实滑点）：
1. 假滑点：Raydium 直读 vault → 恒定乘积模拟（理想化，无路由拆分）
2. 真实滑点：Jupiter quote 的 priceImpactPercent + 各金额实际成交价（含路由拆分/费用）
3. 可执行价差 = Jupiter 实际成交价 vs Raydium 中间价（bps）——这才是能吃到的
4. 关键输出：滑点曲线 + 临界金额（价差被滑点吃光的点）

用法：
  python solana_dex_slippage_verify.py --once
  python solana_dex_slippage_verify.py --watch 60

依赖：hermes venv python3.11 + requests；HELIUS_API_KEY 从 ~/.hermes/.env 读
关联：notes/node-infra-acceptance-checklist-20260808.md（验收）、D4 的 solana_dex_spread_monitor.py
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"https": PROXY}


def get_helius_key() -> str:
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("HELIUS_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return ""


HELIUS_KEY = get_helius_key()
RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}"

RAYDIUM_SOL_USDC = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
SOL_VAULT = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
USDC_VAULT = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"

JUPITER_QUOTE = "https://api.jup.ag/swap/v1/quote"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# 采样金额阶梯（SOL）：覆盖小单到深池冲击
SAMPLES_SOL = [0.1, 1, 10, 50, 100, 250, 500]
RAYDIUM_FEE = 0.003  # 0.3%


def rpc(method, params):
    if not HELIUS_KEY:
        return None
    resp = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                         timeout=15, proxies=PROXIES if os.environ.get("NO_PROXY") != "1" else None)
    return resp.json().get("result")


def read_raydium() -> dict:
    """直读 Raydium SOL-USDC：中间价 + 恒定乘积滑点曲线。"""
    if not HELIUS_KEY:
        return {}
    sol = rpc("getTokenAccountBalance", [SOL_VAULT])
    usdc = rpc("getTokenAccountBalance", [USDC_VAULT])
    if not sol or not usdc or not sol.get("value") or not usdc.get("value"):
        return {}
    sol_amt = sol["value"]["uiAmount"]
    usdc_amt = usdc["value"]["uiAmount"]
    if not sol_amt or not usdc_amt:
        return {}
    mid = usdc_amt / sol_amt
    k = sol_amt * usdc_amt
    # 恒定乘积模拟两条腿（假滑点基准）：
    # 卖 SOL 腿：投入 amt SOL → 换回 USDC（与 Jupiter 同方向对比）
    # 买 SOL 腿：投入 amt USDC → 换回 SOL（完整环的买腿成本）
    curve = []
    for amt in SAMPLES_SOL:
        new_sol = sol_amt + amt
        new_usdc = k / new_sol
        gross = usdc_amt - new_usdc
        out_usdc = gross * (1 - RAYDIUM_FEE)
        exec_price = out_usdc / amt
        slip_bps = (mid - exec_price) / mid * 10000  # 相对中间价的滑点（正=变贵）
        # 买 SOL 腿：投入等值 USDC（amt * mid）→ 换回 SOL
        buy_usdc_in = amt * mid
        new_usdc_b = usdc_amt + buy_usdc_in
        new_sol_b = k / new_usdc_b
        sol_out = (sol_amt - new_sol_b) * (1 - RAYDIUM_FEE)
        buy_cost_price = buy_usdc_in / sol_out if sol_out else 0  # USDC/SOL 实际买价
        curve.append({"amount_sol": amt, "out_usdc": out_usdc, "exec_price": exec_price,
                      "slippage_bps": round(slip_bps, 1), "buy_cost_price": buy_cost_price})
    return {"mid_price": mid, "pool_sol": sol_amt, "pool_usdc": usdc_amt, "curve": curve}


def jupiter_quotes() -> list:
    """Jupiter 各金额真实报价：实际成交价（真实滑点，路由分散后远小于单池模拟）。"""
    rows = []
    for amt in SAMPLES_SOL:
        try:
            params = {"inputMint": SOL_MINT, "outputMint": USDC_MINT,
                      "amount": int(amt * 1e9), "slippageBps": 300}
            resp = requests.get(JUPITER_QUOTE, params=params, timeout=15,
                                proxies=PROXIES if os.environ.get("NO_PROXY") != "1" else None)
            d = resp.json()
            if "outAmount" not in d:
                continue
            out = int(d["outAmount"]) / 1e6
            exec_price = out / amt
            impact_pct = d.get("priceImpactPct")
            impact_bps = round(float(impact_pct) * 100, 1) if impact_pct else None
            labels = [s.get("swapInfo", {}).get("label", "?") for s in d.get("routePlan", [])]
            rows.append({
                "amount_sol": amt, "out_usdc": round(out, 2), "exec_price": exec_price,
                "impact_bps": impact_bps,
                "route": "+".join(labels) if labels else "?",
            })
        except Exception as e:
            rows.append({"amount_sol": amt, "error": str(e)[:60]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", type=int, default=0)
    args = ap.parse_args()

    if not HELIUS_KEY:
        print("ERROR: 未找到 HELIUS_API_KEY", file=sys.stderr)
        return 1

    def tick():
        raydium = read_raydium()
        jup = jupiter_quotes()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n=== 真实滑点验证 @ {ts} ===")
        if not raydium:
            print("Raydium 直读失败")
            return
        print(f"Raydium 池: {raydium['pool_sol']:.1f} SOL / {raydium['pool_usdc']:,.0f} USDC")
        print(f"中间价: {raydium['mid_price']:.4f} USDC/SOL\n")
        print(f"{'金额SOL':>8}{'Jup卖价':>11}{'Ray买成本':>11}{'池价差bps':>10}{'环净收益bps':>12}{'路由':>28}")
        for r in jup:
            if "error" in r:
                print(f"{r['amount_sol']:>8}  ERROR {r['error']}")
                continue
            # 完整环：USDC → Raydium 买 SOL（含 fee+滑点）→ Jupiter 卖 SOL（含真实路由）
            c = next((x for x in raydium["curve"] if x["amount_sol"] == r["amount_sol"]), None)
            if not c:
                continue
            ray_buy_cost = c["buy_cost_price"]  # 在 Raydium 买 1 SOL 的实际成本（USDC/SOL）
            jup_sell_price = r["exec_price"]    # 在 Jupiter 卖 1 SOL 的实际收入（USDC/SOL）
            # 毛价差：Jupiter 卖价 vs Raydium 中间价
            gross_bps = (jup_sell_price - raydium["mid_price"]) / raydium["mid_price"] * 10000
            # 环净收益：卖出收入 - 买入成本（含两腿 fee + 滑点），这才是真实可赚
            net_bps = (jup_sell_price - ray_buy_cost) / ray_buy_cost * 10000
            print(f"{r['amount_sol']:>8}{jup_sell_price:>11.4f}{ray_buy_cost:>11.4f}{gross_bps:>10.1f}"
                  f"{net_bps:>12.1f}{r['route'][:26]:>28}")
        print("\n解读：环净收益 >0 = USDC→Raydium买SOL→Jupiter卖SOL 扣两腿成本后真实可赚")

    tick()
    if args.watch and not args.once:
        while True:
            time.sleep(args.watch)
            tick()


if __name__ == "__main__":
    sys.exit(main())
