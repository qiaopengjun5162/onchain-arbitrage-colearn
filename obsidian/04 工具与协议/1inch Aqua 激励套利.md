---
title: 1inch Aqua 激励套利
date: 2026-08-19
type: note
status: active
tags:
  - tool-protocol
  - incentive-arbitrage
  - liquidity-mining
  - event-driven
source:
  - "https://x.com/NeoWeb3Nova/status/2089920914661982670"
related:
  - "[[跨所资金费率套利]]"
  - "[[OKX 闪赚对冲]]"
  - "[[知识图谱 v1 · 阶段二收官]]"
---

# 1inch Aqua 激励套利

一句话结论：1inch Aqua Maker / LP Incentive Program 不是撸空投也不是价差套利，而是**激励套利（Incentive Arbitrage）**——协议为冷启动花真金白银补贴「真实成交量」，玩家优化头寸去捕获补贴。套利的不是币价，是协议的补贴。

## 核心机制

| 层 | 机制 | 关键点 |
|---|---|---|
| 资产层 | 资产留在钱包，allowance 支撑多个做市 Position | 只有真实 Swap 命中报价才移动资产 |
| 收益层 | Swap Fee + 活动补贴 | 基础奖励池 1000 万枚 1INCH + 最多 50 万 USDC DAO 激励 |
| 分配层 | **按 processed volume 分配，不是 parked TVL** | 成交越多 → 激励越多 |
| 防刷层 | wallet cap + taker-maker exclusion + wash-trading filter | 奖励率高到自交易可获利 → 市场可被暂停 |

## 关键数字

- @w3_888：7 月底入场，目标「撸 10 万 U」；8/11 自述两周收益超 3 万 U（自述，gross vs net 存疑）
- 官方临界点：【协议奖励 > 制造成交量的成本】——1inch 知道存在机制套利者
- 8/2 该玩家「血泪教训」：资产价格核对问题，错误创建 LP Pair 会亏钱
- 风险：价格变化 / Impermanent Loss / Inventory Risk / 合约风险；价格变化可能让 LP 最终全部持有某一种资产

## 方法论贡献

- 分类谱系：Price Arbitrage（最底层）← Incentive Farming ← **Incentive Arbitrage**（本案例位置）
- 两类 LP 对比：普通撸毛党拿 $500 Reward 但 Inventory Loss −$800 净亏；激励套利玩家按奖励池/竞争/成交量/inventory risk 动态调仓
- 「无风险」说法被作者自己纠正：低风险 ≠ 无风险

## 下一步

- 确认 1inch Aqua 当前支持链/Pair 奖励池状态
- 「活动补贴期雷达」候选扩到 1inch Aqua（与 OKX 闪赚、Lighter 积分同类监控项）
