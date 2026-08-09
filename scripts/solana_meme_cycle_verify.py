#!/usr/bin/env python3
"""Solana 长尾币完整环验证：USDC → 买 meme → 卖回 USDC（只读）。

对应 CEX 侧 `basis_arb_model.py` 的长尾测试（notes/longtail-basis-test-snapshot-vs-persistence-20260809.md）：
主流池无机会（D5 实测），长尾币可能有——本脚本用 Jupiter 真实路由验证 Solana meme 币。

口径：完整环 = 投入 USDC 买 meme → 用所得 meme 卖回 USDC → 看收回多少。
净收益 bps > 0 = 真实可赚（含 Jupiter 路由滑点，不含手动费）。

用法：
  python solana_meme_cycle_verify.py              # 全部 meme 币
  python solana_meme_cycle_verify.py --once --symbols BONK,WIF

依赖：hermes venv python3.11 + requests；Jupiter api.jup.ag（走代理，v6 已弃用）
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Solana 主网 meme 币 mint（2026-08-09 quote 探测：仅 BONK/WIF 可交易，其余地址已失效）
MEME_TOKENS = {
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
}

SAMPLE_USDC = [10, 100, 1000]  # 三个档位（USDC 数量，整数）
RETRY = 3                      # 429 重试次数
RETRY_WAIT = 3                 # 重试间隔（秒）


def get_quote(input_mint: str, output_mint: str, amount: int) -> dict:
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "slippageBps": 100,
    }
    for attempt in range(RETRY):
        try:
            r = requests.get(QUOTE_URL, params=params, timeout=15,
                             proxies={"http": PROXY, "https": PROXY})
            if r.status_code == 429:
                time.sleep(RETRY_WAIT * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == RETRY - 1:
                raise
            time.sleep(RETRY_WAIT * (attempt + 1))
    raise RuntimeError("429 after retries")


def cycle_verify(symbol: str, mint: str) -> list:
    """完整环：USDC → meme → USDC。返回各档位结果。"""
    rows = []
    for usdc_in in SAMPLE_USDC:
        try:
            # 腿 1：USDC → meme
            q1 = get_quote(USDC_MINT, mint, usdc_in * 1_000_000)  # USDC 6 decimals
            meme_out = int(q1["outAmount"])  # meme 的原子单位
            if meme_out <= 0:
                rows.append({"usdc": usdc_in, "error": "腿1无输出"})
                continue
            # 腿 2：meme → USDC
            q2 = get_quote(mint, USDC_MINT, meme_out)
            usdc_back = int(q2["outAmount"]) / 1_000_000
            net_bps = (usdc_back - usdc_in) / usdc_in * 10000
            rows.append({
                "usdc": usdc_in,
                "usdc_back": round(usdc_back, 4),
                "net_bps": round(net_bps, 2),
                "route1": "+".join(p["swapInfo"]["label"] for p in q1.get("routePlan", [])),
                "route2": "+".join(p["swapInfo"]["label"] for p in q2.get("routePlan", [])),
            })
        except Exception as e:
            rows.append({"usdc": usdc_in, "error": str(e)[:80]})
        time.sleep(0.4)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--symbols", default=",".join(MEME_TOKENS.keys()))
    args = ap.parse_args()
    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"=== Solana 长尾币完整环验证 @ {ts} ===")
    print(f"{'币种':<8}{'投入USDC':>9}{'收回USDC':>11}{'净收益bps':>11}{'路由':>44}")
    for sym in syms:
        mint = MEME_TOKENS.get(sym)
        if not mint:
            print(f"{sym:<8} 未知 mint（跳过）")
            continue
        rows = cycle_verify(sym, mint)
        for r in rows:
            if "error" in r:
                print(f"{sym:<8}{r['usdc']:>9}  ERROR {r['error']}")
            else:
                print(f"{sym:<8}{r['usdc']:>9}{r['usdc_back']:>11.4f}{r['net_bps']:>11.2f}"
                      f"{(r['route1'][:20] + ' → ' + r['route2'][:20]):>44}")
        print()


if __name__ == "__main__":
    sys.exit(main())
