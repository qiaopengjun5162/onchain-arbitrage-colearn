---
title: Ramp × x402：Agent 支付接入企业账本
date: 2026-08-21
type: note
tags:
  - onchain-arbitrage
  - tool
---

# Ramp × x402：Agent 支付接入企业账本（@solana 官方，2026-08-21 群分享）

> 来源：https://x.com/solana/status/2090470972008943806（@solana 官方，486 likes）
> Quote：Teddy Riker（Ramp）
> 归档日期：2026-08-21 ｜ 类型：基础设施新闻（Agent×Payments 直接相关）

## 内容

- **Ramp 客户现在可以给 agent 钱包注资，让 agent 通过 x402 在 Solana 上支付**
- x402 已结算 **3500 万+ 笔交易**——这是第一次触碰企业账本（corporate ledger）
- 三个能力：
  1. Provision & fund agent wallets（创建+注资 agent 钱包）
  2. Empower agents to buy via x402 on Solana（agent 自主支付）
  3. Ledgering + spend controls（企业级记账与支出控制，开箱即用）

## 与我们关系（🔴 直接相关：Paxon 的 Agent×Payments Hackathon 方向）

- **x402 = HTTP 402 Payment Required 标准化**（agent 支付协议）：Agent 通过标准 HTTP 状态码完成支付 = 「agent 是支付主体」的基础设施
- **可审计结算落地**：Paxon 构想「带路由层/多模型调度/可审计结算的 AI 基础设施」——Ramp 这次把「企业级记账+支出控制」接进 agent 支付 = 用户构想的「可审计结算」层正在被基础设施化
- **3500 万+ 笔交易** = x402 生态已非概念验证，真实流量存在
- 信号：合规路径（Ramp 是法币入金合规商）打通 = Agent 支付从「链上玩具」走向「企业采购」——这与 SEC/DTCC 已批（币股）、新韩 RWA 同一条「机构资金入链」主线

## 结论

- 基础设施新闻，已核验（@solana 官方账号 + 3500 万笔声称）
- **对 Paxon 的 Agent×Payments 方向：x402/Ramp 是「可审计结算」层的现成组件**——做 Hackathon 架构时直接参考（不必自建结算层，接 x402 + 企业账本即可）
- 归档为 Agent×Payments 方向素材
