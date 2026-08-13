#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
薄池深度探测（thin_pool_depth_probe.py）— 2026-08-13
======================================================
#13 执行层卡点攻坚：Jupiter swapInfo 暴露 ammKey + protocols 可单池限定报价
→ 用「每池 × 金额档执行价格」重建冲击曲线 = 深度曲线（TVL 的替代度量）。

为什么不用 TVL：
- DexScreener 未索引 Quantum/HumidiFi 等新 AMM（按协议名/地址都查不到）
- Jupiter 池列表 API 404
- 各 AMM 程序账户布局未知 → 链上 vault 解析每个协议一行代码（无底洞）

冲击曲线 = 更直接的容量度量：#13 的容量边界 = 滑点吃掉价差的位置。
深度分级（500 SOL vs 0.1 SOL 执行价差）：<20bps 深 / 20-100bps 中 / >100bps 薄

用法：hermes venv python3 scripts/thin_pool_depth_probe.py
产出：data/thin_pool_depth.csv（池 × 金额档价格 + 冲击 bps + 深度分级）
"""

import csv
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "thin_pool_depth.csv"
PROXY = "http://127.0.0.1:7890"
JUPITER_QUOTE = "https://api.jup.ag/swap/v1/quote"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# 雷达 FEE_BPS 里的薄池/新池 + 对照深池（Raydium/Orca 用于校准）
POOLS = ["Raydium", "Orca", "HumidiFi", "BisonFi", "TesseraV", "Scorch",
         "Flux", "Quantum", "Aquifer", "ZeroFi", "Byreal", "Deriverse", "AlphaQ"]
SAMPLES_SOL = [0.1, 1, 10, 100, 500]

def quote(pool, amount_lamports):
    url = (f"{JUPITER_QUOTE}?inputMint={SOL_MINT}&outputMint={USDC_MINT}"
           f"&amount={amount_lamports}&slippageBps=300&protocols={pool}")
    req = urllib.request.Request(url, headers={"User-Agent": "research"})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    with opener.open(req, timeout=25) as r:
        return json.loads(r.read().decode())

def main():
    rows = []
    for pool in POOLS:
        prices = {}          # 金额档 → 执行价（USDC/SOL）
        amm_keys = set()
        for sol in SAMPLES_SOL:
            try:
                d = quote(pool, int(sol * 1e9))
                plan = d.get("routePlan", [])
                if not plan:
                    continue
                si = plan[0].get("swapInfo", {})
                out = int(d.get("outAmount", 0)) / 1e6
                px = out / sol
                prices[sol] = px
                if si.get("ammKey"):
                    amm_keys.add(si["ammKey"])
            except Exception:
                continue
            time.sleep(0.4)
        if not prices:
            print(f"⚠️ {pool}: 无任何报价")
            continue
        # 冲击 = 最大档 vs 最小档执行价差（bps）
        small = prices.get(0.1) or prices.get(min(prices))
        large = prices.get(500) or prices.get(max(prices))
        impact_bps = (large - small) / small * 10000 if small and large else None
        grade = "深" if (impact_bps is not None and abs(impact_bps) < 20) else \
                ("中" if (impact_bps is not None and abs(impact_bps) < 100) else "薄")
        row = {"pool": pool, "impact_bps": round(impact_bps, 1) if impact_bps is not None else "",
               "grade": grade, "ammKey": next(iter(amm_keys), "")[:16],
               "n_samples": len(prices)}
        for sol, px in sorted(prices.items()):
            row[f"px_{sol}"] = round(px, 4)
        rows.append(row)
        print(f"{pool:<12} 冲击 {row['impact_bps']:>8} bps  分级[{grade}]  档数 {len(prices)}")

    if rows:
        new = not CSV_PATH.exists()
        with open(CSV_PATH, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\n✅ 落盘 data/thin_pool_depth.csv（{len(rows)} 池）")
    print("\n分级标准：500 vs 0.1 SOL 执行价差 <20bps=深 / 20-100=中 / >100=薄")
    return 0

if __name__ == "__main__":
    sys.exit(main())
