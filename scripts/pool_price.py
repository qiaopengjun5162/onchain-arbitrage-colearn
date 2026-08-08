#!/usr/bin/env python3
"""链上池子价格 — Helius RPC 查 SOL-USDC Raydium 池子储备

安全：Helius key 从环境变量读取（HELIUS_API_KEY），不硬编码。
用法：HELIUS_API_KEY=xxx python pool_price.py
"""
import os
import requests, json

HELIUS_KEY = os.environ.get("HELIUS_API_KEY", "")
if not HELIUS_KEY:
    raise SystemExit("ERROR: 请设置 HELIUS_API_KEY 环境变量（export HELIUS_API_KEY=...）")
RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}"

def rpc(method, params):
    resp = requests.post(RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params})
    return resp.json()["result"]

RAYDIUM_SOL_USDC = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
SOL_VAULT = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
USDC_VAULT = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"

print("=" * 55)
print("  SOL-USDC Raydium 池子链上数据")
print("=" * 55)

sol = rpc("getTokenAccountBalance", [SOL_VAULT])
usdc = rpc("getTokenAccountBalance", [USDC_VAULT])

sol_amt = sol["value"]["uiAmount"]
usdc_amt = usdc["value"]["uiAmount"]
price = usdc_amt / sol_amt

print(f"\n  SOL Vault:  {sol_amt:,.2f} SOL")
print(f"  USDC Vault: {usdc_amt:,.2f} USDC")
print(f"\n  💰 价格: 1 SOL = ${price:.4f}")

# 恒定乘积模拟 1 SOL swap
k = sol_amt * usdc_amt
fee = 0.997
new_sol = sol_amt + 1
new_usdc = k / new_sol
out = (usdc_amt - new_usdc) * fee

print(f"\n  🧪 模拟 swap 1 SOL:")
print(f"     输出: {out:.4f} USDC")
print(f"     价格: 1 SOL = ${out:.4f}")
print(f"     滑点: {((out - price) / price * 100):.4f}%")
print("=" * 55)
