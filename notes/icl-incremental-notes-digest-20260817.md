# 共学增量笔记 91 篇消化（2026-08-17 批次）

> 来源：`sources/残酷共学_增量笔记_带索引_20260817.pdf`（intensivecolearn.ing 2026-08-16 后新增 91 篇，213 页）
> 提取文本：`sources/残酷共学_增量笔记_提取文本_20260817.txt`（25.6 万字符）
> 消化时间：2026-08-18 上午（Hermes，3 子代理并行分章阅读 + 人工采样 9 篇）
> 上一批：`icl-incremental-notes-digest-20260816.md`（90 篇）

## 一句话

9 大章节 91 篇，本批最强五条线：**083（SimonQuant）Tokenized Stock × Hyperliquid HIP-3 RWA 基差套利**（机会存在置信度 90%，币股线从「时钟差」升级为「RWA 基差」）、**057（starkxun）资金费短窗口系统性骗人**（4 天窗口外推高估 9.3 倍，筛选判据完整化）、**052（xzone911）Monad gasLimit 不退回成本模型**、**037（Web3Rason）测量自我污染**（「速度溢价 51bps」= 自己填的滑点被原样读回）、**032（xsl）+033 原子性≠执行权**（竞价让渡 95% 后净剩 0.04 ETH）。与 08-16 批次（执行纪律）相比，本批从「执行纪律」推进到「系统性可审计的决策记录 + 新资产类别套利」。

## 主题分布

| 章节 | 篇数 | 核心内容 |
|---|---|---|
| 01 AMM机制 | 11 | PI vs Slippage、Quoter 幻觉量化、LP 范围/手续费查询、稳定币池失衡 |
| 02 LI.FI与跨链 | 14 | 跨链成本实证、链路身份治理、库存预部署、充提状态套利 |
| 03 MEV与抢跑 | 9 | OEV/SVR 机制、原子性≠执行权、PBS 供应链、竞价让渡 |
| 04 做市与LP | 6 | 做市积分创收、Neutrl 停赎、CCTP、V2/V3 对比 |
| 05 其他 | 1 | 闭环资产验证（单笔大额主导） |
| 06 套利框架 | 31 | 本批主力：Monad 成本/资金费对冲/观测缓冲/机会评分 |
| 07 学习计划 | 5 | Kelly、Paper Trading 方案、周末清坑 |
| 08 实盘与数据 | 7 | ADR 扩散vs收敛、Dune 管道、RWA 基差、天然价差 |
| 09 风险与安全 | 7 | 三角套利延迟优化、可审计决策记录、工具风险 |

## 高价值笔记速览（与用户研究线直接互证）

### ⭐ 083: Tokenized Stock × HIP-3 RWA 基差套利（SimonQuant，87 分）——币股线直接升级
- **结构**：Long NVDAx（链上 tokenized stock）+ Short xyz:NVDA（Hyperliquid HIP-3 perp），赚 Basis 收敛 + Funding + 微观结构错位。机会存在置信度 90%、小资金可交易 edge 70%
- **核心分解 log(P/X) = log(P/O) + log(O/X)**：perp 自身多空失衡（受 funding/杠杆/清算影响）与 oracle-vs-xStock 价格发现差（受传统市场开闭市/周末/做市商库存影响）分开定价，不能简单做 Perp−Spot
- **周末效应**：周五收盘 100 → 周末 NVDAx 104、HIP-3 107（P/X−1 = 2.88%）——传统价格锚消失后两个 24/7 市场争夺价格发现权，是结构性 alpha（判断置信度 70%）
- **TradeXYZ oracle 机制**：equity perp 的 internal oracle time constant ≈30 分钟 + discovery bounds 处理周末/假日 pricing session
- **Executable Basis 纪律**：屏幕 +70bps 实打可能 +15 甚至 −10；必须用真实可成交价（per 腿 taker 价 + 规模相关）
- **EB 完整账**：收敛 +45 + funding +18 − perp 费/滑点 9 − xStock 费/冲击 11 − 链上/库存 3 − 风险缓冲 5 = +35bps；$50k 完整例 net 36.8bps ≈ $184
- **信号初值**：MAD 稳健 Z = (b−median)/(1.4826×MAD)，Z>2.5 + Funding>0 + Executable Edge>25bps；7 类 session regime（US cash/pre/after-hours/overnight/weekend/holiday/earnings）
- **风控**：max_unhedged_time 1-3 秒；预放库存不临时跨链；basis 0.5%→3% 先爆仓的是现货腿（HL 账户不知道 Solana 腿会被清算→禁用高杠杆）；回测 1s/tick，看 Median/P5 Net Edge + MABE
- → 互证：082 B2 CRWD 51.9bps（CEX↔HL 是 CEX↔CEX 的 5-20 倍）完全同族；币股时钟差研究线新增「RWA 基差」分支——xStocks 已进 Solana（Jupiter/Raydium/Kamino 接入），我们 Jito 管线 + Solana 深池扫描可直接复用

