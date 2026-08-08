---
title: The Graph
date: 2026-08-07
type: note
status: active
tags:
  - tool
  - data
  - indexer
  - subgraph
source:
  - "https://thegraph.com/"
related:
  - "[[MEV]]"
  - "[[学习过的开源套利项目]]"
---

# The Graph（链上数据索引协议）

> 官方：https://thegraph.com/
> 定位：把链上原始事件/状态编译成可查询的 GraphQL 子图（subgraph），是套利 bot「数据层」的基础设施

## 是什么

The Graph 是去中心化索引协议。合约事件（Transfer/Swap/OrderFilled 等）被整理成 subgraph，开发者用 GraphQL 查询，不用自己跑全节点解析日志。

## 在套利研究中的位置

- **数据层**：和 [[MEV]] 笔记里「数据层 = 眼睛」对应——NodeDB/syncoor（BaseBuster）和 The Graph 是同一层不同实现
- **机会扫描前置**：跨池/跨链套利要先有结构化池子状态，subgraph 是最省事的取数方式
- **和开源 bot 的关系**：[[学习过的开源套利项目]] 里 bot 多自建数据层，The Graph 是更通用的替代/补充

## 使用注意

- 公共 subgraph 可能有延迟/覆盖不全，高频策略常自建索引（Geyser/自建 RPC）
- 查询频率受 Rate Limit，批量策略需评估配额（呼应 LI.FI 实测的 RPM 核算思路）
