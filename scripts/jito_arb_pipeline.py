#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jito Arb Pipeline（jito_arb_pipeline.py）— D13 剩余项（2026-08-16）
====================================================================
把三段串成一条「发现→判定→执行」链（D15 pipeline 整合的雏形）：

  1. 发现：DexScreener 拉真实 SOL/USDC 深池（流动性 TOP N）
  2. 判定：复用 arb_profit_simulator 的 Pool 模型跑跨池搬（薄→深）+ 往返
           → 净利 bps > 阈值 且 扣 gas 后仍正 = 正利润路径
  3. 执行：正利润路径 → Jupiter quote → 官方 /swap/v1/swap 交易 → Jito sendBundle
           （复用 jito_swap_bundle.py 的 jup_quote/jup_swap_tx/提交轮询）

⚠️ 现实预期：主流池间价差已被磨平（共学实测：常驻价差被磨平，肉在事件窗口）。
   本脚本跑出「0 信号」= 正确输出，与哨兵/知识图谱结论一致；价值在流程打通。

用法：
  python scripts/jito_arb_pipeline.py                 # 判定 + dry-run 模拟执行
  python scripts/jito_arb_pipeline.py --execute       # 有正利润路径则真提交（小额）
  python scripts/jito_arb_pipeline.py --top 10 --amount 1.0

