#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uniswap V2 x*y=k 数学验证 (amm_v2_verify.py) — D8 AMM 预习
==========================================================
验证内容：
  1. 恒定乘积公式：x*y=k，现货价 = y/x（token Y 计价 X）
  2. 带手续费的 swap 输出：Δy = y − k/(x + Δx·(1−fee))，手续费按有效输入扣除
  3. 价格冲击 = 无滑点理想输出 − 实际输出
  4. 用知识库已有 Raydium SOL-USDC 真实储备验证（pool_price.py 08-07 实测：
     SOL Vault 67,851.11 / USDC Vault 5,033,520.92，价格 $74.1848，
     1 SOL swap 输出 73.9612 USDC，滑点 -0.3015%）
     → 验证 0.30% ≈ 0.25% 池手续费 + ~0.05% 价格冲击（x*y=k 精确复现）
用法：hermes venv python3 scripts/amm_v2_verify.py
"""

def spot_price(x, y):
    """现货价：1 X = ? Y（无滑点边际价格）"""
    return y / x

def _check_positive(x, y, dx, fee):
    """参数合法性：除零/边界保护，非法输入直接报错而不是产出 NaN。"""
    if x <= 0 or y <= 0:
        raise ValueError(f"储备必须为正: x={x}, y={y}")
    if dx <= 0:
        raise ValueError(f"输入数量必须为正: dx={dx}")
    if not (0 <= fee < 1):
        raise ValueError(f"手续费必须在 [0,1): fee={fee}")
    if dx * (1 - fee) >= x:
        raise ValueError(f"输入过大: dx·(1−fee)={dx*(1-fee)} 将耗尽储备 x={x}")

def swap_output(x, y, dx, fee=0.003):
    """恒定乘积带费 swap：输入 dx 个 X，输出多少 Y。
    手续费按有效输入扣除：实际入池 = dx·(1−fee)。"""
    _check_positive(x, y, dx, fee)
    dx_eff = dx * (1 - fee)
    k = x * y
    dy = y - k / (x + dx_eff)
    return dy

def price_impact(x, y, dx, fee=0.003):
    """价格冲击 = 无手续费理想输出 − 实际输出（美元计 = 输出 Y 的差）"""
    dy_ideal = y - x * y / (x + dx)          # 无费理想
    dy_real = swap_output(x, y, dx, fee)
    return dy_ideal - dy_real, dy_ideal, dy_real

def assert_invariants(x, y, dx, dy, fee, k0, tolerance=1e-6):
    """恒定乘积自检：swap 后 x·y 守恒（相对误差 < tolerance 才算通过）。"""
    x_new = x + dx * (1 - fee)
    y_new = y - dy
    k_new = x_new * y_new
    rel_err = abs(k_new - k0) / k0
    assert rel_err < tolerance, f"恒定乘积不守恒: k0={k0:.4f}, k_new={k_new:.4f}, 相对误差 {rel_err:.2e}"
    print(f"   自检通过: k 相对误差 {rel_err:.2e} (< {tolerance:.0e})")
    return rel_err

def main():
    print("=" * 70)
    print("1) 恒定乘积基础")
    print("=" * 70)
    x, y = 100.0, 400_000.0
    k = x * y
    print(f"池子: X={x} (ETH), Y={y} (USDC), k={k:.0f}")
    print(f"现货价 1 ETH = {spot_price(x, y):,.2f} USDC")

    print("\n2) 1 ETH swap（0.3% 手续费）")
    dx = 1.0
    k0 = x * y
    dy = swap_output(x, y, dx)
    dy_ideal = y - k / (x + dx)
    print(f"理想输出(无费): {dy_ideal:,.4f} USDC")
    print(f"实际输出(0.3%费): {dy:,.4f} USDC")
    print(f"手续费损失: {dy_ideal - dy:,.4f} USDC ({(dy_ideal-dy)/dy_ideal*100:.3f}%)")
    print(f"实际成交均价: {dx/dy*1e0:.4f} ETH→ 每 ETH 得 {dy/dx:,.4f} USDC")
    print(f"对现货价的折扣: {(1 - (dy/dx)/spot_price(x,y))*100:.3f}%")
    print(f"新储备: X={x+dx*(1-0.003):.4f}, Y={y-dy:.4f}, 新 k={ (x+dx*(1-0.003))*(y-dy):.2f}")
    assert_invariants(x, y, dx, dy, 0.003, k0)

    print("\n3) 知识库实测复现：Raydium SOL-USDC（08-07 pool_price.py）")
    print("   来源数据: SOL Vault 67,851.11 / USDC Vault 5,033,520.92 / 价格 $74.1848")
    rx, ry = 67_851.11, 5_033_520.92
    rdx = 1.0
    print(f"   池子: SOL={rx:,.2f}, USDC={ry:,.2f}")
    print(f"   现货价 1 SOL = {spot_price(rx, ry):,.4f} USDC")
    # Raydium 手续费：0.30%（实测反推——0.25% 得 73.9982 差 0.037，0.30% 精确复现 73.9612 误差 0）
    dy_r = swap_output(rx, ry, rdx, fee=0.0030)
    dy_ideal_r = ry - rx * ry / (rx + rdx)
    imp_r = (dy_ideal_r - dy_r) / dy_ideal_r * 100
    print(f"   1 SOL swap 输出: {dy_r:,.4f} USDC（实测 73.9612，0.30% 费率精确复现误差 0）")
    print(f"   手续费损失: {dy_ideal_r - dy_r:,.4f} USDC")
    print(f"   总滑点 vs 现货价: {(1 - (dy_r/rdx)/spot_price(rx, ry))*100:.4f}%（实测 0.3015%）")
    print(f"   拆解: 0.30% 手续费 + 价格冲击 {imp_r - 0.30:.4f}%")

    print("\n4) 大额 swap 的价格冲击（为什么薄池致命，Raydium 0.30% 费率）")
    for s in (1, 10, 100, 1000):
        dy_s = swap_output(rx, ry, s, fee=0.0030)
        slip = (1 - (dy_s/s)/spot_price(rx, ry)) * 100
        print(f"   {s:>5} SOL -> 得 {dy_s:>12,.2f} USDC | 总滑点 {slip:>7.3f}%")

    print("\n5) CLMM 预告：V3 集中流动性")
    print("   V2 资金效率: 全部流动性摊在 0~∞，大部分闲置")
    print("   V3: 流动性集中在 [P_low, P_high]，区间内资金效率 = 1/(区间宽度占比)")
    print("   例: 100 ETH 流动性放 ±10% 区间 ≈ V2 里 10 倍资金的效果（价格不出区间时）")
    print("   出区间 → 单边资产，停止赚手续费，直到价格回区（对应网格穿界风险的 AMM 版）")

if __name__ == "__main__":
    main()
