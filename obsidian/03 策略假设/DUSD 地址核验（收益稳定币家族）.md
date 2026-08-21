---
title: DUSD 地址核验（收益稳定币家族）
date: 2026-08-21
type: note
tags:
  - onchain-arbitrage
  - strategy
---

# DUSD (Dialectic USD) 地址核验（2026-08-21 群分享）

> 来源：Paxon 分享地址 0x1e33e98af620f1d563fcd3cfd3c75ace841204ef（无上下文，按地址核验流程走）
> 归档日期：2026-08-21 ｜ 方法：ETH 公共 RPC + blockscout + CoinGecko + web

## 地址身份

- **合约名**：MachineShare（blockscout 已验证）
- **Token**：DUSD（Dialectic USD）
- **部署**：ETH 主网（creation tx 0x019b5465…），owner = BeaconProxy（0x6b006870）
- **标准 ERC20 全套**：name/symbol/decimals(18)/totalSupply/balanceOf/allowance/approve/transfer 齐全

## 协议身份：Makina Finance 的收益稳定币

- **DUSD = Makina 的 USDC 记账策略份额**（Pharos：USDC-accounted Makina strategy share with queued exits）
- 策略：跨 AMM + 货币市场的链上收益生成（institutional-grade DeFi Execution Engine）
- **价格 $1.036**（Bybit/CoinGecko 一致）——**对 USDC 溢价 3.6%**
- 市值 $264 万 ｜ 容量上限 $7500 万 ｜ **24h 交易量仅 $19.5**（流动性极差）｜ ATH $1.39

## 关键特征：溢价从哪来

1. **queued exits（排队退出）**：赎回需排队 + 实时 backlog 调整缓冲——流动性折价/排队成本 = 二级市场溢价的来源
2. **流动性极差**：24h 量 $19.5——价格几乎不被真实交易支撑，任何报价都是「名义价」
3. **收益稳定币赛道**：与 USDe/Ethena、sUSDe、USDL 同族（我们 BSC 取证见过 USDL）

## 与我们方向的关系

- **收益稳定币溢价 ≠ 可套利**：虽然名义溢价 3.6%，但 ①排队退出机制抹平套利空间（你无法即时赎回）②$19 日量的市场任何仓位都出不来 ③ATH $1.39 → $1.036 说明溢价是波动不是稳定
- 与 sUSDe/USDe（我们研究过的稳定币套利家族）同族：**「账面溢价」必须过流动性关和退出机制关**
- 方法：地址核验流程（RPC 查 code/balance → blockscout 查合约名 → CoinGecko 查市场 → Pharos 查安全画像）已跑通

## 结论

- **DUSD 是 Makina 收益稳定币的份额代币**，$1.036 溢价主要由排队退出 + 极差流动性造成
- **不可套利**（退出排队 + $19 日量）；归档为收益稳定币家族样本
- 无新研究动作；如果 Paxon 有特定意图（比如看它和哪个币的价差），请补充上下文
