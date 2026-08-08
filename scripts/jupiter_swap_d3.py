#!/usr/bin/env python3
"""
D3 主线：Jupiter Swap API 完整流程 — quote → build → 模拟 → （可选）提交

关键发现（2026-08-07 实测）：
- quote-api.jup.ag v6/v7 已下线/被墙；新 API 是 api.jup.ag/swap/v1/quote（Metis 路由引擎）
- Jupiter Swap API 只索引 MAINNET 流动性，devnet 无池子可路由
- 本机需走 Clash 代理（127.0.0.1:7890）才能访问 api.jup.ag
"""
import json, sys, urllib.request

PROXY = "http://127.0.0.1:7890"
BASE = "https://api.jup.ag/swap/v1"
WALLET = "6MZDRo5v8K2NfdohdD76QNpSgk3GH3Aup53BeMaRAEpd"  # devnet/mainnet 同一 id.json

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def fetch(url):
    proxy = urllib.request.ProxyHandler({"https": PROXY, "http": PROXY})
    opener = urllib.request.build_opener(proxy)
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-d3"})
    with opener.open(req, timeout=20) as resp:
        return json.loads(resp.read())


def quote(amount_lamports, slippage_bps=100, mode="ExactIn"):
    params = {
        "inputMint": SOL,
        "outputMint": USDC,
        "amount": str(amount_lamports),
        "slippageBps": str(slippage_bps),
    }
    if mode == "ExactOut":
        params["swapMode"] = "ExactOut"
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return fetch(f"{BASE}/quote?{qs}")


def build(amount_lamports, wallet, slippage_bps=100):
    """GET /swap/v2/build 返回 raw swap instructions（Router 路径，可完全控制交易）"""
    params = {
        "inputMint": SOL,
        "outputMint": USDC,
        "amount": str(amount_lamports),
        "taker": wallet,
        "slippageBps": str(slippage_bps),
    }
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    return fetch(f"{BASE.replace('/v1', '/v2')}/build?{qs}")


if __name__ == "__main__":
    amount = 100_000_000  # 0.1 SOL
    print(f"=== 1. Quote: {amount/1e9} SOL -> USDC ===")
    q = quote(amount)
    print(json.dumps({k: q[k] for k in ("inAmount", "outAmount", "otherAmountThreshold", "swapMode", "priceImpactPct")}, indent=2))
    if "routePlan" in q:
        print("routePlan:")
        for r in q["routePlan"]:
            print(f"  - {r['swapInfo']['label']}  {r['percent']}%")
    if "error" in q:
        print("ERROR:", q["error"])
        sys.exit(1)

    print(f"\n=== 2. Build swap tx (Router 路径 /swap/v2/build) ===")
    b = build(amount, WALLET)
    if "error" in b:
        print("ERROR:", b["error"])
    else:
        keys = [k for k in b.keys()]
        print("build response keys:", keys)
        print("swapInstruction programId:", b.get("swapInstruction", {}).get("programId", "")[:40])
        print("setupInstructions:", len(b.get("setupInstructions", [])))
        print("computeBudgetInstructions:", len(b.get("computeBudgetInstructions", [])))
        alts = b.get("addressesByLookupTableAddress", {})
        print("addressLookupTables:", len(alts) if alts else 0)
        print("blockhash:", (b.get("blockhashWithMetadata") or {}).get("blockhash", "")[:20])
