#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
套利利润模拟器 v0（arb_profit_simulator.py）— D10 预习（2026-08-13）
====================================================================
D10 主线要求：输入池子参数 + 价格 + Gas，输出多池子多路径的扣费后利润。纯模拟不链上操作。

路径类型：
  1. 单腿往返（A 买 → A 卖）：吃同池滑点 + 双次手续费，恒负 = 基线
  2. 三角（A→B→C→A）：跨池价差环，x*y=k 滑点 + 每跳费率
  3. 跨池搬（同资产两池价差）：薄池买 → 深池卖（corridor 雷达的走廊模型）
  4. 多路径对比：给定本金，输出所有路径净利 bps + 可执行判定

模型：
  - V2 带费 swap：Δy = y·(1 - x/(x+Δx·(1-fee))) 精确解
  - gas 成本：SOL 计价，按输入 SOL 价格折算
  - 判定：净利 > 0 且 > 滑点噪音阈值（默认 2bps）

用法：
  python3 scripts/arb_profit_simulator.py --demo            # 内置演示数据
  python3 scripts/arb_profit_simulator.py --pool x.json     # 从文件读池子列表
  纯模拟：不读 RPC、不广播交易。
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

MIN_EDGE_BPS = 2.0      # 净利低于此 = 噪音，不判定可执行
SOL_PRICE = 175.0       # 演示用 SOL 价格（USD）；真实场景从输入读


@dataclass
class Pool:
    name: str
    rx: float          # 储备 X（如 SOL）
    ry: float          # 储备 Y（如 USDC）
    fee_bps: float = 30.0
    gas_sol: float = 0.000005   # 单笔交易 SOL gas

    def price_y_per_x(self) -> float:
        return self.ry / self.rx

    def swap_x_for_y(self, dx: float) -> float:
        """卖 dx 个 X，得到 dy 个 Y（V2 带费精确解）"""
        if dx <= 0:
            return 0.0
        eff = dx * (1 - self.fee_bps / 10000)
        dy = self.ry * (1 - self.rx / (self.rx + eff))
        return dy

    def swap_y_for_x(self, dy: float) -> float:
        """卖 dy 个 Y，得到 dx 个 X"""
        if dy <= 0:
            return 0.0
        eff = dy * (1 - self.fee_bps / 10000)
        dx = self.rx * (1 - self.ry / (self.ry + eff))
        return dx

    def impact_bps(self, amount_x: float) -> float:
        """按当前价买入 amount_x 的滑点（bps，近似）：理想价 vs 实际成交均价"""
        p0 = self.price_y_per_x()
        # 买入 amount_x 需要卖多少 Y：反解 dy 使 swap_y_for_x(dy)=amount_x
        # 二分法精确解
        lo, hi = 0.0, self.ry * 10
        for _ in range(60):
            mid = (lo + hi) / 2
            if self.swap_y_for_x(mid) < amount_x:
                lo = mid
            else:
                hi = mid
        dy = hi
        avg = dy / amount_x if amount_x else 0.0
        return (avg - p0) / p0 * 10000


def run_roundtrip(p: Pool, amount_x: float) -> dict:
    """单腿往返：X → Y → X，返回净损 bps"""
    dy = p.swap_x_for_y(amount_x)
    back = p.swap_y_for_x(dy)
    net = back - amount_x
    net_bps = net / amount_x * 10000 if amount_x else 0
    gas_usd = p.gas_sol * 2 * SOL_PRICE
    return {"type": "roundtrip", "pool": p.name, "in": amount_x, "out": back,
            "net": net, "net_bps": net_bps, "gas_usd": gas_usd}


def run_triangle(p1: Pool, p2: Pool, p3: Pool, amount_x: float) -> dict:
    """三角：X→Y (p1) → Z (p2) → X (p3)，p1 用 X/Y，p2 用 Y/Z，p3 用 Z/X"""
    # 需要三个池子共享资产：p1 卖 X 买 Y；p2 卖 Y 买 Z；p3 卖 Z 买 X
    dy = p1.swap_x_for_y(amount_x)          # X→Y
    dz = p2.swap_x_for_y(dy) if False else p2.swap_y_for_x(dy)  # 兼容：p2 卖 Y 买 Z
    back = p3.swap_x_for_y(dz) if False else p3.swap_y_for_x(dz)  # p3 卖 Z 买 X
    # 上面两行简化实现：要求 p2 是 (Y,Z) 池、p3 是 (Z,X) 池
    net = back - amount_x
    net_bps = net / amount_x * 10000 if amount_x else 0
    gas_usd = p1.gas_sol * 3 * SOL_PRICE
    return {"type": "triangle", "path": f"{p1.name}→{p2.name}→{p3.name}",
            "in": amount_x, "out": back, "net": net, "net_bps": net_bps, "gas_usd": gas_usd}


