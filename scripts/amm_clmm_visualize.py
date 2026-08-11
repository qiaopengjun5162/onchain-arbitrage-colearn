#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uniswap V3 / Orca Whirlpool CLMM 集中流动性数学验证 (amm_clmm_visualize.py) — D9 预习
====================================================================================
验证内容：
  1. tick 与价格：P(t) = 1.0001^tick，±10% 区间 = 多少个 tick
  2. 虚拟储备 vs 实际储备：区间内提供同等深度的资金效率倍数
  3. 区间内 swap 公式：Δy = L·(√P_new − √P_cur)，Δx = L·(1/√P_cur − 1/√P_new)
  4. 出区间 → 单边资产（网格穿界风险的 AMM 版）
  5. 可视化：V2 vs V3 流动性分布 + 资金效率

用法：hermes venv python3 scripts/amm_clmm_visualize.py
产出：data/clmm_visual.png（流动性分布对比图）
"""
import math
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_PNG = BASE_DIR / "data" / "clmm_visual.png"

TICK_BASE = 1.0001  # V3/Whirlpool tick 步长


def tick_to_price(tick: int) -> float:
    return TICK_BASE ** tick


def price_to_tick(p: float) -> int:
    return int(round(math.log(p) / math.log(TICK_BASE)))


def sqrt(p: float) -> float:
    return math.sqrt(p)


def liq_from_reserves(x, y, pa, pb, p_cur):
    """由实际储备 + 区间反推流动性 L（标准 V3 公式）。"""
    sa, sb = sqrt(pa), sqrt(pb)
    sp = sqrt(p_cur)
    # 区间内：x = L·(1/√p − 1/√pb)，y = L·(√p − √pa)
    L_from_x = x / (1 / sp - 1 / sb)
    L_from_y = y / (sp - sa)
    return L_from_x, L_from_y


def swap_y_given_x(L, sp_cur, sp_new):
    """卖 X 买 Y：价格从 sp_cur 升到 sp_new，输出 Y = L·(sp_new − sp_cur)。"""
    return L * (sp_new - sp_cur)


def swap_x_given_y(L, sp_cur, sp_new):
    """卖 Y 买 X：价格从 sp_cur 降到 sp_new，输出 X = L·(1/sp_new − 1/sp_cur)。"""
    return L * (1 / sp_new - 1 / sp_cur)


def main():
    print("=" * 72)
    print("1) tick 与价格：P(t) = 1.0001^tick")
    print("=" * 72)
    for t in (0, 100, 954, 23027):
        print(f"   tick={t:>6} -> P = {tick_to_price(t):.4f}")
    p0 = 74.0  # SOL/USDC 当前价附近（对应 Raydium 实测 $74.18）
    t0 = price_to_tick(p0)
    print(f"   当前价 P={p0} -> tick={t0}")
    for w in (0.05, 0.10, 0.20, 0.50):
        pl, ph = p0 * (1 - w), p0 * (1 + w)
        tl, th = price_to_tick(pl), price_to_tick(ph)
        print(f"   ±{w*100:>3.0f}% 区间 [{pl:.1f}, {ph:.1f}] -> tick [{tl}, {th}] 宽 {th-tl} ticks")

    print("\n" + "=" * 72)
    print("2) 虚拟储备 vs 实际储备：资金效率")
    print("=" * 72)
    # V2 池：实际储备 = 全部，价格 74
    x2, y2 = 67_851.11, 5_033_520.92  # Raydium SOL-USDC 实测储备
    L2 = math.sqrt(x2 * y2)
    print(f"   V2 池: X={x2:,.0f} SOL, Y={y2:,.0f} USDC, L(√k)={L2:,.0f}")
    # V3 同 L：±10% 区间 [66.6, 81.4]
    pa, pb = p0 * 0.9, p0 * 1.1
    sa, sb = sqrt(pa), sqrt(pb)
    sp = sqrt(p0)
    # 实际需要的储备（价格在区间中点时）：
    #   x = L·(1/√p − 1/√pb)，y = L·(√p − √pa)  ← 价格在区间内，X 由下沿+当前价决定，Y 由当前价+上沿决定
    x3 = L2 * (1 / sp - 1 / sb)
    y3 = L2 * (sp - sa)
    print(f"   V3 同 L，±10% 区间: 实际需 X={x3:,.0f} SOL, Y={y3:,.0f} USDC")
    print(f"   资金效率: X {x2/x3:.1f}x, Y {y2/y3:.1f}x —— 同样的 L 只花 ~1/10 资金")
    # 反向：同样资金在 ±10% 区间能提供多少 L
    x_same, y_same = 6_785, 503_352  # V2 的 1/10
    L_small = min(x_same / (1 / sp - 1 / sb), y_same / (sp - sa))
    print(f"   （反向）用 V2 的 1/10 资金放 ±10% 区间 -> L={L_small:,.0f} = V2 L 的 {L_small/L2*100:.0f}%")

    print("\n" + "=" * 72)
    print("3) 区间内 swap（L 恒定）")
    print("=" * 72)
    L = L2
    for dpct in (0.01, 0.05, 0.099):  # 价格上升 1% / 5% / 9.9%（接近区间上沿）
        p_new = p0 * (1 + dpct)
        dy = swap_y_given_x(L, sp, sqrt(p_new))
        print(f"   价格 {p0} -> {p_new:.2f} (+{dpct*100:.1f}%): 输出 Y = {dy:,.0f} USDC（= SOL 上涨带来的池内 USDC 增加）")
    # 价格出区间上沿后：X 耗尽，只剩 Y
    p_out = p0 * 1.11  # 超出 1.1 上沿
    dy_out = swap_y_given_x(L, sp, sqrt(pb))
    print(f"   价格到上沿 {pb:.2f} 时: X 已耗尽，再涨 -> 池内只剩 Y={y3:,.0f} USDC 单边资产")

    print("\n" + "=" * 72)
    print("4) 出区间 = 单边资产（网格穿界风险的 AMM 版）")
    print("=" * 72)
    print("   价格 < 下沿: 全部是 X（SOL），不再赚手续费，等价格回来")
    print("   价格 > 上沿: 全部是 Y（USDC），不再赚手续费")
    print("   -> 与网格回测同构：区间外单向堆积（网格=库存单向堆积）")
    print("   实盘含义：CLMM LP 的『无常损失』在出区间时锁定为方向性风险")

    print("\n" + "=" * 72)
    print("5) 可视化（V2 vs V3 流动性分布）")
    print("=" * 72)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib import font_manager

        # macOS 中文字体（DejaVu Sans 无 CJK 字形，中文 title 会变方框）
        for fp in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
                   "/System/Library/Fonts/Hiragino Sans GB.ttc"):
            if Path(fp).exists():
                font_manager.fontManager.addfont(fp)
                plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
                break

        prices = np.linspace(p0 * 0.5, p0 * 1.5, 400)
        # V2: 每价格点可用的「单位价格区间流动性」= y/x 变化率（恒定 = 全区间均匀）
        v2_density = np.full_like(prices, 1.0)
        # V3 ±10%: 区间内集中（高度 = 资金效率），区间外 0
        in_range = (prices >= pa) & (prices <= pb)
        v3_density = np.where(in_range, x2 / x3, 0.0)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        ax1.plot(prices, v2_density, label="V2 (均匀分布)", color="gray", lw=2)
        ax1.plot(prices, v3_density, label=f"V3 ±10% 区间 (资金效率 {x2/x3:.1f}x)", color="tab:blue", lw=2)
        ax1.axvline(pa, color="tab:red", ls="--", alpha=0.6, label="区间下沿")
        ax1.axvline(pb, color="tab:red", ls="--", alpha=0.6, label="区间上沿")
        ax1.set_xlabel("价格 (USDC/SOL)")
        ax1.set_ylabel("流动性密度 (相对)")
        ax1.set_title("V2 vs V3 流动性分布对比（同 L）")
        ax1.legend()
        ax1.grid(alpha=0.3)

        # 资金效率 vs 区间宽度
        widths = np.linspace(0.02, 0.5, 100)
        eff = 1 / widths  # 近似：区间宽度占比越小资金效率越高
        ax2.plot(widths * 100, eff, color="tab:green", lw=2)
        ax2.set_xlabel("区间宽度 (±%)")
        ax2.set_ylabel("资金效率 (×)")
        ax2.set_title("资金效率 vs 区间宽度（窄区间 = 高杠杆做市）")
        ax2.grid(alpha=0.3)

        plt.tight_layout()
        os.makedirs(OUT_PNG.parent, exist_ok=True)
        plt.savefig(OUT_PNG, dpi=120)
        print(f"   已保存: {OUT_PNG}")
    except Exception as e:  # noqa: BLE001
        print(f"   ⚠️ 可视化失败: {e}")


if __name__ == "__main__":
    main()
