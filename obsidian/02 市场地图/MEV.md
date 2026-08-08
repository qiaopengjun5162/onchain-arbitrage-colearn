---
title: MEV 与排序两难
date: 2026-08-05
type: note
status: 研究
tags:
  - onchain-arbitrage
  - mev
  - mempool
  - 排序
source: notes/mempool-and-ordering.md
---

# MEV 与排序两难

> 群友原话：有公共 mempool 的链，被 builder 和 MEV bot 把持得死死的；没有公共 mempool 的链，私有排序器又是个黑盒。正面竞争太激烈，得打差异化。

## 两种链，两种死法

### 有公共 mempool（Ethereum 主网）
- 交易被打包前对所有人可见 = 明牌
- builder / searcher / Flashbots 专门盯着 mempool 套利交易，用更高出价抢跑或夹击
- 竞争烈但**规则透明**，有防御工具（私有通道、anti-MEV RPC）

### 无公共 mempool（Solana、各 L2 私有排序器）
- 交易直接进入排序器/leader，外部看不到排队
- 排序器是黑盒：被插队、丢包、夹，只有「成交/没成交」结果，归因难
- Solana 特殊：无 mempool 但有 Jito bundle 拍卖，抢跑以另一种形式存在

## 对策略的含义

「正面竞争太激烈，得打差异化」——和共学核心叙事一致（速度/基建卷不过，找市场差/规则差/信息差）：

1. **不在排序层红海拼速度**：原子套利、三明治防御拼 builder 关系，个人没有 edge
2. **差异化 = 找排序竞争还没卷到的地方**：新链、新池子、跨链路径（多一次排序竞争者指数减少）、CEX-DEX 之间（跨两个排序体系）
3. **防御优先于进攻**：先用私有通道/防 MEV RPC 保护交易，再谈找机会。被 front-run 掉的不仅是利润，还有对策略有效性的判断

## 捆绑原子性：让 tx 和 target 绑在一起

> Paxon：gas 高让 target tx 和你的 tx 绑一起，要么都不成交要么都成交，结果就是全部同区块、相邻交易。

- **传统 gas 竞价**：出价高只是排序靠前，target 可能没进同区块 → 前腿买、后腿没跟上，白亏
- **Bundle 绑定（Flashbots / Jito）**：前腿+target+后腿打包成原子单元，要么全进要么全拒 → 消除单腿风险，所有 tx 同区块**相邻执行**

**为什么"相邻"重要**：三明治利润完全依赖顺序（前腿买 → target 大额买 → 后腿卖）。同区块+相邻 = 锁定价差；中间插别人交易，价差被吃掉。

- Solana 上 Jito Bundle 提供同样的原子提交机制（D11-D13 要学）
- 但 bundle 提交本身有成本（tip），leader 有最终决定权；个人用 bundle 做套利本质仍在排序层竞争

## L1 vs L2 排序机制

- **以太坊 L1**：PoS，每 12 秒按 stake 权重抽签挑 Proposer 排序；排序权 = MEV 提取权
- **Layer 2 排序器**：链下"交易收货员"，软确认 + 批量提交 L1 结算
  - 中心化（早期 OP/ARB）/ 去中心化（Espresso、Radius）/ Based Rollup（排序权还 L1）
  - 中心化风险：单点故障 + 审查能力；应对 = **forced inclusion**（直接发 L1 绕过）
  - **软确认 ≠ 最终确认**：跨链套利若基于软确认决策，承担 L1 回滚风险

## 连接（双链）

- [[套利第一性原理框架]] — 原子锁定是四道检查之一
- [[套利策略全景]] — MEV 在策略类型里的定位
- [[LI.FI 跨链可执行价差 120 轮实测]] — 跨链路径复杂度溢价
- [[学习过的开源套利项目]] — EVM/Solana/Sui 三链 MEV 通道对照