### ⭐ 057: 资金费对冲从零开始（starkxun，87 分，1.1 万字）——筛选判据完整化
- **短窗口系统性骗人**：BILL 4 天窗口 +126.01% 同号 100% → 拉满 88 天仅 +13.57%（**高估 9.3 倍**）；SKR/WLFI/WLD 长窗口符号反转；清算案例 14 天窗口低估 39 倍（18,682 vs 真值 721,542）
- **完整筛选判据**：同号 ≥70% + 历史劈两半不反号 + 30 天内回本 + 名单换手率 ≤50%（compare 换手 >50% 说明筛的是噪音）；通过榜 LINK 15.78%（380 天/92% 同号）最扎实
- **Backpack 细节**：每小时结算（8760 次/年）非 8h；往返费地板 maker 20bps / taker 30bps；回本年化 1 天 73% / 30 天 2.43% / 90 天 0.81%；**所有 taker 单 100ms 减速带、仅 postOnly 免疫**（中文圈少有人知的硬约束）
- 定性 carry 非套利；五步路线：自跑筛选 → 复现陷阱 → 服务器跑两周 compare → 小额真跑 20-30 次测单腿发生率 → 填成本模型才算总数
- → 互证：与 075「躺平证伪」（ETH 5.0%/SOL −1.2%、翻转 70-90 次/30 天）、080 入场三条件（24h 均费率≥0.01%/h + 无翻转 + 成交额≥$10M）、062 甜区年化 10-11% 完全同族——我们 funding 监控直接补「短窗口对比 + 换手率」两列

### ⭐ 052: Monad 成本模型（xzone911，87 分）——gas 语义不同的链是生死线
- **gasLimit 不退回**：成本 = 提交 gasLimit×gasPrice 全额计，估少直接 out of gas；estimateGas×1.2x 安全系数（12000bps）后**重新全额计入成本**
- 最低 gas price 100 gwei（默认 121）；先确认顺序、下一块才执行（状态延迟 ≥1 块）
- FastLane：阈值 10 MON（≤10 走 direct，bid 默认利润 1%，payBidOnFail 禁用）；**msg.value 预付 bid 不能算进 route 利润守卫**（会计陷阱）
- 类比：Solana 保守预算 5,000→19,000 lamports
- → 互证：五阶段管线「成本模型」章节新增「gas 语义检查」步骤；任何新链集成先确认 gasLimit 退回策略

### ⭐ 037: 测量自我污染（Web3Rason，88 分，1.4 万字）——「一致到小数点后一位」恰证明没在测市场
- **速度溢价 51bps 作废**：Day 11 的「速度溢价 51bps」实为自己填的 0.5% 滑点被 toAmountMin 原样读回（滑点 0.1/0.3/0.5% 对应差值 11.02/30.94/51.02bps，toAmount 恒 1.02bps）——**量测上线前先验证「该让它变的参数真的让它变」**（L0 纪律：内部一致性 ≠ 外部效度）
- **价差与池深是同一状态两张脸**：长尾跨链 91 样本毛价差中位 50bps、净利中位 307bps；代币化股票基差中位 11.7/p95 12.4/max 12.6bp = carry 非机会
- **v3 Quoter 两阶段**：3,050 池 → 7,996 三角路径 → 一阶过滤 226 → Quoter 后真实机会 0，幻觉 100% 集中在含 v3 腿稳定币三角
- **平方滑点模型二次否证**：预测 50k 档恶化 24.5bps，实测整曲线 <1.1bps 且非单调（10k 1.06 > 30k 0.72）——模型预测 vs 实测必须分开报
- **主网分账实测**：毛差 1.14bps 即成立，builder 抽 55.4%、发起者实得 21.6%；bot 7,176 笔闭环成功仅 3.09% 但链费仅占毛利 0.32%
- **零费率天花板**：maker 0bp 吃满仅 $18.87/小时
- 延迟归因：网络 RTT 1-2ms→0.5ms 几乎无效；应用层重写捕获率 87.5%→96.8%、路径计算 40s→3s
- → 互证：008 的 Quoter 幻觉量化（97-99.5% 幻觉、std 0.083≫中位数、无通用校正公式）——**Quoter 是唯一可信验证**；回测/扫描器上线前的自查清单新增 037 条

