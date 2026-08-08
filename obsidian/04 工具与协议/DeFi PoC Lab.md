---
title: DeFi PoC Lab
date: 2026-08-07
type: note
status: active
tags:
  - tool
  - mev
  - security
  - research
source:
  - "https://starkxuns-organization.gitbook.io/defi-poc-lab/amm-specific-attacks/mev-gong-ji"
related:
  - "[[MEV]]"
  - "[[套利策略全景]]"
---

# DeFi PoC Lab（MEV 攻击研究）

> 文档：https://starkxuns-organization.gitbook.io/defi-poc-lab/amm-specific-attacks/mev-gong-ji
> 定位：AMM 专项攻击 / MEV 手法的研究资料库（Proof of Concept 实验室）

## 是什么

一个系统整理 DeFi/AMM 攻击手法的研究型 GitBook，覆盖三明治、套利、清算等 MEV 相关攻击的 PoC 与原理。

## 在套利研究中的位置

- 和 [[MEV]] 笔记互补：MEV 笔记讲机制（公共 mempool vs 私有排序器、捆绑原子性），DeFi PoC Lab 给具体攻击手法与代码级 PoC
- 和 [[套利策略全景]] 里「MEV/三明治」类策略对应：理解对手在做什么，才能设计不被吃的对冲
- **研究/学习用**：PoC 是理解机制的工具，不是实盘脚本——本项目铁律区分研究/模拟/实盘

## 使用注意

- 仅用于理解攻击面与防御（如学三明治以避开被夹），不用于主动攻击
- 配合 [[套利第一性原理框架]] 的「机会为什么还存在」：很多 MEV 机会来自协议规则摩擦
