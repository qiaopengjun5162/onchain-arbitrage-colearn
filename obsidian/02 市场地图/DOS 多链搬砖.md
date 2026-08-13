---
title: DOS 多链搬砖
date: 2026-08-11
type: note
status: 监控中
tags:
  - onchain-arbitrage
  - cross-chain
  - 价差套利
  - offt
  - layerzero
source: notes/dos-bridge-arb-20260811.md
related:
  - 跨链报价成本结构 L0006
  - 跨所价差套利 Demo 决策
  - 套利成本模型
---

# DOS 多链搬砖

> 三步落地：找多链币 → 监控多链价格 → 判断价差搬砖。只读调研 + paper 模拟，实盘须单独批准。

## 桥核验（已确认）

- DOS = LayerZero V2 OFT：BSC OFT ↔ ETH OFTAdapter ↔ ETH 原生 ERC20；Endpoint V2；peer 双向确认
- 桥 1:1 无代币费；桥费 ETH→BSC ~$0.02、BSC→ETH ~$0.69（BNB gas 贵）；到账 1-3 分钟
- 假币清单：BSC/ETH/Base 多处同名诱饵，只认白名单合约

## 找多链币（实证）

- **「BSC+ETH 双链都深」的多链币极度稀缺**：ZRO/ALT/W/PENDLE/ENA 在 BSC 全无主流 USDT 池
- DOS 是特殊案例：新上币窗口（Gate/OKX/Upbit 密集上币）驱动 BSC 侧流动性（BSC 主池 $93 万 vs ETH 浅池 $1.2 万）
- 找币正确过滤条件 = 「两链池深度都够」，不是「币是否多链」

## 监控与判定（实测快照）

| 配对 | 毛价差 | 净价差 | 方向 | 结论 |
|---|---|---|---|---|
| DOS BSC↔ETH | 136bps | **7.6bps** | BSC→ETH | NO-GO（阈值 300bps） |

- 读取链路：RPC 直读 V3 池 slot0（sqrtPriceX96 → 价格），与 Gate ticker 精确一致（0.5292 vs 0.529）
- **BSC→ETH 方向桥费 $0.69 是主要杀手**；ETH→BSC 方向（$0.02）若 ETH 折价会好很多
- 触发条件：ETH 侧相对 BSC 折价 >3% 且走 ETH→BSC 便宜方向 → 才有肉

## 风险红线

假币/克隆池、ETH 浅池滑点、桥延迟 vs 价差寿命、CEX 提现开放时间、插针

## 下一步

- [ ] 监控接 cron watchdog（净价差 ≥300bps 告警）
- [ ] 找多链币自动化：新上币公告 + 双链池深度检查自动加入监控
- [ ] 0xd21258ed 地址取证（可能是 DOS 搬砖实证样本）