### ⭐ 032: 原子性≠执行权（xsl，90 分）
- bundle 保证顺序+全有或全无，但不保证 top-of-block、会被竞争 bundle 改状态挤掉、晚到/validator 无 mev-boost/无共同 relay 则无法纳入
- 双模型：landed_net = 毛差 − DEX fee/滑点/冲击 − base fee/gas − priority fee/builder 支付 − 融资成本；expected_net = P(纳入)×landed_net − 基础设施成本
- **敏感性表**：毛差 1.00 ETH、执行成本 0.20 剩 0.80，竞价让渡 50%/80%/95% 后仅 0.400/0.160/0.040 ETH；033 同族：$1000−gas$50−bid$700=净 $250
- 负样本须按 revert / bid too low / conflict / late / proposer coverage 分类
- → 互证：Solana Jito bundle 管线同构（tip 定价 = 竞价让渡的 Solana 版）；「landed vs expected」双模型可并入执行层评估

### ⭐ 030: OEV 与 Chainlink SVR（jinnzy，90 分）——机制补全
- OEV = 预言机价格更新触发的 MEV（典型 = 清算 backrun）；SVR 核心 = **同一价格报告走双聚合器**：Standard 照常进公共 mempool、SVR 先进私有拍卖通道（主网 MEV-Share/Titan，Base/Arbitrum/BNB/Monad 走 Atlas），价格更新与清算**原子化**（同区块同成败），私有路由失败按可配置延迟回退 Standard feed
- 拍卖出价由 DeFi 协议与 Chainlink 按协议定制费率分成（无固定值）；对比 Api3 OEV = 拍卖「独家价格更新权」
- 边界：SVR 只回收预言机触发价值，不消除三明治/抢跑；本质是价值分配问题不是新策略
- → 互证：08-15 批次 SVR 选链第一维（未上 SVR 的链 $0.61M/年 100% 归己 vs 已上被抽 89%）机制完整化——清算哨兵选链评估表可直接引用

### ⭐ 004: CEX-DEX/跨链库存/充提事件驱动系统性研究（SimonQuant，89 分，1.8 万字）
- **预置库存套利 > 实时搬币**（交易秒级、rebalancing 分钟级，彻底解耦）；真正价值在 Executable Net Edge 而非 Displayed Spread
- **容量次线性**：Capital×10 利润仅 ×3-6；100bps 理论价差在 1K/10K/100K/300K 规模净 Edge 为 80/55/10/−30bps；Min Edge 分层：库存 20bps vs 实时桥 50-200bps
- **充提状态第一性原理**：Deposit Disabled→内部溢价（外部 10 vs 内部 10.5 = 5%），Withdrawal Disabled→内部折价；Resume 是均值回归催化剂；信息延迟 19 秒定胜负（12:00:01 vs 12:00:20）
- 示例账：20K USDT、45bps−31bps=14bps→$28/次×120 = $3360/月（2.8%）；桥风险量化 0.5% 事故率×40% 损失 = 20bps/年 Expected Loss
- → 互证：DOS 多链搬砖（桥费吃成净 7.6bps 的 NO-GO 判定）获「Min Edge 分层」理论支撑；事件驱动研究线新增充提状态维度

