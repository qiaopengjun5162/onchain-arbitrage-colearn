#!/usr/bin/env python3
"""Backrun 冲击模拟器（2026-08-10）：复刻 888BMM 案例的「受害交易 + backrun」机制。

场景（888BMM 实例如下，2026-08-10 17:38 UTC+8）：
  受害交易：17,920 USDC 砸进 EURC 储备近耗尽的薄池，只拿回 246.66 EURC（隐价 $72.6）
  backrun：正常池买入 EURC（$1.18）→ 受害池虚高价卖出 → 净赚 $17,275

本脚本对任意「正常池 + 薄池」组合模拟：
  1. 受害交易买穿薄池（恒定乘积）→ 算价格扭曲
  2. backrun：正常池价买 EURC → 受害池卖出（含 0.3% 费率）
  3. 输出：扭曲%、backrun 毛利润、净利（扣费）

数据：DexScreener 的 price + liquidity 反推储备（简化，不解析池子内部账户）。

用法：
    python scripts/backrun_impact_sim.py --victim-liquidity 85000 --victim-price 1.15 \
        --normal-price 1.15 --attack-usd 17920
"""

import argparse
import math


def simulate(liq_usd, normal_price, attack_usd, fee=0.003, verbose=True):
    """模拟受害+backrun。liq_usd=薄池双边流动性，normal_price=正常 EURC 价（USD）。"""
    # 反推薄池储备（恒定乘积池：liq ≈ 双边 USD 之和；EURC 池双边各约 liq/2 USD）
    half = liq_usd / 2.0
    # 池内 EURC 数量 = half / price_eurc_usd；池内 USDC 数量 = half / 1.0（USDC≈1）
    eurc_reserve = half / normal_price          # 薄池 EURC 数量
    usdc_reserve = half                          # 薄池 USDC 数量
    k = eurc_reserve * usdc_reserve

    if verbose:
        print(f"薄池初始: EURC={eurc_reserve:,.2f} | USDC=${usdc_reserve:,.0f} | k={k:,.0f}")

    # --- 受害交易：attack_usd 买 EURC（池子收 USDC，出 EURC） ---
    usdc_in = attack_usd
    eurc_out_ideal = usdc_in * (normal_price and 1 / normal_price)  # 理想（无冲击）
    new_usdc = usdc_reserve + usdc_in
    new_eurc = k / new_usdc
    eurc_out = (eurc_reserve - new_eurc) * (1 - fee)
    victim_implied_price = usdc_in / eurc_out if eurc_out > 0 else float("inf")

    if verbose:
        print(f"受害交易: ${usdc_in:,.0f} → {eurc_out:,.2f} EURC（理想 {eurc_out_ideal:,.2f}）")
        print(f"  受害隐价: ${victim_implied_price:,.2f}/EURC（正常 ${normal_price:,.2f}）"
              f" → 扭曲 {victim_implied_price / normal_price:,.0f}×")
        print(f"  薄池新储备: EURC={new_eurc:,.2f} | USDC=${new_usdc:,.0f}")

    # --- backrun：正常池买入 EURC（价 normal_price）→ 受害池卖出（价被推高） ---
    # backrun 买入量 = 受害池剩余可卖量的一部分（假设买入后受害池 EURC 价格仍 > 正常价）
    # 最优量：使受害池卖出 EURC 的平均价最大化 —— 简化为「把受害池新价吃到正常价的 M 倍」
    # 简化：backrun 买入 eurc_qty，全部在受害池卖出
    # 受害池当前状态：EURC=new_eurc, USDC=new_usdc（池子从受害者手里拿到 USDC）
    # backrun 卖 EURC 进受害池（池子出 USDC）：用恒定乘积反向
    # 利润 = 卖出所得 - 买入成本
    # 买入量 = 受害池当前 EURC 的一部分（防止卖穿）：取 30%
    buy_qty = new_eurc * 0.30
    cost = buy_qty * normal_price                      # 正常池买入成本
    # 受害池卖出（卖 EURC 换 USDC）
    k2 = new_eurc * new_usdc
    out_usdc = (new_usdc - k2 / (new_eurc + buy_qty)) * (1 - fee)
    profit = out_usdc - cost
    backrun_price = out_usdc / buy_qty if buy_qty > 0 else 0

    if verbose:
        print(f"\nbackrun: 买入 {buy_qty:,.2f} EURC @ ${normal_price:,.4f} = ${cost:,.2f}")
        print(f"  受害池卖出 → ${out_usdc:,.2f}（均价 ${backrun_price:,.4f}/EURC）")
        print(f"  ** backrun 利润 = ${profit:,.2f} **")

    return {"profit": profit, "distortion": victim_implied_price / normal_price if normal_price else 0,
            "victim_implied_price": victim_implied_price}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--victim-liquidity", type=float, required=True, help="薄池双边流动性 USD")
    ap.add_argument("--victim-price", type=float, default=1.15, help="薄池 EURC 正常价")
    ap.add_argument("--normal-price", type=float, default=1.15, help="正常池 EURC 价")
    ap.add_argument("--attack-usd", type=float, default=17920, help="受害交易金额 USD")
    ap.add_argument("--fee", type=float, default=0.003, help="AMM 费率（默认 0.3%）")
    args = ap.parse_args()

    print(f"=== Backrun 冲击模拟 ===")
    print(f"薄池流动性 ${args.victim_liquidity:,.0f} | 正常价 ${args.normal_price} | 受害金额 ${args.attack_usd:,.0f}")
    r = simulate(args.victim_liquidity, args.normal_price, args.attack_usd, args.fee)
    print(f"\n结论: 价格扭曲 {r['distortion']:,.1f}× | backrun 利润 ${r['profit']:,.2f}")
    if r["profit"] > 0:
        print("→ 该薄池对这笔受害金额存在可执行的 backrun（正利润）")
    else:
        print("→ 利润为负：池子太浅/费率吃掉空间，backrun 不可执行")


if __name__ == "__main__":
    main()
