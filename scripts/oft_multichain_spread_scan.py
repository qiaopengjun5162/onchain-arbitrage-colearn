#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFT 多链价差扫描 v1（2026-08-12）——三步法的第 2 步
==================================================
输入：多链币 symbol 列表（可来自 LayerZero playbook 已验证资产）
动作：DexScreener 按链分组取最优池报价 → 跨链两两价差 bps → 排序输出

用法：
    python scripts/oft_multichain_spread_scan.py --symbols DOS,ZRO,AIXBT
    python scripts/oft_multichain_spread_scan.py --file assets.txt
输出：价差排序表（毛价差，未扣桥费/gas——只做初筛，肉不肉要再过桥费关）
"""

import argparse
import json
import os
import sys
import urllib.request

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
MIN_LIQ = 20_000          # 池子最小流动性（低于此价差不可执行）
CHAIN_MAP = {"base": "Base", "bsc": "BSC", "ethereum": "ETH", "arbitrum": "Arb", "polygon": "Poly"}

def http_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXIES))
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def scan(symbol):
    try:
        d = http_json(f"https://api.dexscreener.com/latest/dex/search?q={symbol}")
    except Exception:
        return symbol, []
    best = {}  # chain -> best pair
    for p in (d.get("pairs") or []):
        chain = p.get("chainId")
        if chain not in CHAIN_MAP:
            continue
        base = (p.get("baseToken") or {}).get("symbol", "").upper()
        if base != symbol.upper():
            continue  # 严格 symbol 过滤防假币
        liq = float((p.get("liquidity") or {}).get("usd") or 0)
        if liq < MIN_LIQ:
            continue
        price = float(p.get("priceUsd") or 0)
        if price <= 0:
            continue
        cur = best.get(chain)
        if cur is None or liq > cur["liq"]:
            best[chain] = {"chain": chain, "price": price, "liq": liq,
                           "dex": p.get("dexId"), "vol": float((p.get("volume") or {}).get("h24") or 0)}
    return symbol, list(best.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", help="逗号分隔")
    ap.add_argument("--file", help="每行一个 symbol")
    args = ap.parse_args()
    syms = []
    if args.file:
        syms = [l.strip() for l in open(args.file) if l.strip() and not l.startswith("#")]
    if args.symbols:
        syms += [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not syms:
        print("用法: --symbols DOS,ZRO 或 --file assets.txt")
        return 1

    print(f"=== OFT 多链价差扫描 @ {__import__('time').strftime('%H:%M:%S')}（毛价差，未扣桥费） ===\n")
    rows = []
    for s in syms:
        sym, chains = scan(s)
        if len(chains) < 2:
            print(f"{sym:10s} 无跨链池（{len(chains)} 链）")
            continue
        pairs = []
        for i in range(len(chains)):
            for j in range(i + 1, len(chains)):
                a, b = chains[i], chains[j]
                sp = (b["price"] - a["price"]) / a["price"] * 10000
                pairs.append((f"{CHAIN_MAP[a['chain']]}↔{CHAIN_MAP[b['chain']]}", sp,
                              a["price"], b["price"], min(a["liq"], b["liq"])))
        pairs.sort(key=lambda x: -abs(x[1]))
        for name, sp, pa, pb, liq in pairs[:2]:
            rows.append((abs(sp), sym, name, sp, pa, pb, liq))
        best = pairs[0]
        print(f"{sym:10s} {best[0]:9s} {best[1]:+8.1f}bps  {best[2]:<10.4f} {best[3]:<10.4f}  min_liq ${best[4]:,.0f}")

    print("\n=== 排序（|价差| 前 15） ===")
    for abs_sp, sym, name, sp, pa, pb, liq in sorted(rows, key=lambda x: -x[0])[:15]:
        flag = " ⚠️ 待桥费验证" if abs_sp >= 50 else ""
        print(f"  {sym:10s} {name:9s} {sp:+8.1f}bps  {pa:.4f} vs {pb:.4f}  min_liq ${liq:,.0f}{flag}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
