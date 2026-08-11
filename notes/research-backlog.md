# 研究 Backlog

## 1. 我的 Edge 到底是什么

问题：

- 我能比别人更快吗？
- 我能比别人技术更好吗？
- 如果都不能，我能不能在市场选择、信息差、规则理解、数据整理上找到 edge？

学习路径参照：`notes/learning-path-two-archetypes.md`（新手先吃透价差套利 + 资费套利两个原型，再谈变种）。

下一步：

- 写一页个人能力盘点。
- 选 2-3 个不靠极限低延迟的市场方向。

## 2. 跨所资金费率套利复盘

已知判断：

- 牛市可以研究，但现在跨所很难。
- 同所正费率机会稀缺。
- 负费率套利经常受限于借不到币。
- 跨所要承担流动性、高波动、滑点、价差不收敛、两头挨打等风险。
- 交易所内部团队有天然优势。
- 资金费率套利不是无风险，逼空、ADL、抵押品折价、保证金率和仓位集中都可能带来已实现亏损。

下一步：

- 写一篇复盘：为什么模拟盘和实盘差距大。
- 列出跨所套利的 kill criteria。
- 对照 1Token 资金费套利文章，整理一份风控指标清单。

## 3. 链上 Perp / Hyperliquid 类市场

假设：

链上 perp 相对更开放，仓位、资金费率、清算、订单流和规则更可观察，个人研究者可能更容易找到结构性机会。

需要研究：

- 资金费率机制
- 清算机制
- 订单簿或撮合机制
- API / WebSocket 数据
- LP / vault / maker 机制
- 极端行情下系统表现

下一步：

- 选一个具体市场，做数据字段清单。

## 4. RWA / 币股

假设：

RWA 和币股处在新资产、新规则、新路由出现的阶段，可能存在信息差、流动性碎片化和路径差。

需要研究：

- 1inch RWA / tokenized stock 相关功能
- xStocks / Ondo 等资产路径
- 链上流动性和真实市场价格之间的关系
- 交易时间、停牌、预言机、结算和赎回限制

下一步：

- 用 Hermes 整理一张 RWA/币股协议和工具地图。
- 补美股机制基础：小隐寺投资百科的美股入门/期权分类（https://xiaoyinsi.com/wiki），重点是盘前盘后、交易时间、做空、订单类型——币股 LP 的"闭市漂移"风险核算需要这些前置知识。
- 落地动作（来自群里"币股 LP 稳健"的体感）：选一个 xStocks 系池子，记录费率档、TVL、日成交量、开盘/闭市价差行为，跑一周数据验证"稳健"是否成立。见 `notes/case-toll-fee-pool.md` 环境迁移一节。
- 2026-08-05 新增线索：Binance Web3 Trading API 聚合了 bstock / Ondo / xStocks 等发行方（https://web3.binance.com/zh-CN/dev-docs/products/trading-api/introduction），数据接入成本大降。"多发行方锚定同一股票"的类稳定币套利结构已整理成专题笔记，见 `notes/tokenized-stock-arbitrage.md`。

## 5. 预测市场 LP / 自动挂单

假设：

预测市场 LP 的 edge 不一定来自预测准确，而可能来自报价、库存控制、手续费、价差管理和风险边界。

需要研究：

- 盘口结构
- 手续费
- LP 收益来源
- 事件结算规则
- 自动挂单脚本
- 极端新闻冲击下的库存风险

下一步：

- 找一个预测市场，记录盘口和成交数据字段。

2026-08-07 新增线索（论文 arXiv 2608.00666，两篇解读已归档）：

- **机制套利真实存在**：2.59 亿笔交易 → 111.8 万 USDC 机制套利利润（97% 来自 NegRisk Adapter「NO 回收套利」）；专业量化 2024.04-2025.04 提取约 4000 万美元，第一名单人 200.9 万
- **数学内核**：Marginal Polytope（市场间逻辑依赖 = 套利来源）、Bregman Projection（KL 散度算最优方案）、Frank-Wolfe + Gurobi（落地执行）、非原子执行风险（CLOB 不能原子成交）
- **关键认知**：市场约 40% 定价偏差，远没想象中高效；但执行门槛高（流动性木桶效应、毫秒级竞争、50 万+资金起步）
- **利润在压平**：NegRisk 单次转换利润中位数从 2024 年中 ~1 USDC 降到 2026 年初 ~0.08 USDC
- **对个人**：完整复刻机构系统不现实；可尝试「只读 NO 库存优化器」（作者给了开发需求），先看当前真实利润分布
- 笔记：`notes/polymarket-negrisk-no-recycle-arbitrage.md` + `notes/polymarket-arbitrage-math-framework.md`；Polymarket skill 已有查价能力，缺策略层

