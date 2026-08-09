#!/usr/bin/env python3
"""
Jupiter Quote API — 第一个 Solana 链上数据脚本
功能：拉取 SOL-USDC 实时报价，输出价格、滑点、路由信息
"""
import os
import requests
import json

# 代理配置：本地 Clash/V2Ray 代理
PROXY = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")

# Jupiter Swap API v1（Metis 路由引擎；quote-api.jup.ag v6 已于 2025-10-01 弃用）
JUPITER_QUOTE_URL = "https://api.jup.ag/swap/v1/quote"

# Token mints on Solana mainnet
SOL_MINT = "So11111111111111111111111111111111111111112"   # Wrapped SOL
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

def get_quote(input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50):
    """
    调用 Jupiter Quote API 获取报价
    
    Args:
        input_mint: 输入 token 的 mint 地址
        output_mint: 输出 token 的 mint 地址
        amount: 输入数量（lamports，1 SOL = 1_000_000_000 lamports）
        slippage_bps: 滑点容忍度（basis points，50 = 0.5%）
    """
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "slippageBps": slippage_bps,
    }
    
    resp = requests.get(JUPITER_QUOTE_URL, params=params, proxies={"https": PROXY})
    resp.raise_for_status()
    return resp.json()


def format_amount(lamports: int, decimals: int = 9) -> str:
    """lamports → 人类可读"""
    return f"{lamports / 10**decimals:,.6f}"


def main():
    amounts_sol = [
        100_000_000,      # 0.1 SOL
        1_000_000_000,    # 1 SOL
        10_000_000_000,   # 10 SOL
    ]
    
    print("=" * 60)
    print("  Jupiter Quote: SOL → USDC")
    print("=" * 60)
    
    for amount_lamports in amounts_sol:
        try:
            quote = get_quote(SOL_MINT, USDC_MINT, amount_lamports)
            
            sol_amount = format_amount(int(quote["inAmount"]))
            usdc_amount = int(quote["outAmount"]) / 1_000_000  # USDC 6 decimals
            
            # 隐含价格
            price = usdc_amount / (int(quote["inAmount"]) / 1_000_000_000)
            
            # 路由信息
            route_plan = quote.get("routePlan", [])
            hops = " → ".join(
                f"{p['swapInfo']['label']}" for p in route_plan
            )
            
            print(f"\n  📥 输入:  {sol_amount} SOL")
            print(f"  📤 输出:  {usdc_amount:,.6f} USDC")
            print(f"  💰 价格:  1 SOL = ${price:.4f}")
            print(f"  📊 滑点:  {quote.get('slippageBps', 'N/A')} bps")
            print(f"  🛣️  路由:  {hops}")
            
            # 额外信息
            other_amount_threshold = quote.get("otherAmountThreshold", "0")
            if other_amount_threshold:
                min_received = int(other_amount_threshold) / 1_000_000
                print(f"  ⚠️  最少收到: {min_received:,.6f} USDC (含滑点)")
            
        except Exception as e:
            print(f"\n  ❌ {format_amount(amount_lamports)} SOL: {e}")
    
    print("\n" + "=" * 60)
    
    # 反向报价：USDC → SOL
    print("\n  🔄 反向: USDC → SOL (100 USDC)")
    try:
        quote_reverse = get_quote(USDC_MINT, SOL_MINT, 100_000_000)  # 100 USDC
        sol_out = int(quote_reverse["outAmount"]) / 1_000_000_000
        price_reverse = 100 / sol_out
        print(f"  📤 输出:  {sol_out:.6f} SOL")
        print(f"  💰 价格:  1 SOL = ${price_reverse:.4f}")
        print(f"  🛣️  路由:  {' → '.join(p['swapInfo']['label'] for p in quote_reverse.get('routePlan', []))}")
    except Exception as e:
        print(f"  ❌ {e}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