### ⭐ 086/091: 机会评分可审计化（Junfan Chen，88 分×2）
- 分数不替代证据：signal_key / quote_age_ms / executable_bps / capital_lock_seconds / path_type / failure_risk / exit_route_available，缺字段降置信度进人工复核，**不用默认值伪装成可比较数据**
- 四类分项：edge / freshness / capital_efficiency / execution_confidence；记录 6 类拒绝原因 + 当时输入快照（避免事后用最新报价倒推）
- **决策版本化**：strategy_version + cost_model_version + pricing_snapshot_at，改 gas/桥费/安全垫后可重放旧版本，区分「市场变化 vs 策略变化」
- → 互证：evidence-tracker 台账补「拒绝原因分布 + 版本号」两列；与 034 套利实验数据库（漏斗 100,000 发现→980 真盈利、13 种 failure 枚举）同族

### ⭐ 070: 九天地图盘点（HenryChang，90 分）——执行成本全谱
- 成本五拼图实测：两腿 60bps/三腿 90bps 费率走廊、冲击≈量/池深比（Sushi 枯池 1 万亏 19%）、ETH 原子套利 gas $0.05-0.2（BSC 约 1/7）、searcher 把 ~90% 毛利付 builder（p99/p50 = 44x）、最快端点落后 5 块
- 四只假机会标本：走廊内漂移 18.3bps<60bps、三角 +28.83bps 逐腿负、USDC→USDT 单向 +7.7bps 反向 8.3bps、旧数据鬼影
- → 互证：「看起来赚了≠真的赚了」家族又添一例；观测缓冲（063：小额漂移 0.0215bps/秒）与 29,166 USD 上界敏感性

### ⭐ 085: Binance 三角套利延迟优化（Zhihui Zhang，89 分）
- 三层递进：网络层 AZ 实测 RTT 1-2ms→0.5ms（min 0.513/max 1.009ms）+ 最优 IP 硬编码 /etc/hosts + FIX API；应用层 Elixir 87.5%（CPU 100% OOM）→ +C++ 91.7% → Full C++ 96.8%，路径计算 40+ 秒→3 秒（lock-free/热路径零分配/-O3 -march=native -flto/去容器 Nix）；OS 层 kernel-rt + busy_read 50000 + 禁 iptables + 禁中断合并 + mitigations=off + tuned latency-performance
- → 互证：执行现实学（287ms L2 地板）的 CEX 侧对照；「网络层改动最小收益确定、应用层收益最大」可作我们的优化优先级模板

### ⭐ 078: ADR 扩散 vs 收敛（bamboo，89 分）——机制决定策略
- 同一对概念两个市场结论相反，根因 = **有无强制收敛机制**：HFT 下架币有交易所结算时间窗（强制收敛）→ 赌扩散有兜底可做；海力士 ADR 无强制收敛（供应量新发行/注销可瞬间击穿溢价）→ 只做收敛，赌扩散=裸赌方向可能一直被套
- 海力士 8/13-14 溢价 48% 极端位实盘 −828U 教训互证
- → 互证：信息差套利状态机 + 事件驱动研究线新增「强制收敛机制」判断维度

