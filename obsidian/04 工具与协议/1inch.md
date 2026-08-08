---
title: 1inch
date: 2026-08-07
type: note
status: active
tags:
  - tool
  - dex-aggregator
  - limit-order
source:
  - "https://zh.blog.1token.tech/crypto-fund-101-funding-fee-arbitrage-strategy/"
  - "https://1inch.io/"
related:
  - "[[跨所资金费率套利]]"
  - "[[套利策略全景]]"
---

# 1inch（DEX 聚合器 + 限价单协议）

> 资金费套利策略文：https://zh.blog.1token.tech/crypto-fund-101-funding-fee-arbitrage-strategy/
> 定位：同链 DEX 聚合路由 + 限价单（Fusion）协议，套利执行层候选

## 是什么

1inch 是老牌 DEX 聚合器，把多个 AMM 的流动性拆单路由以最小化滑点；另有 Fusion 限价单协议（无需 Gas 的挂单）。

## 在套利研究中的位置

- 同链 DEX 套利执行层：和 [[套利策略全景]] 里「DEX 间套利」对应——找同链不同池价格差后用 1inch 路由执行
- 和 LI.FI 互补：LI.FI 管跨链，1inch 管同链
- 资金费率套利：1Token 文章讲用现货+合约组合做资金费套利，1inch 可作为现货腿执行通道
- 对照研究：聚合器竞品见 KyberSwap（kyberswap.com）/ 0x（0x.org）

## 使用注意

- Fusion 限价单有履约不确定性（resolver 接单），非原子——呼应 [[MEV]] 非原子执行风险
- 聚合路由仍有价格影响，大额需测同链往返地板