## 6. MEV / AMM 攻击 PoC

定位：

先当作理解链上交易排序、AMM 风险和透明市场竞争的训练材料，不作为默认赚钱方向。

需要研究：

- Sandwich
- Front-running
- Back-running
- JIT Liquidity
- MEV Bundle
- Flashbots / private tx / builder

下一步：

- 跑 DeFi PoC Lab 的 MEV Foundry 测试。
- 写一篇“为什么 MEV 门槛高”的笔记。

## 7. taoli.tools 工具拆解

问题：

半自动对冲套利工具如何处理双边下单、价差监控、仓位、资金费率和风险提醒？

下一步：

- 体验功能。
- 写工具拆解：它解决了什么，没解决什么，背后的策略假设是什么。

## 8. 信息差来源系统

目标：

不要只收藏信息，要把信息变成可验证机会假设。

校准原则（2026-08-05）：

公开分享的策略默认是滞后信息——edge 已被提取大半。扫描信息时优先提取"发现路径"（看了什么数据、注意到什么异常），而不是策略本身。详见 `notes/2026-08-03-context.md`。

来源：

- GitHub
- 官方文档更新
- 协议公告
- 黑客松奖项
- 交易所公告
- RWA/币股新资产
- 预测市场新事件
- 高质量个人账号：@hunterweb303（2026-08-05 贡献了"收过路费"思路，见 `notes/case-toll-fee-pool.md`）
- 待发布跟踪：Bruce 承诺写一篇 Sub2API + CN2 主机的搭建部署文章（灵感来自 @icooperhero），发布后收进知识库

下一步：

- 用 Hermes 设计一个每周信息扫描任务。

## 8.5 监控 Bot 基本功

定位：

突发溢价靠人工来不及，监控 Bot 是"在场"的前提。第一阶段只做发现和告警，不做自动执行。

补充定位（2026-08-05）：

监控 Bot 不只是告警工具，它是"数据发掘"这个能力缺口的第一个载体：告警规则 = "知道该盯什么"的显式表达，CSV 日志 = 私有数据集的第一块砖。详见 `notes/2026-08-03-context.md` 能力缺口一节。

选型：

- Python + ccxt（CEX 行情/资金费）+ DexScreener API（DEX 价格）+ Telegram Bot（告警）
- 最小闭环：拉数据 -> 算价差 -> 阈值告警 -> 记日志

详见 `notes/monitoring-bot-quickstart.md`。

下一步：

- 写一个只读监控 demo，跑 1-2 周看误报率。

信号清单（随讨论累积）：

- CEX/DEX 价差（monitor_demo.py 已覆盖）
- 资金费率突变 + basis 分位（见 `funding-fee-arbitrage-1token.md`）
- LP 环境三指标：池子日成交量/TVL、价格穿越频率、趋势/震荡比（见 `case-toll-fee-pool.md`）
- 大额撤池告警：池子 reserve 突变、LP token 大额转出、项目方关联地址撤池——砸盘和 rug 的先行指标（2026-08-05 群经验，EVM 盯 Burn/Transfer 事件，Solana 用 Helius webhook 盯池子账户）

## 9. Solana 单独研究线

定位：

Solana 不直接作为“马上套利赚钱”的目标，而是作为一条独立研究线。重点研究交易结构、DEX/perp、Jito/MEV、priority fee、compute units、数据索引、RPC/Geyser、路由聚合和执行达成率。

为什么值得研究：

- 本地已有 Solana/Rust/Anchor/Pinocchio 项目积累。
- Solana 账户模型、交易结构、CU、priority fee、Jito bundle 等机制和 EVM 差异很大。
- 链上 DEX/perp 和路由聚合较活跃，适合做数据监控和执行质量研究。

风险：

- Solana 速度型 MEV 很卷，容易变成 RPC、节点、Jito、低延迟和模拟准确性的基建竞赛。
- 第三方 MEV bot 文档和二进制不要直接信任，更适合作为学习样本。

下一步：

- 先整理 Solana 资料地图。
- 从 Jupiter/Raydium/Orca/Meteora/Drift/Jito/Pyth/Helius 官方资料开始。
- 研究 rust-mev-bot 文档，只做架构和风险拆解，不导入私钥实盘运行。

