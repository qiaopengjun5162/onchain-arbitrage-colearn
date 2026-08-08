---
title: LI.FI
date: 2026-08-07
type: note
status: active
tags:
  - tool
  - bridge
  - dex-aggregator
  - execution
source:
  - "https://li.fi/"
  - "https://docs.li.fi/"
  - "https://x.com/brucexu_eth/status/2085022891339554855"
related:
  - "[[LI.FI 跨链可执行价差 120 轮实测]]"
  - "[[套利第一性原理框架]]"
  - "[[套利成本模型]]"
---

# LI.FI（跨链执行层 / 桥+DEX 聚合）

> 官方：https://li.fi/ ｜ Docs：https://docs.li.fi/
> 定位：跨链套利与 Agent 集成的执行层入口（发现价差 → 调用 quote → 路由执行）

## 是什么

LI.FI 把**跨链桥 + DEX 聚合**打包成统一 API：一次 `/v1/quote` 请求返回跨链路径（含桥费、Gas、滑点）。是「发现价差之后真正去执行」的管道，不是价格源本身。

## 成本结构（实测口径）

- **LI.FI 固定费 25 BPS**（Portal 注册时显示 `LI.FI fee: 25 BPS - FIXED`）
- 真实案例总成本 ≈ **27.5 BPS**（25bps LI.FI + Gas）——套利价差常被这个磨损吃掉
- Break-even 公式：最低所需价差 = 桥/DEX 费 + 双链 Gas + 滑点 + Price Impact + 延迟失败成本

## 与本项目的关系

- 长文《从发现价差到执行》：本人 X 发布，讲接入 LI.FI 实现跨链套利 + AI Agent 集成（MCP Server 配置）
- 120 轮报价级实测：量化「报价≠成交」，见 [[LI.FI 跨链可执行价差 120 轮实测]]
- Portal 注册：integration string 永久不可改（本项目用 `paxon`），API key 不入库（存 `.env` + `.gitignore`）
- 呼应 [[套利第一性原理框架]]：成本地板优先于波动率，先测同链往返地板

## 注册要点（安全红线）

- integration name 可改，string 永久不可改
- 钱包绑定（referrer 返佣）研究阶段可跳过
- API key 绝不截图发人、绝不入库