### 其他高价值
- **022**：LI.FI 25bps 平台费是 gas（$0.03）的 81 倍；route 30 秒内翻转（CHEAPEST 切换、5-7 条）不可缓存成静态结论；feeSplit.integrator=0 需在响应中验证
- **023**：链路身份治理七教训——**chainId 只在 EVM 内唯一**（lz 将 Aptos 标 chainId:1 撞 Ethereum）、非 EVM 用原生 gas 币当键（11 链 11 币零重复）、证据分级 ca_match 58/native 50/chainlist 46/manual 43/lz_name 81，人工裁决 29 条防 INSERT OR REPLACE 洗掉
- **007**：Quoter 幻觉率 99.5%（tick_aware=False）/ 97.2%（True），偏差 std 0.083≫中位数 −0.028，无通用校正公式
- **044**：周末杠杆 ETF 偏离第 20-22 次监控——SNXX +165-181bps、KORU +189-226bps 常态、MUU 杠杆比异常 1.27-1.41x + Gate vs Binance 差 21.6bps 为唯一信号；8/12 极端值 SNXX +1731bps
- **072**：USDC 脱锚 12% 价差配 Curve 3pool 几亿美元深池同时成立 = Day8「大价差必配浅池」的**反例**（认知/信息差撑起的价差可以配深池：没人敢填 vs 填不动）
- **075**：Kelly f=(p×b−q)/b，90% 胜率/1.2x 赔率 Kelly=81.7% 但只用 1/4；资金隔离冷 80%/热 15%/Gas 3%/储备 2%；止损单笔 1%/单日 3%/连亏 5 笔停 24h/周回撤>10% 暂停
- **082**（kelthuz4d，90 分）：8/15+8/16 双批 198 篇合并消化，天然价差基准（Lighter vs EdgeX 0.04% 中位数、要求额外 ≥0.02%）、sNUSD 复现（LLTV 91.5% 借 1006.9）、PM UMA 保证金 ~$750/2h
- **084**：Dune 数据管道——dex.trades + prices.hour（按量加权前向填充 7 天过期）是三表回测底座；HL 免 key 实测 SKHX +42.4%/yr vs SKHY −13.6%/yr 双腿合计 ~56%/yr 都在付费→只做短期+极端位回归
- **081**：Gate CrossEx 开源前端（122 星/75 fork/AGPL-3.0）：一 Key 七所共享保证金、密钥只留本地后端、费率按原生结算周期标准化（Bitget 4h vs Binance 8h）——跨所执行层候选工具（注意：084 提到开源仓库当前 404，需复核）

## 对我们研究线的增量（编号清单）

1. **币股线升级为「RWA 基差套利」分支**：083 给出完整框架（log 分解、weekend session、MAD Z 信号、EB 账）。下一步：扫 xStocks（NVDAx/TSLAx/SPYx/QQQx，Solana 上已有池）vs HL HIP-3 的 basis+funding 基线——先建数据抓取脚本（HL 免 key + xStock DEX 报价），跑 2 周基线再谈信号
2. **funding 监控补两列**：短窗口 vs 长窗口对比（057 高估 9.3 倍案例）+ 名单换手率 ≤50% 判据；Backpack 每小时结算 + taker 100ms 减速带写入交易所参数表
3. **成本模型模板新增「gas 语义检查」**：Monad gasLimit 不退回、1.2x 后重算——集成任何新链先确认
4. **扫描器自查清单补「测量自我污染」条**：验证「该让它变的参数真的让它变」（037 滑点指纹 11.02/30.94/51.02bps）
5. **执行层评估改双模型**：landed_net × P(纳入) − 基建成本（032）；Jito tip 定价 = 竞价让渡的 Solana 版
6. **evidence-tracker 补「拒绝原因分布 + 决策版本号」**：区分市场变化 vs 策略变化（086）
7. **事件驱动研究线新增充提状态维度**：Deposit/Withdrawal Disabled → 内部溢/折价 + Resume 回归催化剂（004）
8. **Quoter 纪律再确认**：97-99.5% 幻觉率、无通用校正、v3 腿必须 Quoter（007+037 双证）

## 未消化清单

- 长文类（后续需要时按需精读）：013 LI.FI B1-B6（2 万字）、033 MEV 讲义（2 万字）、037（已消化核心）、004/083（已消化核心）
- 低分 <70 笔记 30 篇：多为打卡流水/概念复述，已由子代理一句话带过，无独立消化价值

## 勘误/互证修正

- **Day8「大价差必配浅池」需加限定**：072 给出反例——认知/信息差撑起的价差（USDC 脱锚 12%）可以配深池（Curve 3pool 几亿美元），区分「填不动」vs「没人敢填」两种形态
- **037 修正 037 自身**（Day 11 笔记）：速度溢价 51bps 是测量自指污染，修正为 ≈1.0-1.1bps——本 digest 只收录修正后结论
- **「无套利带 60bps 走廊」未在本批直接出现**，最接近的是 022（25bps 平台费）+ 004（Min Edge 分层 20/50-200bps），作走廊参数证据补充
- **Gate CrossEx 仓库状态矛盾**：081 称开源（122 星/75 fork）可用，084 实测当前 404——以 404 为准标记「待复核」，别当现成工具接入
