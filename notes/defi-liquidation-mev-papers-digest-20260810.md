# 清算/套利学术文献四连读（2026-08-10）

> 来源：Paxon 分享 4 篇论文（2026-08-10），PDF 归档 `sources/papers/`
> 解读角度（Paxon 引导）：①固定利差下 liquidation bonus 如何形成 searcher incentive；②Aave V2 头寸状态机对 liquidator scanner 的价值
> 状态：文献消化（数据点来自论文，未在本库复现）

## ⚠️ 勘误（2026-08-11 晚，来自群友 starkxun 的四连读对照 + AFT 2025 论文原文）

| 本笔记旧结论 | 外部证据 | 处置 |
|---|---|---|
| 主流市场清算人只有 2-3 个（四连读第 4 篇推断） | Aave V3 有 **183** 个、Compound V3 **184** 个、Morpho **159** 个清算人 | ❌ **作废**——「清算利润必然被竞价吃平」的机制结论仍成立，但竞争烈度比原判断高两个数量级 |
| 80% 清算是 $10 以下尘埃（我们 30 天样本） | 三大协议清算中位 **$20,266** | ❌ 作废——是我们样本的特性（小仓位为主），不是市场的 |
| 30 天全市场约 $640 万 | 论文三年 $14.58 亿 ≈ $40.5M/月；2022-11 极端 48h $12 亿 | ⚠️ 修正——我们窗口低约 6 倍，极端事件时差 100 倍+ |
| 「毛机会 50-98% 被构建者拿走」 | Wintermute 66% / SCP 81% / 整合渠道 ~90% | ✅ 独立印证（starkxun 从 AFT 2025 表格自行加总） |
| 清算机器人收款地址 0x51c7...2a7f 可能是 Wintermute | 该地址 = AFT 2025 论文中最大的 CEX-DEX searcher Wintermute（$74.8B 量、与 builder rsync 垂直整合） | ✅ 升级——「不是独立生意，是 Wintermute 订单流管道」的猜测获外部证据 |

> 详情见 `notes/day7-incremental-digest-20260811.md` 第 6 节。

## 论文清单

| # | 论文 | 作者/机构 | 年份 | 主题 |
|---|---|---|---|---|
| 1 | An Analysis of Fixed-Spread Liquidation Lending in DeFi | Moallemi & Patange, Columbia | 2024 | 固定利差清算建模（Aave/Compound/JustLend） |
| 2 | Frictions in DeFi Liquidations: Evidence from the Aave V2 Main Market | Schuler, U. Basel | 2026 | Aave V2 清算摩擦实证（46 个月/5.4 万头寸） |
| 3 | DeFi Liquidations Cluster Across Protocols in a Multivariate Hawkes Framework | Cao & Gang | 2025 | 清算跨协议聚集（Aave V3/Compound V3/Morpho） |
| 4 | Measuring CEX-DEX Extracted Value and Searcher Profitability | Wu/Sui/Thiery/Pai (Flashbots/EF/Paradigm) | 2025 (AFT) | CEX-DEX 套利价值测量（19 个月/720 万笔） |

## 1. Fixed-Spread Liquidation（Columbia 2024）

**核心实证**：70-80% 的清算发生在**没有向下价格跳变**的时段（30min 窗口 81%、1h 79%、12h 71%、1d 75%，5 种窗口 n=20~60 全部 >69%）。

**模型**：被动借款人（指数分布监控时域 T）的清算成本闭式解；最优健康因子 h\* 平衡融资成本（多抵押的资本机会成本）与清算成本。实证匹配要求借款人监控频率 = 交互频率的 3-4 倍；实际借款人初始 h 高于模型最优（保守）。

**searcher incentive 含义**（Paxon 角度）：
- **liquidation bonus 是固定折扣（5-10%）而非市场出清价** → searcher 的利润 = bonus × 规模 − 滑点 − gas − 执行风险。竞争下利润被压到「刚覆盖 gas」的水平（与 066 群友笔记 s_min 公式同构）
- **70% 无跳变清算 = 机会不是「等暴跌」**：任何 h<1 的头寸在预言机更新后都可能是目标，无论价格是否跳水。searcher 的 edge 在**监控覆盖率和预言机更新时点**，不在价格预测
- 预言机离散更新（论文承认的简化）：实际清算集中在预言机更新块附近

