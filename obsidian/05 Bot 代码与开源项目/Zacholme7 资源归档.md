---
title: Zacholme7 资源归档
date: 2026-08-06
type: note
status: 学习（未部署）
tags:
  - onchain-arbitrage
  - bot
  - mev
  - rust
  - 资源清单
source: notes/zacholme7-resources.md
---

# Zac Holme (Zacholme7) — Rust MEV/套利开发者资源

来源：https://github.com/Zacholme7
Paxon 学习过这位大佬的公开代码，对套利有懵懂概念，但只是学习未实际部署。

## 个人简介

Zac Holme，Rust 生态 MEV/套利开发者，sigp（SSV 协议）成员。作品集中在以太坊/Base 生态的套利机器人和链上数据基础设施。

## Pinned 仓库

| 仓库 | 说明 | Stars |
|---|---|---|
| PoolSync | DeFi 池扫描器 | 85 |
| BaseBuster | Base L2 套利机器人 | 80 |
| sigp/anchor | SSV 协议的 Rust 实现 | 68 |
| NodeDB | Revm DB，从 Reth DB 拉最新状态 | 43 |
| syncoor | EVM 链历史+实时事件日志同步 | 8 |
| Mev-aholic | MEV 资源清单（eth.md + sol.md） | 78 |

## BaseBuster 要点

- Base L2 套利机器人，"mid-tier"
- **作者自述**："This bot has bought me a couple coffees, but my hourly wage would be like 0.02$ an hour. This is not a infinite money glitch!!!"
- 已移除部分 alpha，当前不编译，但代码里大量有价值信息

> 诚实披露：即使是大佬的实战 bot，时薪也只有 0.02 美元——套利不是印钞机，这是最好的现实教育。

## Mev-aholic 资源清单（核心）

- **Solana (sol.md)**：9 个套利 bot（0xNineteen/solana-arbitrage-bot、ARBProtocol/solana-jupiter-bot、egaotan/solana-arbitrage …）+ 3 个清算 bot（mrgnlabs/eva01、egaotan/solana-liquidate、01protocol/zo-keeper）
- **Ethereum (eth.md)**：套利（flashbots/simple-arbitrage、degenbot …）/ 三明治 Sando（libevm/subway、rusty-sando …）/ 清算（yield-liquidator、aave-liquidation …）/ 符号执行（hevm、manticore …）/ 工具（alloy、revm、reth、artemis …）
- **Sleuthing 工具**：eigenphi.io、libmev.com、mevwatch.info、zeromev.org、relayscan.io

## 概念框架：从代码反推的套利 bot 构成

1. **数据层（NodeDB + syncoor）= 眼睛**：实时拿到链上状态和事件日志
2. **机会扫描（PoolSync）= 雷达**：周期比对各池价格，发现偏离即候选
3. **套利执行（BaseBuster）= 手**：构造原子交易，抢在别人前面上链
4. **MEV 深水区（Mev-aholic）= 进阶手段**：三明治/back-run/清算，拼 mempool 可见性+排序权

**关键认知**：即使实战 bot 时薪也 0.02 美元——技术能跑通 ≠ 有正收益。这层现实预期比代码更值钱。

**与本项目主线对应**：
- LI.FI 主线 ≈ 跨链版"机会扫描+执行"
- Solana 主线 ≈ 理解"执行层"（Jito/MEV/bundle/priority fee）
- 当前研究向、未实盘，和 BaseBuster"咖啡级收益"现实一致

## 连接（双链）

- [[学习过的开源套利项目]] — 三项目对照总表
- [[MEV]] — 三链 MEV 通道对照
- [[套利第一性原理框架]] — 四层概念框架
- [[套利策略全景]] — bot 实现对应策略类型