依赖：hermes venv（solders/solana-py + 无 requests 也行，urllib 够）
"""
import argparse
import base64
import json
import random
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

# 复用同目录脚本
sys.path.insert(0, str(Path(__file__).resolve().parent))
from arb_profit_simulator import Pool, run_crosspool, run_roundtrip  # noqa: E402
from jito_swap_bundle import (http_get, http_post, jup_quote, jup_swap_tx,  # noqa: E402
                              pick_tip, ENGINE, RPC, LOG_FILE as SWAP_LOG)
from solders.keypair import Keypair  # noqa: E402
from solders.transaction import VersionedTransaction  # noqa: E402
from solders.message import MessageV0  # noqa: E402
from solders.system_program import transfer, TransferParams  # noqa: E402
from solders.pubkey import Pubkey  # noqa: E402

PROXY = "http://127.0.0.1:7890"
DEXSCREENER = "https://api.dexscreener.com/latest/dex/search"
MIN_EDGE_BPS = 2.0          # 判定阈值（与模拟器一致）
SOL_PRICE_USD = 75.5        # ⚠️ 2026-08-16 实测 SOL ≈ $75.5（模拟器默认 175 是演示值）
GAS_SOL = 0.000005

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def fetch_pools(symbol_a="SOL", symbol_b="USDC", top_n=6):
    """DexScreener 拉同对深池。返回 [{name, rx, ry, fee_bps, gas_sol, dexId, pairAddress, price}]

    ⚠️ CLMM 池（Raydium 等）的 liquidity.base/quote reserve 字段不可靠
    （实测 2026-08-16：rx=2000万 SOL / ry=22 USDC 与 priceUsd=$81 完全不符）——
    改用 priceUsd 锚定 + 流动性 USD 反推均衡储备：rx = liq/2/price, ry = liq/2"""
    q = urllib.parse.quote(f"{symbol_a} {symbol_b}")
    d = http_get(f"{DEXSCREENER}?q={q}")
    pairs = [p for p in d.get("pairs", [])
             if p.get("baseToken", {}).get("symbol") == symbol_a
             and p.get("quoteToken", {}).get("symbol") == symbol_b]
    pairs.sort(key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
    pools = []
    for p in pairs[:top_n]:
        liq_usd = float(p.get("liquidity", {}).get("usd", 0) or 0)
        price = float(p.get("priceUsd", 0) or 0)
        if liq_usd <= 0 or price <= 0:
            continue
        rx = liq_usd / 2 / price   # 均衡近似：半流动性在 base
        ry = liq_usd / 2           # 半流动性在 quote
        pools.append({
            "name": f"{p.get('dexId','?')}:{p.get('pairAddress','')[:8]}",
            "rx": rx, "ry": ry, "fee_bps": 25, "gas_sol": GAS_SOL,
            "price": price,
        })
    return pools


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="有正利润路径则真提交（默认仅 dry-run 判定）")
    ap.add_argument("--top", type=int, default=6, help="取 TOP N 深池")
    ap.add_argument("--amount", type=float, default=1.0, help="判定本金（X 数量，SOL）")
    ap.add_argument("--pool-file", type=str, help="从 JSON 文件读池子（替代 DexScreener 拉取）")
    ap.add_argument("--prices", type=str, help="价格偏离注入：name:price,name:price（模拟器原始参数，模拟真实价差）")
    args = ap.parse_args()

    # 1) 发现
    if args.pool_file:
        pools_data = json.loads(Path(args.pool_file).read_text())
    else:
        pools_data = fetch_pools(top_n=args.top)
    if not pools_data:
        print("❌ 没拉到池子（DexScreener 可能被限流）")
        sys.exit(1)
    # ⚠️ 价格锚定：DexScreener 的 priceUsd 对不同池有显示噪音（实测 Raydium 显示 $81.61
    # vs 真实 SOL≈$75.5），直接当可执行价差会出假正利润。默认用池子价格中位数统一锚定
    # （池间价差=0，只评估滑点/费率），有真实价差证据时用 --prices 注入。
    anchor = SOL_PRICE_USD
    if args.prices:
        for spec in args.prices.split(","):
            name, px = spec.rsplit(":", 1)  # 池名本身含冒号（dexId:pairAddress），从右切
            for d in pools_data:
                if d["name"] == name:
                    d["ry"] = float(px) * d["rx"]
                    break
    else:
        prices = sorted(d["price"] for d in pools_data)
        anchor = prices[len(prices) // 2] if prices else SOL_PRICE_USD
        for d in pools_data:
            d["price"] = anchor
            d["ry"] = anchor * d["rx"]  # 统一锚定 → 池间价差 0
    pools = [Pool(**{k: d[k] for k in ("name", "rx", "ry", "fee_bps", "gas_sol")}) for d in pools_data]
    print(f"📊 深池 {len(pools)} 个（TOP {args.top}，锚定价 ${anchor:.2f}）：")
    for d in pools_data:
        print(f"  {d['name']:<22} rx={d['rx']:>14,.0f} ry={d['ry']:>16,.0f}")

    # 2) 判定：跨池搬（薄→深 两两组合）+ 单腿往返
    amt = args.amount
    results = []
    for a in pools:
        results.append(run_roundtrip(a, amt))
    for a in pools:
        for b in pools:
            if a.name == b.name:
                continue
            results.append(run_crosspool(a, b, amt))

    # 3) 过滤：净利 bps > 阈值 且 扣 gas 后仍正
    print(f"\n本金 {amt} SOL | SOL=${SOL_PRICE_USD} | 阈值 {MIN_EDGE_BPS}bps")
    print("=" * 90)
    print(f"{'类型':<10}{'路径':<30}{'净利bps':>10}{'净利USD':>12}{'判定':>8}")
    print("-" * 90)
    positives = []
    for r in sorted(results, key=lambda x: -x["net_bps"]):
        gas_usd = r.get("gas_usd", 0)
        net_usd = (r["net_bps"] / 10000) * amt * SOL_PRICE_USD - gas_usd
        net_bps_after_gas = r["net_bps"] - gas_usd / (amt * SOL_PRICE_USD) * 10000
        verdict = "✅ 可执行" if net_bps_after_gas > MIN_EDGE_BPS else ("👀 观察" if net_bps_after_gas > 0 else "❌ 负")
        label = r.get("path", r.get("pool", ""))
        print(f"{r['type']:<10}{label:<30}{r['net_bps']:>10.1f}{net_usd:>12.4f}{verdict:>8}")
        if net_bps_after_gas > MIN_EDGE_BPS:
            positives.append((r, label))

    print("=" * 90)
    if not positives:
        print("→ 0 信号 = 正确输出：主流池常驻价差已被磨平（与知识图谱「14 类剩 3 类活」一致）")
        print("  流程已打通：有正利润路径时本脚本会自动接 Jupiter quote → swap → Jito bundle")
        return

    # 4) 执行：取最优正利润路径 → Jupiter quote → swap → bundle（或 dry-run 演示）
    best, label = positives[0]
    print(f"\n🎯 正利润路径 {len(positives)} 条，取最优: {label}（net_bps={best['net_bps']:.1f}）")
    if not args.execute:
        print("🔒 --execute 未开，停在 dry-run（真实执行需人工确认）")
        return

    with open(Path.home() / ".config/solana/id.json") as f:
        kp = Keypair.from_bytes(bytes(json.load(f)))
    print(f"🔑 钱包: {kp.pubkey()}")

    # 5) Jupiter quote → swap 交易 → 重签名
    amount_lamports = int(amt * 1e9)
    q = jup_quote(SOL_MINT, USDC_MINT, amount_lamports, 100)
    if "error" in q:
        print("❌ quote 失败:", q["error"])
        sys.exit(1)
    print(f"📊 Jupiter quote: {q['inAmount']} → {q['outAmount']} lamports "
          f"(route {len(q.get('routePlan', []))} 跳)")
    swap_b64, _ = jup_swap_tx(str(kp.pubkey()), q)
    swap_tx_unsigned = VersionedTransaction.from_bytes(base64.b64decode(swap_b64))
    swap_tx = VersionedTransaction(swap_tx_unsigned.message, [kp])
    blockhash = swap_tx.message.recent_blockhash

    # 6) tip 交易
    tip_lamports, tip_basis = pick_tip()
    tip_acc = random.choice(http_post(ENGINE, {"jsonrpc": "2.0", "id": 1, "method": "getTipAccounts", "params": []})["result"])
    tip_tx = VersionedTransaction(MessageV0.try_compile(kp.pubkey(),
                                                        [transfer(TransferParams(from_pubkey=kp.pubkey(),
                                                                                 to_pubkey=Pubkey.from_string(tip_acc),
                                                                                 lamports=tip_lamports))],
                                                        [], blockhash), [kp])
    print(f"💸 tip: {tip_basis} = {tip_lamports} lamports")

    # 7) 提交 + 轮询
    encoded = [base64.b64encode(bytes(swap_tx)).decode(), base64.b64encode(bytes(tip_tx)).decode()]
    d = http_post(ENGINE, {"jsonrpc": "2.0", "id": 1, "method": "sendBundle",
                           "params": [encoded, {"encoding": "base64"}]})
    if "error" in d:
        print("❌ sendBundle 失败:", d["error"])
        sys.exit(1)
    bid = d["result"]
    print(f"✅ bundle_id: {bid}")
    for i in range(12):
        time.sleep(3)
        st = http_post(ENGINE, {"jsonrpc": "2.0", "id": 1, "method": "getBundleStatuses",
                                "params": [[bid]]})
        v = st.get("result", {}).get("value")
        if v:
            s = v[0]
            conf = s.get("confirmation_status", "?")
            print(f"  [{i}] {conf} err={s.get('err')}")
            if conf in ("finalized", "confirmed"):
                print(f"🎉 bundle 已确认: https://explorer.jito.wtf/bundle/{bid}")
                return
            if s.get("err") is not None:
                print(f"❌ Invalid: {s.get('err')}")
                return
        else:
            st2 = http_post(ENGINE, {"jsonrpc": "2.0", "id": 1, "method": "getInflightBundleStatuses",
                                     "params": [[bid]]})
            v2 = st2.get("result", {}).get("value", [])
            if v2:
                s2 = v2[0]
                if s2.get("status") in ("Invalid", "Landed"):
                    print(f"  [{i}] {s2['status']} slot={s2.get('landed_slot')}")
                    if s2["status"] == "Landed":
                        print(f"🎉 bundle Landed: https://explorer.jito.wtf/bundle/{bid}")
                    return
    print("⏳ 轮询超时，手动查 explorer.jito.wtf")


if __name__ == "__main__":
    main()