## 2. Frictions in Aave V2（Basel 2026）★ scanner 直接可用

**状态机**（图 4）：H（健康 h≥1）→ V（可清算且 v̄≥θ=250 fin，经济可行）→ S（stale：可清算但量太小，扣交易成本无利可图）。65,585 个可清算案例中 **32,658（约 50%）落在 stale 头寸**。

**Logistic 回归（清算在下一块发生的概率）**：
- ✅ 正相关：清算规模、liquidation bonus、MEV-boost 区块（PBS 私有流/捆绑）
- ❌ 负相关：Gas 高、oracle distortion（预言机偏离）、波动率高
- 反直觉：**稳定币抵押头寸清算概率更低**（拒绝了「稳定币抵押清算更省步骤所以更受欢迎」假设）
- 2022-11（FTX 崩盘）后清算基线概率断崖下降

**对 liquidator scanner 的映射**：
1. **θ 阈值理论化**：我们哨兵已有「奖励 $1K/抵押 $10K 低阈值」——论文给了一致结论：v̄<θ 是 stale，抢了白抢（负期望）。**scanner 应直接算 v̄（最大可清算债务量）而不是只看 HF**
2. **预测因子排序**：规模 + bonus 是清算成功的最强信号（我们排序依据正确）；Gas 高、波动率高、预言机偏离大时**跳过**（执行风险）
3. **预言机偏离的时序**：偏离>1（有利于清算人）时别抢——预言机更新会把相对利润打回；等更新后（失真归 1）才是干净窗口
4. **PBS 效应**：清算更可能发生在 MEV-boost 区块——Ethereum 侧要考虑私有流/捆绑通道

## 3. 清算跨协议聚集（Hawkes 2025）

**结果**：3 变量 Hawkes（Aave V3/Compound V3/Morpho），7,500 事件，ρ̂=0.725（亚临界稳定）；**最强交叉通道 Morpho→Compound V3（Γ̂=0.418）**；自激 0.28-0.32。交叉激发显著优于自激-only 和 ETH 价格共同因子基线；placebo 置换排除共享时间假象。

**含义**：
- **一个协议爆 → 相邻协议跟着爆是结构性现象**（共享抵押品、共享清算人基建、共享流动性），不是 ETH 价格波动能解释的
- 我们清算哨兵「morpho 优先」的实证结论与论文吻合（Morpho 是交叉通道源头）
- **scanner 应跨协议联动**：Morpho 清算事件 = Compound V3 清算的领先指标（~0.4 分支比），单协议监控会漏掉级联第二波

## 4. CEX-DEX Extracted Value（AFT 2025）★ 个人空间判死刑

**结果**：19 个月 7,203,560 笔 CEX-DEX 套利，19 个主要 searcher 提取 **$233.8M**；**前 3 个 searcher 占 3/4 的量与价值**（集中化加剧）。searcher 利润与 builder 整合度挂钩：中性 searcher（流量分散多 builder）利润率更高；独占 searcher 与 builder 分润（利润共享）；**searcher-builder 垂直整合的 builder 利润此前被低估**。高流动性代币 → 大单紧价差低冲击。

**Searcher 收入分解（论文 Table，Paxon 整理）**：

| Searcher | 成交量 | 估计收入 | 给 builder | 净利 | 给出去比例 |
|---|---|---|---|---|---|
| Wintermute | $74.8B | $71.4M | $47.1M | $24.3M | 66.0% |
| SCP | $63.5B | $71.1M | $57.4M | $13.7M | 80.7% |
| Kayle | $41.0B | $28.3M | $16.0M | $12.3M | 56.5% |
| Graves | $229M | $173K | $353K | **-$180K** | 204%（净亏） |

论文原话：「Wintermute 和 SCP 将近 90% 的套利收入直接转给整合的 builder，保留利润率略高于 10%」。

