#!/usr/bin/env python3
"""Day 6 (L0006) 报价对比实验：固定 1k/10k/100k USDC 跨链，对比报价/Gas/桥费/滑点/时长。

官方路线图 L0006：固定 1k/10k/100k USDT 跨链，记录报价、Gas、桥费、滑点差异，找一条意外好路径。
本脚本用 USDC（与群友实验同口径，可比性更强），路线 Base → Arbitrum（笔记063/058 同路线，有基线）。

验证点（来自 notes/colearn-incremental-137-digest-20260810.md）：
1. 笔记058：LI.FI 固定服务费 0.25% 无规模折扣 → 三档到手率应恒定（~0.3216% = 0.25% 费 + ~0.07% 汇率差）
2. 笔记036：成本 U 型曲线最优点 ~1000U → 10k/100k 档损耗应接近或略升
3. 笔记116：容量假象 → 100k 档若路径/报价突变 = 容量问题
4. 笔记063：速度溢价 → 记录 executionDuration，快路径少到账多少

用法：
  python scripts/day6_lifi_quote_compare.py            # 跑三档报价对比
  python scripts/day6_lifi_quote_compare.py --amounts 1000,10000,100000

依赖：python3 + requests（走代理）

⚠️ 2026-08-12 勘误：本脚本未带 integrator 参数，测的是「默认渠道」的 25bps 平台费
（见 `notes/l0006-integrator-retest-20260812.md`）。带 `integrator=jumper.exchange` 该费归零。
重测用 `scripts/l0006_integrator_retest.py`。
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 25
QUOTE_URL = "https://li.quest/v1/quote"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "day6_lifi_quote_compare.csv"

# 链与代币（原生 USDC）
CHAIN_IDS = {"base": 8453, "arbitrum": 42161, "optimism": 10}
USDC = {
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
}
# 只读 quote 的占位 EOA（公开地址，不签名不交易）
FROM_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

USDC_DECIMALS = 1e6


def quote(from_chain: str, to_chain: str, amount_usdc: float, retries: int = 3,
          allow_bridges: str = "", deny_bridges: str = "") -> dict:
    """LI.FI quote：返回拆解后的成本结构。amount 单位 USDC。"""
    params = {
        "fromChain": CHAIN_IDS[from_chain],
        "toChain": CHAIN_IDS[to_chain],
        "fromToken": USDC[from_chain],
        "toToken": USDC[to_chain],
        "fromAmount": str(int(amount_usdc * USDC_DECIMALS)),
        "fromAddress": FROM_ADDRESS,
    }
    if allow_bridges:
        params["allowBridges"] = allow_bridges
    if deny_bridges:
        params["denyBridges"] = deny_bridges
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(QUOTE_URL, params=params, timeout=TIMEOUT, proxies=PROXIES)
            r.raise_for_status()
            d = r.json()
            est = d.get("estimate", {})
            def cost_usd(costs):
                total = 0.0
                for c in costs or []:
                    tok = c.get("token", {})
                    decimals = tok.get("decimals", 18)
                    price = float(tok.get("priceUSD", 0) or 0)
                    total += float(c.get("amount", 0)) / (10 ** decimals) * price
                return total
            fee_total_usd = cost_usd(est.get("feeCosts"))
            gas_total_usd = cost_usd(est.get("gasCosts"))
            to_amount = int(est.get("toAmount", 0)) / USDC_DECIMALS
            to_min = int(est.get("toAmountMin", 0)) / USDC_DECIMALS
            # 总损耗 = (投入 - 预计到账) / 投入，bps
            loss_bps = (amount_usdc - to_amount) / amount_usdc * 10000 if amount_usdc else 0
            return {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "from_chain": from_chain, "to_chain": to_chain,
                "amount_usdc": amount_usdc,
                "to_amount": round(to_amount, 6),
                "to_min": round(to_min, 6),
                "loss_bps": round(loss_bps, 1),
                "fee_usd": round(fee_total_usd, 4),
                "gas_usd": round(gas_total_usd, 4),
                "duration_s": est.get("executionDuration"),
                "tool": d.get("tool", "?"),
                "allow_bridges": allow_bridges or "best",
            }
        except Exception as e:
            last_err = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"quote failed {from_chain}→{to_chain} @{amount_usdc}: {last_err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--amounts", default="1000,10000,100000",
                    help="三档金额 USDC（逗号分隔），默认官方 L0006 的 1k/10k/100k")
    ap.add_argument("--from-chain", default="base")
    ap.add_argument("--to-chain", default="arbitrum")
    ap.add_argument("--bridges", default="best,across,polymer",
                    help="桥变体（逗号分隔）：best=默认最优 / across=快桥 / polymer=慢桥 / deny:eco 等")
    ap.add_argument("--rounds", type=int, default=1, help="每档重复次数（取多次防瞬时报价）")
    args = ap.parse_args()

    amounts = [float(x) for x in args.amounts.split(",")]
    rows = []
    for amt in amounts:
        for bridge in args.bridges.split(","):
            bridge = bridge.strip()
            allow, deny = "", ""
            if bridge == "best":
                pass
            elif bridge.startswith("deny:"):
                deny = bridge.split(":", 1)[1]
            else:
                allow = bridge
            label = bridge
            for rnd in range(args.rounds):
                try:
                    q = quote(args.from_chain, args.to_chain, amt, allow_bridges=allow, deny_bridges=deny)
                    q["round"] = rnd + 1
                    q["bridge_variant"] = label
                    rows.append(q)
                    print(f"[ok] {amt:>8.0f} USDC {label:>10} r{rnd+1}: 到手 {q['to_amount']:.4f} "
                          f"损耗 {q['loss_bps']:.1f}bps 费 ${q['fee_usd']:.4f} gas ${q['gas_usd']:.4f} "
                          f"时长 {q['duration_s']}s 桥 {q['tool']}")
                except Exception as e:
                    print(f"[err] {amt:>8.0f} USDC {label:>10} r{rnd+1}: {e}")

    if not rows:
        print("全部失败", file=sys.stderr)
        return 1

    # 落盘
    LOG_PATH.parent.mkdir(exist_ok=True)
    new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if new:
            w.writeheader()
        w.writerows(rows)

    # 汇总分析
    print(f"\n=== 汇总 @ {rows[0]['ts']} ===")
    print(f"路线: {args.from_chain} → {args.to_chain}（原生 USDC）")
    print(f"{'金额':>10}{'变体':>10}{'到手':>12}{'损耗bps':>9}{'费用USD':>9}{'GasUSD':>9}{'时长s':>8}{'桥':>16}")
    for r in rows:
        print(f"{r['amount_usdc']:>10.0f}{r['bridge_variant']:>10}{r['to_amount']:>12.4f}{r['loss_bps']:>9.1f}"
              f"{r['fee_usd']:>9.4f}{r['gas_usd']:>9.4f}{str(r['duration_s']):>8}{r['tool']:>16}")
    # 到手率是否恒定（058 验证：无规模折扣 → 各档损耗应 ≈ 恒定）
    best_rows = [r for r in rows if r["bridge_variant"] == "best"]
    if len(best_rows) >= 3:
        losses = [r["loss_bps"] for r in best_rows]
        spread = max(losses) - min(losses)
        print(f"\n058 验证（无规模折扣）：best 三档损耗差 {spread:.1f}bps"
              f"{' → ✅ 恒定，无折扣' if spread < 5 else ' → ⚠️ 有规模效应，需查容量假象'}")
    # 同金额不同桥对比（063 验证：速度溢价）
    for amt in amounts:
        group = [r for r in rows if r["amount_usdc"] == amt and len({x["bridge_variant"] for x in rows if x['amount_usdc']==amt}) > 1]
        if len(group) >= 2:
            fast = min(group, key=lambda x: x["duration_s"] or 1e9)
            cheap = min(group, key=lambda x: -x["to_amount"])
            if fast["tool"] != cheap["tool"] and fast["duration_s"] and cheap["duration_s"]:
                d_t = (cheap["duration_s"] or 0) - (fast["duration_s"] or 0)
                d_usd = cheap["to_amount"] - fast["to_amount"]
                print(f"\n063 验证 @{amt:>8.0f}U：{cheap['tool']}({cheap['duration_s']}s,到{cheap['to_amount']:.2f})"
                      f" vs {fast['tool']}({fast['duration_s']}s,到{fast['to_amount']:.2f})"
                      f" → 快{d_t}s 少拿 ${d_usd:.4f}（{d_usd/amt*10000:.1f}bps）")
    print(f"\n已记录 → {LOG_PATH}")


if __name__ == "__main__":
    import sys
    sys.exit(main())
