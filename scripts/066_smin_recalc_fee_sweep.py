#!/usr/bin/env python3
"""066 复算 · 补充：按真实池费率的 Solana 版 s_min。

原公式 6/997 假设两腿都是 0.3% 池费（EVM Uniswap v2 默认）。
Solana 各池费率不同（Raydium 25bps / Orca 30bps / Phoenix 0 / PumpSwap 25bps...），
复算时手续费项应换成 2 × 实际费率。

s_min(rate_bps) = 2·rate/10000 + 2√(Gas_total / R_eff)

用 066 复算脚本 B 场景的实测输入（Gas_total=$0.000761, R_eff=$2,597,141）。
"""

import math

SOL_USD = 76.07
GAS_LAMPORTS = 10_000          # 2 签名 × 5000 基础费 + priority 0（实测）
GAS_USD = GAS_LAMPORTS * 1e-9 * SOL_USD
R_EFF = 2_597_141               # Raydium vault 实测 R/2（2026-08-10 23:0x UTC）

print(f"Gas_total=${GAS_USD:.6f}  R_eff=${R_EFF:,}")
print(f"{'池':<14}{'费率/腿':>8}{'手续费项':>10}{'gas 项':>10}{'s_min':>10}")
print("-" * 56)
for name, bps in [("EVM v2(066 原)", 30), ("Raydium", 25), ("Orca", 30),
                  ("Phoenix", 0), ("PumpSwap", 25), ("Meteora DLMM", 25)]:
    fee = 2 * bps / 10000 * 100
    gas = 2 * math.sqrt(GAS_USD / R_EFF) * 100
    s = fee + gas
    print(f"{name:<14}{bps:>6}bps{fee:>9.4f}%{gas:>9.4f}%{s:>9.4f}%")

print()
print("解读：Solana 上 gas 项 <0.005%，门槛几乎=2×池费率。")
print("     费率最低的池（Phoenix 0bps）s_min≈0.0035%，但那是订单簿非 AMM；")
print("     Raydium/Orca 25-30bps → s_min≈0.50-0.61%，与 EVM 同量级，")
print("     差别在 gas 不再是变量（Solana 当前竞争≈0）——门槛=费率地板。")