**结构性壁垒（Paxon 2026-08-10 补充，个人彻底出局的证据）**：
1. **做市商在 CEX 手续费是负的**：Wintermute/SCP 本身是顶级 CEX 做市商，maker rebate = 负费率——CEX 腿成本为负。个人做 CEX-DEX 套利 CEX 腿要付正手续费，第一层就输了
2. **给出去的比例不止 90% 而是 ~99.9%**：表格「给 builder」只是直接转账口径；加上优先费/区块内竞争等隐性成本后，实际让利接近 99.9%，searcher 净利极薄（Graves 直接净亏）
3. 两者叠加 = 容量大的 CEX-DEX 套利被结构性吃完——**不是「没抢到」，是「入场就输」**

**含义**：
- ETH 主网 CEX-DEX 套利已被「做市商 + builder 垂直整合」垄断——个人无空间（学术级证据，与「跨所价差已磨平」结论同构但更硬）
- 但论文承认只覆盖 19 个「主要」searcher——**长尾、新链、非 ETH 生态（Solana CEX-DEX）仍是空白**
- 与 137 批次笔记094 结论互证：散户活路 = 长尾链/卖铲人/结构性租金

## 四篇合起来的图景

1. **清算侧**：机会不是价格暴跌（70% 无跳变），是**边缘头寸 × 预言机更新时刻 × 经济规模 θ**；成功率由 规模+bonus 决定，Gas/波动/预言机偏离是执行风险；清算会跨协议级联（Morpho→Compound 最强）
2. **套利侧**：成熟市场（ETH CEX-DEX、跨所）已被专业机器 + 垂直整合垄断；个人 edge 只能在监控覆盖（stale→viable 转换）、长尾链、跨协议联动这些「机器人还没铺满」的地方
3. **方法论**：三篇都用「状态建模 + 概率/点过程」——与我们「哨兵只读发现 + 人扣扳机」互补：哨兵给事件，模型给「该不该抢」

## 验证待办

- [ ] 用 Dune Aave V2 清算数据复现「无跳变清算占比」统计（验证 70-80%）
- [ ] 我们的清算哨兵加 v̄（最大可清算债务量）字段 + θ 过滤（论文2 直接落地）
- [ ] 跨协议联动监控：Morpho 清算事件 → 观察 Compound V3 后续清算（验证 Γ̂=0.418）
- [ ] Solana CEX-DEX 套利地图：Jupiter 侧 searcher 集中度（论文4 的 Solana 版）

## 方法论：论文数据复用 + 研究拥挤度（Paxon 2026-08-10）

1. **论文里的现成数据/结论可直接拿来用**——省了自己花好几天拉数据验证的时间。四篇论文的数据点（70% 无跳变、θ=250 fin、Γ̂=0.418、$233.8M/720 万笔）都是可引用的「免费数据集」。
2. **被拉过来研究的 = 充分竞争的**：学术覆盖度是机会拥挤度的天然指标。一个方向一旦有论文（CEX-DEX、Aave 清算、稳定币跨链），意味着专业玩家已充分介入——个人拼不过；反过来，**没论文覆盖的长尾方向（Solana CEX-DEX、跨协议级联第二波、新链清算）才是候选**。
3. **找资料标准流程：谷歌搜 → arxiv 搜 → AI 搜**（论文优先于博客/推文，因为有数据）。

**落地**：以后评估一个新套利方向，先查学术覆盖度（arxiv/论文数量）作为拥挤度代理指标；已充分研究的方向直接降级，把时间投到「机器人没铺满」的角落。

## 关联

- `notes/colearn-incremental-137-digest-20260810.md`（笔记066 s_min / 笔记094 散户活路 / 笔记074 清算友好）
- `notes/liquidation-analysis-90d-20260808.md`（Dune 清算分析）
- `notes/aave-liquidator-0x8d64d775-address-research-20260808.md`（Aave 清算地址取证）
- `scripts/liquidation_monitor.py`（清算哨兵，morpho 优先）