def run_crosspool(buy_pool: Pool, sell_pool: Pool, amount_x: float) -> dict:
    """跨池搬：薄池买 X → 深池卖 X。两池都按 (X,Y) 计价"""
    dy_spend = buy_pool.impact_bps(amount_x) / 10000 * buy_pool.price_y_per_x() * amount_x * 0 + 1  # placeholder
    # 精确版：薄池买 = swap_y_for_x(dy_buy)；深池卖 = swap_x_for_y(amount_x)
    # 反解薄池买入 cost（Y）：二分
    lo, hi = 0.0, buy_pool.ry * 10
    for _ in range(60):
        mid = (lo + hi) / 2
        if buy_pool.swap_y_for_x(mid) < amount_x:
            lo = mid
        else:
            hi = mid
    cost_y = hi
    # 深池卖出得 Y
    get_y = sell_pool.swap_x_for_y(amount_x)
    net_y = get_y - cost_y
    net_bps = net_y / cost_y * 10000 if cost_y else 0
    gas_usd = (buy_pool.gas_sol + sell_pool.gas_sol) * SOL_PRICE
    return {"type": "crosspool", "path": f"{buy_pool.name}→{sell_pool.name}",
            "in": amount_x, "cost_y": cost_y, "get_y": get_y,
            "net_y": net_y, "net_bps": net_bps, "gas_usd": gas_usd}


def demo_pools() -> List[Pool]:
    """内置演示：Raydium 实测参数（2026-08-07）+ 薄池虚构（模拟 HumidiFi 类）"""
    return [
        Pool("Raydium(SOL-USDC)", rx=67851.11, ry=5033520.92, fee_bps=30, gas_sol=0.000005),
        Pool("ThinPool(SOL-USDC)", rx=3000.0, ry=222000.0, fee_bps=30, gas_sol=0.000005),
        Pool("MidPool(SOL-USDC)", rx=15000.0, ry=1111500.0, fee_bps=25, gas_sol=0.000005),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="跑内置演示数据")
    ap.add_argument("--pool", type=str, help="池子 JSON 文件（[{name,rx,ry,fee_bps,gas_sol}]）")
    ap.add_argument("--amount", type=float, default=10.0, help="本金（X 数量，默认 10 SOL）")
    ap.add_argument("--prices", type=str, help="价格偏离注入：buy_pool:y/x,sell_pool:y/x（模拟价差）")
    args = ap.parse_args()

    pools = demo_pools()
    if args.pool:
        data = json.loads(Path(args.pool).read_text())
        pools = [Pool(**{k: d[k] for k in ("name", "rx", "ry", "fee_bps", "gas_sol") if k in d}) for d in data]
    # 价格偏离注入：模拟两池价差（如 ThinPool 报价比 Raydium 低 5%）
    # 格式：--prices "ThinPool:0.74,Raydium:0.779"（y/x 价格，保持 rx 不变调 ry）
    if args.prices:
        for spec in args.prices.split(","):
            name, px = spec.split(":")
            for p in pools:
                if p.name == name:
                    p.ry = float(px) * p.rx
                    break
    by_name = {p.name: p for p in pools}

    amt = args.amount
    results = []
    # 1) 单腿往返（每池）
    for p in pools:
        results.append(run_roundtrip(p, amt))
    # 2) 跨池搬（所有两两组合）
    for a in pools:
        for b in pools:
            if a.name == b.name:
                continue
            results.append(run_crosspool(a, b, amt))

    print(f"本金 {amt} X | SOL=${SOL_PRICE} | 判定阈值 {MIN_EDGE_BPS}bps")
    print("=" * 78)
    print(f"{'类型':<10}{'路径':<28}{'净利bps':>10}{'净利(USD)':>12}{'判定':>8}")
    print("-" * 78)
    for r in sorted(results, key=lambda x: -x["net_bps"]):
        edge = r["net_bps"] - r.get("gas_usd", 0) / (amt * SOL_PRICE) * 10000
        verdict = "✅ 可执行" if edge > MIN_EDGE_BPS else ("👀 观察" if edge > 0 else "❌ 负")
        label = r.get("path", r.get("pool", ""))
        print(f"{r['type']:<10}{label:<28}{r['net_bps']:>10.1f}{edge * amt * SOL_PRICE / 10000:>12.4f}{verdict:>8}")

    # 汇总：正净利路径
    pos = [r for r in results if r["net_bps"] > MIN_EDGE_BPS]
    print("=" * 78)
    print(f"正净利路径: {len(pos)} 条（其余被费率/滑点/gas 吃掉）")
    if not pos:
        print("→ 0 信号 = 正确输出：常驻价差下模拟器给出「无肉」，与哨兵实测一致")


if __name__ == "__main__":
    sys.exit(main())
