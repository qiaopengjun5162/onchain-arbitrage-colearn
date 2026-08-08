# 项目投研完整方法论：工具清单 + 实施流程（Paxon 分享）

> 来源：Paxon 群分享（2026-08-08）
> 关联：`notes/jason-chen-investment-research-methodology-20260808.md`（四层投研模型）、`templates/research-note.md`、`templates/strategy-hypothesis.md`

## 一、项目投研常用工具（六大类）

### 1. 基础信息与行情数据
- CoinMarketCap / DeBank / CoinGecko / TradingView / DeFi Llama
- 媒体：CoinDesk / The Block / CryptoPotato

### 2. 链上数据与分析
- 简单 SQL 语法 + 可视化报表工具
- 区块链浏览器：Etherscan / BscScan / PolygonScan / TronScan
- 专业分析：**Dune / Nansen / Glassnode / Messari / Footprint Analytics**

### 3. 项目代码与安全分析
- GitHub / GitLab：源代码、Commit 频率、贡献者数量、开源程度
- 审计报告：**CertiK / PeckShield / SlowMist**（合约安全性）
- 漏洞赏金：**Code4rena / Immunefi / Bug Bounty**（公开审计、安全评估）

### 4. 社区与社交媒体
- Twitter / Telegram / Discord / Reddit
- Social Blade / Twitter Audit（账号真实度）
- GitHub Community / Issues（开发者活跃度）

### 5. 投资与资金动向
- 募资平台：ICO Drops / CoinList / DAO Maker
- 融资背景：Crunchbase / LinkedIn
- 大额流动：Whale Alert / WhaleStats

### 6. 研究报告与专家观点
- 研究机构报告 / Podcasts / YouTube 专家频道 / 社区 AMA

## 二、完整投研实施过程（八步）

### Step 1：明确研究范围与目标
- 确定方向：公链 / DeFi / NFT / GameFi / PayFI / RWA 等
- 明确深度与预期成果：投资决策 / 技术评估 / 合作可行性

### Step 2：项目筛选原则与信息收集渠道
- 筛选标准：市值、交易量、技术门槛、团队背景
- 信息来源：官网、白皮书、社交媒体、链上数据、第三方研报

### Step 3：基础信息与团队背景调研
- 主要成员/顾问的履历与声誉
- 发展历程、融资情况、资方背景

### Step 4：技术与产品可行性评估
- 技术架构与核心创新点
- 产品形态、可用性、扩展潜力

### Step 5：代币经济模型（Tokenomics）研究
- 代币分配与释放机制
- 代币功能、激励机制、**价值捕获逻辑**

### Step 6：生态与社区分析
- 社区规模与活跃度（开发者/用户/媒体口碑）
- 生态合作伙伴与外部资源整合

### Step 7：研究成果输出与评估
- 形成投研报告或内部评审材料
- 技术 + 市场 + 风险多维度综合结论

### Step 8：持续跟踪与动态调整
- 定期复盘项目进展与市场反馈
- 新信息/风险因素 → 及时修正评估
- 组织讨论会吸收多方观点，不断完善方法论

## 三、与已有方法论的交汇

| 本方法论 | 对应 |
|---|---|
| Step 4 技术评估 | Jason Chen「看里面」（怎么实现/原理） |
| Step 2 信息收集 | Jason Chen「看外面」+ 一手信源原则 |
| Step 6 生态分析 | Jason Chen「看旁边」（赛道横向对比） |
| Step 7 多维度结论 | 共学证据分级（先假设后结论） |
| Step 8 持续跟踪 | 共学「失败的想法也完整记录；验证不成立也是有效产出」 |

## 四、落地到共学/求职

1. **Dune/Glassnode/Nansen 清单** = 今天计划里「Dune 清算数据分析」任务的工具上下文
2. **审计报告查询（CertiK/SlowMist）** = 链上地址取证时可快速查项目安全背景
3. **八步流程可做成模板**：`templates/project-research.md`（把每步的「查什么、去哪查、输出什么」填进去）
4. 求职投研岗 = 直接展示套用此流程的分析报告

## 待做

- [ ] 把八步流程落成 `templates/project-research.md`（可填写模板）
- [ ] 工具清单补全：DeFi Llama 已用于 dead_protocol_screener；Dune 已列入 D4 任务
