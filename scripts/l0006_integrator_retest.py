#!/usr/bin/env python3
"""L0006 integrator 参数复测（2026-08-12）——25bps 平台费是否可被 integrator 归零？

背景：Day 6 L0006 实验测得 LI.FI 固定服务费 0.25% 无规模折扣（"25bps 地板"）。
群友 064（Web3Rason）发现：同一路径同一时刻，带 integrator=jumper.exchange
平台费归零（1000 USDC 到账 1000.0 vs 997.5）。本脚本复现并扩展验证。

测试矩阵：integrator ∈ {无, jumper.exchange, socket, lifi} × 金额 ∈ {100, 1k, 10k, 100k}
指标：toAmount、feeCosts（名称+USD）、gasCosts、executionDuration、toAmountMin

用法：
  python scripts/l0006_integrator_retest.py
输出：
  stdout 表格 + data/l0006_integrator_retest.csv
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 25
QUOTE_URL = "https://li.quest/v1/quote"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "l0006_integrator_retest.csv"

CHAIN_IDS = {"base": 8453, "arbitrum": 42161}
USDC = {
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
}
FROM_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
USDC_DECIMALS = 1e6

INTEGRATORS = [None, "jumper.exchange", "socket", "lifi"]
AMOUNTS = [100, 1000, 10000, 100000]


def quote(from_chain, to_chain, amount_usdc, integrator=None, retries=3):
    params = {
        "fromChain": CHAIN_IDS[from_chain],
        "toChain": CHAIN_IDS[to_chain],
        "fromToken": USDC[from_chain],
        "toToken": USDC[to_chain],
        "fromAmount": str(int(amount_usdc * USDC_DECIMALS)),
        "fromAddress": FROM_ADDRESS,
    }
    if integrator:
        params["integrator"] = integrator
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(QUOTE_URL, params=params, timeout=TIMEOUT, proxies=PROXIES)
            if r.status_code == 400:
                return {"error": "400: " + r.text[:200]}
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    return {"error": str(last_err)[:200]}


def cost_usd(costs):
    total = 0.0
    for c in costs or []:
        tok = c.get("token", {})
        decimals = tok.get("decimals", 18)
        price = float(tok.get("priceUSD", 0) or 0)
        total += float(c.get("amount", 0)) / (10 ** decimals) * price
    return total


def summarize(d):
    if "error" in d:
        return None
    est = d.get("estimate", {})
    fees = est.get("feeCosts") or []
    fee_names = ";".join(f.get("name", "?") for f in fees) or "-"
    to_amount = float(est.get("toAmount", 0)) / USDC_DECIMALS
    return {
        "to_amount": to_amount,
        "fee_names": fee_names,
        "fee_usd": cost_usd(fees),
        "gas_usd": cost_usd(est.get("gasCosts")),
        "duration_s": est.get("executionDuration", 0),
        "to_amount_min": float(est.get("toAmountMin", 0)) / USDC_DECIMALS,
        "routes": len(d.get("routes") or []),
    }


def main():
    print(f"== L0006 integrator retest {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} ==")
    print(f"path: Base USDC → Arbitrum USDC")
    rows = []
    for amount in AMOUNTS:
        for integ in INTEGRATORS:
            d = quote("base", "arbitrum", amount, integ)
            s = summarize(d)
            tag = integ or "(无)"
            if s is None:
                print(f"  {amount:>7,} USDC | {tag:16s} | ERROR: {d.get('error','')[:80]}")
                rows.append({"amount": amount, "integrator": integ or "", "to_amount": "",
                             "fee_usd": "", "gas_usd": "", "duration_s": "", "err": d.get("error", "")[:100]})
                continue
            print(f"  {amount:>7,} USDC | {tag:16s} | 到账 {s['to_amount']:.2f} | fee={s['fee_usd']:.4f}$ ({s['fee_names']}) "
                  f"| gas={s['gas_usd']:.4f}$ | {s['duration_s']}s | min={s['to_amount_min']:.2f}")
            rows.append({"amount": amount, "integrator": integ or "",
                         "to_amount": round(s["to_amount"], 4), "fee_usd": round(s["fee_usd"], 6),
                         "gas_usd": round(s["gas_usd"], 6), "duration_s": s["duration_s"],
                         "fee_names": s["fee_names"], "to_amount_min": round(s["to_amount_min"], 4)})
            time.sleep(0.4)

    with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["amount", "integrator", "to_amount", "fee_usd",
                                          "gas_usd", "duration_s", "fee_names", "to_amount_min", "err"])
        w.writeheader()
        w.writerows(rows)
    print(f"logged: {LOG_PATH}")


if __name__ == "__main__":
    main()