## 10. LP 作为入门研究对象

背景：

入门阶段"基本上都是去提供流动性的"（见 `notes/2026-08-04-entry-reflection.md`）。与其把 LP 当成没进展的代名词，不如把它变成第一个可验证的研究样本。

需要研究：

- 无常损失的计算和实际发生条件
- fee APR 名义值 vs 实际到手（复投、领取成本、价格区间）
- LP + 合约对冲的类资金费率套利结构
- 稳定币 LP、预测市场 LP 的报价和库存逻辑

案例样本：

- `notes/case-premium-buyin-lp.md`：溢价买入 + 加池子吃利差，用已知上限的溢价成本换高利差收入
- `notes/lp-dynamic-range.md`：程序动态调区间，上涨行情继续吃 fee；研究点是调整触发条件、成本和回测对比
- `notes/case-toll-fee-pool.md`：收过路费——在套利机器人必经之路上放高费率池；核心风险是 toxic flow / LVR 和 JIT 竞争

下一步：

- 记录当前在做的 LP 池子：链、协议、资金规模、入场价格、fee 收入、IL
- 一周后复盘：fee 是否覆盖了 IL

## 11. Cosmos 生态跨链价差（偏门候选）

来源：8.4 聊天记录学习版（`notes/zero-based-learning-edition-84.md` 第七章）。

假设：

Cosmos 多链生态里，同一经济资产的主链资产、包装资产（axlUSDC/axlATOM）、质押衍生品（stkATOM）在不同链和 DEX 间定价不一致。冷门链（如 SCRT）竞争少，符合"偏门套利"方向。

需要先核查（不要当结论）：

- 包装资产的发行方、合约地址、赎回路径和流动性
- 跨链/赎回等待时间 vs 价差持续窗口
- 目标链的真实活跃度（活跃地址、交易量、费用，而不是听说）
- "解压 14 天、撸 30 个点"的资产、锁定期、收益来源和退出条件

下一步：

- 选一个具体资产（如 stkATOM），用 Hermes 整理它的完整路径：发行方 -> 合约 -> 流动性 -> 赎回 -> 价差数据

## 12. 防 MEV 交易通道调研

来源：2026-08-05 群讨论（`notes/mempool-and-ordering.md`）。

假设：

个人研究者在公共 mempool 链上没有 builder 关系，私有排序器链又是黑盒，防御（不被夹）比进攻（找机会）优先级更高。防 MEV 通道是低成本基建。

待验证清单：

- Binance Wallet API：聚合 LI.FI/1inch/Liquidmesh 报价 + 免费付费级节点 + 防 MEV，接入条件和实际效果待测
- Flashbots Protect / MEV Blocker（EVM）
- Jito bundle（Solana）：机制、门槛、费用

下一步：

- 注册 Binance Wallet API，用同一笔测试交易对比走普通 RPC 和防 MEV 通道的成交结果

## 13. 低容量结构性价差量化（2026-08-11 新增）

来源：群讨论复盘结论「个人活路在低容量结构性价差」× Bruce 14 类对照表 ✅ 区间（清算/铸赎/消息事件/跨链非稳定币）——「低容量」目前只是定性判断，未量化。

假设：

- 小池子/小所的价差持续时间更长（竞争者少），但容量上限低（吃几笔就没了）、对手方风险高（提现/插针/跑路）。
- 存在一个「容量 × 持续时间 × 竞争度」的可行域：价差足够大、持续足够久、且容量能容纳目标仓位时，个人才有可执行空间。

验证路径（接 backrun 模拟器升级待办）：

- 小池价差持续性：solana_dex_spread_monitor 已有全配对时间序列（corridor_series.csv），按池子深度分层统计「出轨事件 >20bps 的持续时间分布」，验证「薄池价差持续更久」。
- 容量上限：对出轨池子测 1/10/100 SOL 档报价滑点（jupiter_route_monitor 已有双报价采样），找「容量边界」——滑点吃掉价差的档位。
- 小所价差：OKX/bitget/kucoin 可用的币种 vs 主流所价差（ccxt 拉盘口），统计价差与成交量的关系，验证「小所价差大但深度浅」。
- 输出：一页「低容量可行域」判断表（方向 × 价差中位数 × 持续时间 × 容量上限 × 风险），填进 Bruce 14 类对照表。

风险提示：

- 低容量 = 退出难，先问「买得到是否卖得出」再谈价差。
- 小所对手方风险优先于价差（吃尸体教训：先验证提现，再验证价差）。
