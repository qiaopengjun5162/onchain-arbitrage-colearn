---
title: VolaSet 协议观察与 Solana 官方两帖
date: 2026-08-21
type: note
tags:
  - onchain-arbitrage
  - strategy
---

# VolaSet 协议观察 + Solana 官方两帖（2026-08-21 群分享）

## 1. Swing → VolaSet：波动率结算基础设施化（观察类）

> 来源：https://x.com/ChainBetter/status/2090432719876436248（Ray，344 followers，观察分析帖）
> 归档日期：2026-08-21 ｜ 核验：swing.xyz 存在（Tilda 403）+ SwingHook = fair onchain volatility 基础设施

### 内容
- Swing 把 Volatility Settlement 机制抽象成独立协议 VolaSet：任何 ERC-20 可创建自己的 Pool（无需改 token 合约）
- 四类角色：Pool Creator（付创建费+设 Pool Edge）/ LP（提供流动性+按份额承担结算）/ Participant（选 pool+金额+0.5x-5x volatility factor）/ Frontend Operator（构建产品收 frontend fee，不托管资产）
- **Pool Edge 0%-5% = Pool 的长期统计优势**——结算结果直接影响 Pool 资产和 LP 份额
- 协议收入：Pool Creation Fee + Settlement Protocol Fee

### 定性
- **核验**：真实（swing.xyz 存在）；但帖子是个人分析非官方公告，344 followers 观察帖
- **本质**：这是「链上波动率交易」基础设施——Pool Edge 0-5% 类似做市商的统计优势，参与者付波动率溢价，LP 赚统计优势
- **与我们方向**：与 Hayden 配对 AMM / Polymarket LP 同族（卖保险模型）；Pool Edge 可视为「买保险者付费」的显式参数化
- **暂无实盘意义**：早期协议，流动性未知；归档为「卖保险家族」新样本

## 2. @solana 官方：Solana School Fall Class（2026-08-21）

> https://x.com/solana/status/2090621091135815696（501 likes）

- 7 周线下实战课（8/31 - 10/16），面向所有人开放申请
- 每周真实 program 交付 + 嘉宾讲座 + DevRel 办公时间 + Demo Day
- 申请：https://luma.com/jy1g8k90

### 与我们关系
- Solana 开发能力建设（我们主线=Solana 套利，Rust 双实现）——课程与求职相关，可申请
- 时间：8/31 开始 = 共学 D18 之后，时间不冲突

## 3. @solana 官方 BREAKING：韩国新韩资管 KRW 代币化基金（2026-08-21）

> https://x.com/solana/status/2090609313869906111（565 likes）

- 韩国 Shinhan Asset Management 在 Solana 建 KRW 代币化基金，**模型参照 BlackRock BUIDL**
- 四方 MOU：Solana Foundation + etherfuse + Orca
- 目标市场：RWA 代币化 $36B（今日）→ BCG 预测 $30T（2030）

### 与我们关系（币股方向直接利好）
- **BUIDL 模式 = 链上国债/货币市场基金**：KRW 版本上 Solana = 亚洲资金入链
- RWA $36B → $30T 叙事 = 我们🥇币股方向（闭市漂移/预上市）的宏观底座
- etherfuse（代币化基础设施）+ Orca（DEX）组合 = Solana RWA 生态扩张信号
- 与我们 D17 已核验的 SEC/DTCC 已批（币股方向利好）同一条线：**机构资金入 Solana = 流动性池变深 = 套利机会类型变化**

## 结论

- VolaSet：卖保险家族新样本（观察级，无实盘意义）
- Solana School：能力建设机会（与求职相关）
- 新韩 RWA：币股方向宏观利好 +1（BUIDL 模式入亚）
- 均无紧急动作；归档
