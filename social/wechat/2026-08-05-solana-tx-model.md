---
title: 共学 D1：Solana 套利，从理解交易模型开始
wechat_title: 共学 D1：Solana 套利，从理解交易模型开始
digest: Solana 没有公共 mempool，套利逻辑因此完全不同。从交易路径、费用结构到三明治攻击现状，再到个人套利者真正可行的方向——CEX-DEX 价差与资金费率。
author: Paxon Qiao
wechat_author: Paxon Qiao
cover: 2026-08-05-solana-tx-model.cover.png
---

# 共学 D1：Solana 套利，从理解交易模型开始

> 链上套利残酷共学 · 第 1 天
> 2026-08-05

---

我一直以为 Solana 套利跟以太坊差不多——盯 mempool、抢跑、比谁 Gas 高。读完 Solana 交易模型才发现，这个假设全错。

**Solana 没有公共 mempool。**

这句话单独看像个技术细节，但它彻底改变了套利的底层逻辑。

---

## 以太坊 vs Solana：两条完全不同的路

以太坊的交易路径是公开的：你的交易先进入 mempool 排队，所有人都看得见。Searcher 在里面找猎物，Builder 按 Gas 价高低打包。谁给的 Gas 多，谁先进块。这是一场公开的价格战。

Solana 不同。交易通过 QUIC 协议直接发给当前 Leader，中间没有"公开等待池"。一旦离开你的节点，下一站就是 Leader。别人看不到你的交易意图。

这个差异有多大？一个数据：以太坊出块 12 秒，Solana 出块 400 毫秒——快 30 倍。

---

## "Solana Gas 几乎免费"是误解

很多人说 Solana 不需要关心 Gas——不完全对。

Base fee 确实极低，每笔交易固定 5000 lamports（约 0.000005 SOL）。但 Priority fee 不一样：这是付给当前 Leader 的附加费用，Leader 有动力在同一个 slot 内优先处理 fee 更高的交易。

再加上 Jito tip——付给 Jito Block Engine 来让你的 bundle 被 searcher 选中——你就有了两套非公开的"排序竞价"体系。

不是没有竞价，是竞价从公开变成了隐蔽。

---

## 三明治攻击真的消失了吗？

Jito 在 2023 年曾开放公共 mempool，导致 Solana 上三明治攻击泛滥。2024 年 3 月，迫于社区压力，Jito 关闭了公开 mempool。

但没有完全消失。私人 order flow、Jito bundle 内部排序、高频轮询链上状态——这些仍然给有渠道的人留了后门。只不过从"人人都能夹"变成了"有特殊渠道的人才能夹"。

对个人套利者来说，这不是主要威胁。但知道它存在，比不知道好。

---

## 个人套利者的机会在哪？

研究了各种套利类型后，我的结论是：

- 三明治攻击：几乎不可能（需要私人 order flow）
- 三角套利：理论可行，但 Jito bundle 赛道竞争最激烈
- **CEX-DEX 价差和资金费率套利**：个人最现实的方向

个人的 edge 不在速度——你的服务器跑不过专业做市商。edge 在信息差：币安和链上的价格差、不同交易所的资金费率周期、跨平台的价格不一致。这些东西不是算力问题，是信息搜集和分析的问题。

---

## 今天我还做了什么

除了读交易模型，还花了半天搭基础设施：

**链上数据脚本跑通了。** 本来打算用 Jupiter quote API 读池子价格，结果 API 被墙，v6 端点也已弃用。转而用 Helius RPC 直读 Raydium SOL-USDC 池子的 vault 余额——一次跑通。实测数据：

```
SOL Vault:  67,851.11 SOL
USDC Vault: 5,033,520.92 USDC
池子价格: 1 SOL = $74.1848
模拟 swap 1 SOL: 输出 73.9612 USDC，滑点 -0.3015%
```

滑点拆开看：0.30% 是池子手续费，只有约 0.0015% 是价格冲击。小池子里固定费率才是大头——这个认知后面做利润估算时很重要。

**Agent 基建也搭好了。** Telegram 群 + 5 个 Forum Topic（学习/策略/数据/开发/打卡），Hermes Bot 配好白名单，修了一个崩溃 bug。第一天不着急学策略，先把工具链跑顺——21 天很长，第一天省下的摩擦成本后面每一天都在受益。

---

## 明天做什么

1. 跑 Bruce 的画像 Prompt，出两周学习计划
2. 读 Orca Whirlpool 的 CLMM（集中流动性做市商）定价逻辑——价格从 sqrtPrice 算，跟恒定乘积完全不同
3. 写一个跨 DEX 价差监控 demo

---

*本文为个人学习记录，不构成投资建议。链上套利有风险，请自行评估。*
