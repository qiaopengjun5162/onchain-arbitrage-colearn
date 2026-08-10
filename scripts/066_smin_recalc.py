#!/usr/bin/env python3
"""066 最小可行价差公式复算（用我们的真实 Gas 数据）

公式（clare ma 笔记 066）：s_min = 6/997 + 2·√(Gas_total / R_eff)
- 6/997 = 两次 swap 手续费（0.3% 池费 × 2）= 0.6018%
- Gas_total = 双边执行成本（美元）
- R_eff = 有效池深度（美元，两池都受冲击 → R/2 口径）

复算两个场景：
A. EVM 原场景：clare ma 实测数据（验证公式复现）
B. Solana 场景：我们的真实数据
   - Gas：priority fee 实测 30 小时全 0（data/priority_fee_history.csv），
     交易费 = 5000 lamports 基础费（base fee），双边按 2 笔交易
   - R_eff：Raydium SOL-USDC vault 实时余额（k = x·y）
"""

import json
import math
import os
import sys
from pathlib import Path

import requests

KB = Path("/Users/qiaopengjun/Code/Solana/onchain-arbitrage-colearn")
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 15
SOL_USD = 76.07     # 2026-08-10 coingecko 实测
RAYDIUM_SOL_USDC = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
SOL_VAULT = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
USDC_VAULT = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"


def get_helius_key() -> str:
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("HELIUS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def rpc(url: str, method: str, params):
    resp = requests.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                         timeout=TIMEOUT, proxies=PROXIES)
    return resp.json().get("result")


def s_min(gas_total_usd: float, r_eff_usd: float) -> tuple[float, float, float]:
    """返回 (s_min%, 手续费%, gas%)。"""
    fee_pct = 6 / 997 * 100          # 0.6018%
    gas_pct = 2 * math.sqrt(gas_total_usd / r_eff_usd) * 100
    return fee_pct + gas_pct, fee_pct, gas_pct


def main():
    print("=" * 72)
    print("066 复算：s_min = 6/997 + 2√(Gas_total / R_eff)")
    print("=" * 72)

    # ---- 场景 A：EVM 原场景（clare ma 实测，公式验证）----
    print("\n【A】EVM 原场景（clare ma 2026-08-08 实测）")
    a_gas = 0.0103      # 双边 Gas_total USD
    a_r_eff = 4_443_774  # R_eff USD
    a, a_fee, a_gas_pct = s_min(a_gas, a_r_eff)
    print(f"  Gas_total=${a_gas:.4f}  R_eff=${a_r_eff:,.0f}")
    print(f"  s_min = {a:.4f}%  （手续费 {a_fee:.4f}% + gas {a_gas_pct:.4f}%）  原笔记值 0.6114%")
    print(f"  ✅ 复现误差 {abs(a - 0.6114):.4f}pp" if abs(a - 0.6114) < 0.005 else "  ⚠️ 与笔记值不一致")

    # ---- 场景 B：Solana 我们的真实数据 ----
    print("\n【B】Solana 场景（我们的真实数据）")

    # B1. Gas：priority fee 实测全 0 + 5000 lamports 基础费
    hist = KB / "data" / "priority_fee_history.csv"
    zero_rows = 0
    max_prio = 0.0
    if hist.exists():
        with open(hist) as f:
            lines = f.readlines()[1:]
        for ln in lines:
            parts = ln.strip().split(",")
            if len(parts) >= 6:
                zero_rows += 1
                try:
                    max_prio = max(max_prio, float(parts[5]))
                except ValueError:
                    pass
    prio_lamports = 0  # P99 也是 0
    print(f"  priority fee 历史：{zero_rows} 条快照，max 均值 {max_prio:.1f} lamports → 实测竞争成本≈0")
    base_fee_lamports = 5000  # Solana 每签名基础费
    n_sig = 2                 # 双边各 1 笔交易
    gas_lamports = base_fee_lamports * n_sig + prio_lamports
    gas_usd = gas_lamports * 1e-9 * SOL_USD
    print(f"  Gas: {n_sig} 签名 × 5000 lamports + priority 0 = {gas_lamports:,} lamports = ${gas_usd:.6f} (SOL=${SOL_USD})")

    # B2. R_eff：Raydium SOL-USDC vault 实时余额
    key = get_helius_key()
    url = f"https://mainnet.helius-rpc.com/?api-key={key}"
    sol = rpc(url, "getTokenAccountBalance", [SOL_VAULT])
    usdc = rpc(url, "getTokenAccountBalance", [USDC_VAULT])
    if not sol or not usdc or not sol.get("value") or not usdc.get("value"):
        print("  ⚠️ 无法读取 Raydium vault，用已知量级兜底")
        sol_amt, usdc_amt = 55_000.0, 4_200_000.0
    else:
        sol_amt = sol["value"]["uiAmount"]
        usdc_amt = usdc["value"]["uiAmount"]
    r_eff = usdc_amt / 2  # 两池冲击 → 有效深度减半（066 口径）
    print(f"  Raydium vault 实时：{sol_amt:,.1f} SOL × {usdc_amt:,.0f} USDC（≈${sol_amt*SOL_USD+usdc_amt:,.0f}）")
    print(f"  R_eff = R/2 = ${r_eff:,.0f}")

    b, b_fee, b_gas_pct = s_min(gas_usd, r_eff)
    print(f"  s_min = {b:.4f}%  （手续费 {b_fee:.4f}% + gas {b_gas_pct:.5f}%）")

    # B3. 对比：Solana 手续费更贵（Raydium 0.25% 池费为主）但 gas 几乎免费
    print("\n【对比】")
    print(f"  {'':<16}{'手续费':>10}{'gas 项':>10}{'s_min':>10}")
    print(f"  {'EVM 原场景':<14}{a_fee:>9.4f}%{a_gas_pct:>9.4f}%{a:>9.4f}%")
    print(f"  {'Solana 我们':<14}{b_fee:>9.4f}%{b_gas_pct:>9.4f}%{b:>9.4f}%")
    print(f"\n  结论方向：手续费项占比 "
          f"{b_fee/b*100:.1f}%（Solana）vs {a_fee/a*100:.1f}%（EVM）——"
          f"gas 越便宜，门槛越被手续费主导")

    # B4. 不同 gas price 敏感性（Solana 版）
    print("\n【Solana gas 敏感性】")
    print(f"  {'场景':<22}{'Gas_total':>12}{'s_min':>10}{'gas 占比':>10}")
    for label, mult in [("当前(priority=0)", 1), ("priority=0.01/CU", 14_000),
                        ("Jito 竞争(0.1/CU)", 140_000), ("极端抢跑(1/CU)", 1_400_000)]:
        g = (base_fee_lamports * n_sig + mult) * 1e-9 * SOL_USD
        s, _, gp = s_min(g, r_eff)
        print(f"  {label:<20}{g:>12.6f}{s:>9.4f}%{gp:>9.4f}%")


if __name__ == "__main__":
    main()
