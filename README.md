# 链上套利残酷共学笔记

> 🔭 **个人套利研究武器库** | 21 天残酷共学（2026-08）| Python + Rust 双实现
>
> **研究范围**：DeFi 清算套利 · 跨所价差 · 资金费率拥挤度 · 币股时钟差 · Solana DEX 套利 · MEV/原子套利
>
> 📊 **监控哨兵 8 个**（cron 自动运行，只读发现，人扣扳机）：上币公告 · OI 异动 · 清算 · 停运协议 · 协议清单 · 跨所价差 · 币股时钟差 · 资金费率拥挤度
>
> ⚠️ **免责声明**：本仓库为研究学习记录，所有脚本只读、不下单，不构成投资建议。链上地址均为公开数据。

## 🚀 快速导航

| 想了解 | 去哪 |
|---|---|
| **Taoli Tools 套利角度清单 + dsh 实操验证**（X @aliez_ren 9 类套利角度对照我们研究——7 类已覆盖、2 新线索（Bitget 资金费逃票/BNB IDO 前后）；dsh 三大宣称全部实测属实+顺手修 2 脚本） | `notes/taoli-tools-arb-angles-dsh-verify-20260815.md` |
| **链上取证方法论**（怎么分析一个套利地址） | `notes/aave-liquidator-0x8d64d775-address-research-20260808.md` · `notes/robinhood-arb-0xd7121208-address-research-20260808.md` |
| **EVM 实战案例：闪贷灌金库 + oracle/DEX 价差**（Morpho 0 费闪贷 $27.7M 灌 Lulo 金库→allocator 铺 3 市场；V4 近空池 $0.686 扫 sNUSD vs oracle $1.0638 → 满额 91.5% LTV 借出，单笔净赚 ~$297/gas $0.87；含 `idToMarketParams()` + ChainlinkOracleV2 vault 模式取证新动作） | `notes/morpho-flashloan-vault-snusd-arb-case-20260813.md` |
| **L0011 研究拆解工作流**（阶段三 D10：观察→假设→证据→实验→决策 五步 + T0-T5 六任务模板 + Morpho 案例拆解实录；Hermes 分工=人定义问题/Agent 取证；衔接 L0013 证据体系） | `notes/l0011-research-decomposition-workflow-20260814.md` |
| **执行现实学：服务器方案评估 + Sequencer 287ms + 官方工具栈**（自建全节点 $240-430/月=研究期过度配置；287ms=L2 公共路径速度地板，结构性机会不需要抢；Bruce 工具文 digest：LI.FI 100RPM+25bps/Binance Web3 免费四类/Taoli $5k/私有 RPC/安全五规则；金句「套利关键是发现机会不是基建」） | `notes/execution-reality-infra-latency-20260814.md` |
| **HaasOnline 三角套利 scam bot 拆解**（反诈取证：披官方外衣要求导入私钥；8-11 官方辟谣 + 8-13 受害者 4.1 BNB 被转空；识别 check 五连问；归因边界=陈述≠证据需链上核验） | `notes/haasonline-scam-bot-case-20260814.md` |
| **LI.FI API Key 配置清单**（已注册 Integration：Key 只显示一次→测试→安全存放 ~/.config→环境变量接入→匿名 vs 带 Key 对比验证；Key 不进 git/聊天） | `notes/lifi-api-key-setup-20260814.md` |
| **HKDAP 合约审计 digest**（香港首个持牌港元稳定币：KYC fail-open 死代码/治理单签/transfer 绕过/主网部署 debug 版 13 条；HKMA 指引 4 条冲突；沉淀审计取证五招：角色枚举/授权矩阵/升级还原/存储槽直读/事件对账；稳定币套利方向标记观察） | `notes/hkdap-audit-digest-20260814.md` |
| **哨兵速读手册**（24 个哨兵×4 问：监控什么/字段含义/触发条件/看到后怎么办；状态色 🟢🟡🔴🔶；字段速记 bps/P50/可用/z-score/出轨；配套 infra_selfcheck 输出升级为「人话版」+ lifi 代理端点单独放宽红线 4000ms 防误报） | `notes/sentinel-cheatsheet-20260814.md` · `scripts/infra_selfcheck.py` |
| **从研究到生产五阶段管线**（阶段0研究→1回测→2脚本→3模拟→4生产，每阶段 exit criteria；当前位置：0✅/1🔄/2✅/3-4⏳；第一条全流程线候选=币股漂移/费率窗口/PM 事件；Solana 剩余缺口=Jito Bundle pipeline；理解检验机制=费曼复述 15min/天） | `notes/from-research-to-production-roadmap-20260814.md` |
| **周会 digest 2026-08-14**（Ethanlxl CEX 套利实战方法论：大币无机会/山寨靠狗庄/费率→溢价指数→意图；LI.FI 产品矩阵 ear/composer/intents 零费；z0y1 分享池价vs预言机=我们案例互证） | `notes/weekly-meeting-digest-20260814.md` · `sources/链上套利残酷共学周会_transcript_2026-08-14.txt` |
| **Morpho 监测方案 digest**（检测公式 deviation=|oracle−spot|/oracle；borrowable=oracle×LTV；三条发现路径（价差扫描/埋雷筛选/去锚监控）；L0-L3 分层；告警 2%/5%/10%；雷达数据源解锁=GraphQL 实测（首屏 4 埋雷市场）；sNUSD 窗口复盘=16h 生命周期+利用率 100% 冻结） | `notes/morpho-discovery-monitoring-digest-20260814.md` · `sources/morpho-arbitrage-discovery-monitoring-2026-08-14.pdf` · `sources/morpho-snusd-arbitrage-window-report-2026-08-14.pdf` |
| **HFT 狗庄出货案例**（0x4bfd879f 在 8/7 HFT 暴涨 3.5 倍行情中净卖 61.4 万 HFT 赚 ~$1-1.9 万；资金链=巨鲸 0x28C6…（212k ETH）供币→合约出货→利润归集；沉淀「狗庄识别」信号→已落地每小时雷达 whale_dump_radar.py；含完整取证过程实录 6 步） | `notes/hft-pump-dump-execution-0x4bfd879f-20260814.md` · `scripts/whale_dump_radar.py` |
| **赛道选择结论**（清算/原子/跨链怎么选） | `notes/arbitrage-track-selection-20260808.md` |
| **风控总纲**（套利=概率游戏，敞口控制生死线） | `notes/arb-risk-black-swan-20260809.md` |
| **137 篇增量批次消化**（LI.FI 0.25% 成本地板 / 无套利带 / Robinhood V4-hook 开窗根因 / 0xd712 失败成本门槛公式 / Solana LP 集中度） | `notes/colearn-incremental-137-digest-20260810.md` · `sources/残酷共学_增量笔记_带索引_20260809.pdf` |
| **Day 6 报价对比实验**（L0006：Base→Arb USDC 三档×三桥；无规模折扣 25bps 恒定 + 快6s≈1bps + 「时长假象」across 100k 档 1s→900s）⚠️ **2026-08-12 复测勘误：25bps 是默认参数渠道费，带 `integrator=jumper.exchange` 全档归零（socket/lifi 照收）→ 跨链门槛下移 25bps** | `notes/day6-lifi-quote-compare-20260810.md` · `scripts/day6_lifi_quote_compare.py` · `notes/l0006-integrator-retest-20260812.md` · `scripts/l0006_integrator_retest.py` |
| **验证日：066+128**（066 最小价差公式复算：EVM 0.6114% 精确复现、Solana priority fee 30h 全 0 → 门槛=费率地板 Raydium 0.50%；128 WETH/USDG 双池核验：深池 0x52e65B 3.04e18 vs 浅池 0xb2a6aD 5.82e15 = 522 倍，bot proxy 0x19c8 吻合） | `notes/backtest-verify-066-128-20260810.md` · `scripts/066_smin_recalc.py` · `scripts/066_smin_recalc_fee_sweep.py` |
| **网格策略趋势市回测**（「在金」1300U 幸存者偏差验证：OKX BTC 1h 13 个月，下跌月亏损率 88% vs 非下跌月盈利 100%；0 手续费仍净亏 → 趋势月库存浮亏>震荡月 gross edge；10x 杠杆 -10% 月即爆仓；手续费 vs 格距生死线 = L0007 成本拆解落地） | `notes/grid-trend-backtest-20260811.md` · `scripts/grid_trend_backtest.py` · `data/grid_monthly_backtest.csv` |
| **Day 7 全景笔记**（认知主线：看起来赚了≠真的赚了——网格1300U/Polymarket榜一/gas反杀/OPENAI假价差四案例→5问筛选框架；工程7项全跑通；研究线#13/#14；广度14条归档；明日D8衔接） | `notes/day7-complete-20260811.md` |
| **L0008 机会候选清单 v1**（11 候选×5 问筛选：✅进清单 3 个=PM 天气稳赢/事件驱动吃尸体/跨所费率事件窗口（全有真实证据）；🟡待验证 5 个=币股/perp funding/低容量/rebalancing/OFT；🟡计划 1=PM LP；❌2 暂缓；挂掉的候选全挂在「30 天证据」） | `notes/l0008-opportunity-candidate-list-v1-20260812.md` |
| **AI 时代判断力方法论**（编程史坐标轴：意图→执行转换成本下降 → 抽象层缺失警告 → 写作=意图结构化=prompt 上游；与「判断力是方向盘、AI 是加速器」互证） | `notes/ai-judgment-methodology-20260812.md` |
| **DOS 多链搬砖三步落地**（找币→监控→搬砖：slot0 直读价格与 Gate 精确一致；BSC+ETH 双链深池多链币极稀缺（候选 OFT 币 BSC 全无池）；DOS 毛价差 136bps 但 BSC→ETH 桥费 $0.69 吃成净 7.6bps → 当前 NO-GO；等 ETH 折价+ETH→BSC 便宜方向） | `scripts/multi_chain_spread_monitor.py` · `notes/dos-bridge-arb-20260811.md` |
| **研究线 #14：Meme 微观结构**（5M 壳价 cohort 验证「难亏钱」假设 + Dev 行为哨兵四本账 + 增发监控；博弈研究非实盘建议；接 #13 低容量量化共享基建） | `notes/research-backlog.md` · `notes/meme-dev-harvest-pattern-20260811.md` |
| **TUT Rust 双实现 v2 · 时间对齐**（inner join on ts 替代 index 硬对齐；ts 毫秒归一化+去重；抓到 v1 盲区：2025-03-20 bn 09:00 起 vs bg 00:00 起=按 index 配对全错；交叉验证：2026-05-28 检出 11-bar 窗口、2026-08-09 检出 31-bar/16.16% 插针窗口，与 Python 版一致） | `scripts/tut_backtest/rust/src/main.rs` |
| **无套利带雷达 v2**（Raydium 锚点校准：池 58oQChx 活跃确认；深度过滤=腿价偏离锚点≥300bps 标 suspect 不告警；Jupiter 池列表 API 不可用→偏离代理；实测全配对在走廊内，100 SOL 档 Raydium↔Quantum 61.4bps 顶到 60bps 走廊上沿） | `scripts/no_arb_corridor_radar.py` · `data/corridor_series.csv` |
| **Meme 盘 Dev 出货手法拆解**（140 盘链上取证：建仓→藏仓59%转子钱包→试探→主卖40%→子钱包清仓→Locker 分润；「四本账」监控+进出规则=费后正数才进/受控大卖就走；信息差套利状态机，接 onchain-address-forensics） | `notes/meme-dev-harvest-pattern-20260811.md` |
| **Binance Alpha「搬砖套利」拆解**（Alpha=币安链上聚合入口非独立市场，订单链上执行；「Alpha vs 链上价差」=聚合报价 vs 单池=显示假象；Alpha 资产提现受限=资金闭环存疑；真机会=公告前埋伏的信息差博弈，非价差套利） | `notes/binance-alpha-arbitrage-20260811.md` |
| **Solana 个人线第一周总结**（D1-D7：交易模型/Anchor 环境/devnet swap/双实现监控/币股哨兵/执行层 5 哨兵；对照 v1 校准自查全达标且超前；广度标注 3 候选：币股★★★/低容量★★★/链上 perp★★） | `notes/solana-week1-summary-20260811.md` |
| **「看起来赚了≠真的赚了」gross vs net 方法论**（网格1300U/Polymarket榜一/gas反杀三案例合一：评估赚钱案例 5 问=口径/成本占比/返佣依赖/市场状态/最小有效规模；L0008 机会清单筛选前置） | `notes/gross-vs-net-three-cases-20260811.md` |
| **D8 预习：AMM 数学 x*y=k**（公式推导+Python 手算；Raydium SOL-USDC 真实储备精确复现 73.9612 误差 0；费率反推=0.30% 非 0.25%；深池 1000 SOL 滑点 1.7%；滑点曲线=容量曲线，接 backrun 薄池扫描） | `notes/amm-math-v2-preview-20260811.md` · `scripts/amm_v2_verify.py` |
| **tvscreener 验证**（TradingView Screener Python 库：直连免费，美股实价/涨跌/1h 全有；意外收获 CryptoScreener 含 BITGET:RSPYUSDT 等 tokenized 股对 → 币股时钟差双腿数据源打通；坑：ticker 过滤需前缀+isin 不支持多值） | `notes/tvscreener-verified-20260811.md` |
| **实操案例：毛利为正 gas+桥费翻负**（0.004 ETH 跨链毛利 +0.13% 但成本占 1.46%=毛利的 11 倍 → 净亏；最小有效规模=固定成本/价差率，$7.5 亏、$83 平、$1000 进最优点；门槛公式 NO-GO 判定一致） | `notes/gas-bridge-fee-eats-arb-case-20260811.md` |
| **群讨论复盘：认知推进四阶段**（概念共识→案例吸引→路径>代码→基建门槛；系统=数据/识别/执行/风控四层；术语：吃尸体=对手方风险/埋伏/原子套利；AI 降门槛不产利润；结论：案例≠收益证明、个人活路在低容量结构性价差） | `notes/group-discussion-synthesis-20260811.md` |
| **Polymarket 排行榜税前口径验证**（@runes_leo 推文实测：手续费公式逐档正确；每股费实测 0.012-0.014 与推文吻合；返佣真实可量化 Djdjdjekekek 11 天 $74.6K；榜单 pnl=gross；抓到反例 HomeRunHazard 月榜 +$454K 但近 11 天纯交易 −$121K；修正：24-45% 只适用于 edge≈费的吃单 bot） | `notes/polymarket-leaderboard-gross-pnl-20260811.md` · `scripts/polymarket_leaderboard_fee_verify.py` |
| **PM 论文 digest：Probabilistic Forest**（AFT 2025：Polymarket 一年已实现套利 $3,960 万 / 买 NO $17.3M 最大头 / 两类套利定义 / 约 99% 机会未被执行；LLM 找依赖市场对方法；与 127 盘口镜像互证） | `notes/pm-probabilistic-forest-arb-paper-20260812.md` · `sources/papers/pm-probabilistic-forest-arb-2508.03474.pdf` |
| **PM 实盘教训：天气市场与规则风险**（Paxon 第一手经验：官方朝令夕改/幽灵订单扭曲盘口/结算改 30s TWAP/平仓流动性亏 30-50%「开仓不想平仓」/尾盘赌反转吃筹码/「别做比市场定价更准的策略」/带方向 LP 计划=结构性 edge） | `notes/pm-weather-lp-lessons-20260812.md` |
| **PM rebalancing 盘口扫描器 v1.1**（盘口可执行口径：ΣYES_ask<1 扣费+容量才出信号；不用 VWAP 防高估；幽灵墙标记；实测 300 市场 0 信号=镜像结构正常态；审计 JSONL） | `scripts/pm_rebalancing_scanner.py` · `data/pm_rebalancing_scan.jsonl` |
| **Backrun 薄池扫描器 v1**（容量边界量化：SOL 主流全深池互证 D5；BONK 容量边界实测 $10K——$10K 档 -40%、$50K 档 -73%；长尾币按美元档扫 + 多跳路由 outputMint 定位坑） | `scripts/backrun_thin_pool_scanner.py` · `notes/research-backlog.md` #13 |
| **Maker LIQ2.0 拍卖哨兵 v1**（35 ilk 动态发现 + 多 RPC fallback + watchdog；cron 30m；双 Agent 协同撞 DB 教训） | `scripts/maker_clipper_sentinel.py` · `scripts/auction_sentinel.py` |
| **清算/套利学术四连读**（70% 清算无跳变 / Aave V2 状态机 H-V-S / Hawkes 跨协议级联 Morpho→Compound / CEX-DEX 3 巨头垄断 $233.8M） | `notes/defi-liquidation-mev-papers-digest-20260810.md` · `sources/papers/` |
| **Bruce 第一性原理 + 14 类对照总表**（官方教材：无套利一致性/7步执行法/14 类区间 vs 我们实测的存活状态导航页） | `notes/bruce-first-principles-arbitrage-20260810.md` |
| **888BMM 两腿 swap 实例**（USDC→EURC→USDC 无 flashloan 无清算；与 068 互证）+ **信息差套利本质**（赚钱=信息差套利，三步法=哨兵架构同构） | `notes/888bmm-two-leg-swap-20260810.md` · `notes/information-gap-arb-essence-20260810.md` |
| **Day 6 晚间增量精华**（046「成本在时间不在费用」与时长假象独立互证 / 093 Solana 首笔盈利+构造延迟瓶颈 / 094 事件套利六阶段 / 085 滑点授权金句 / 086 报价采集 v1 / 091 清算多链化 / 092 完整成本模型） | `notes/day6-incremental-evening-digest-20260810.md` · `sources/残酷共学_增量笔记_带索引_20260810.pdf` |
| **L0009 阶段复盘·知识图谱 v1**（四层结构：概念→机制→工具→决策；14 类存活地图三支柱（毛差<费/价差≠可执行/返佣撑收益）；7 条互证网；edge 收敛=事件驱动>常驻>预测）→ `notes/l0009-knowledge-graph-v1-20260813.md` |
| **证据记录体系 v1**（D10 流水线第一步：6 个 🟡 候选 × 30 天自动收数 → `data/evidence_daily.jsonl` + 台账 `notes/evidence-tracker.md`；cron 每日 23:30 watchdog；到期自动评分）→ `scripts/evidence_harvester.py` |
| **Day 8 增量精华**（008 DOS 加错池子=信息差活教材 / 073 大价差≠好机会·8 项成本 / 117 DOS LayerZero 独立核验=互证 / 048 固定金额薄池毁灭冲击 / 114 bStock四层市场证伪·TradFi perp 全清单 HK11+KR3 / 057 HIP-3 双边做市）→ `notes/day8-incremental-digest-20260812.md` |
| **Day 9 增量精华**（012 µToken=Unipeg 同团队+v4 Hook 双账本错位 / 018 DOS 三方互证·池子 1 万U+未开提现 / 034 LayerZero 同工具互证·224 资产 / 002 GUA「行消失」四态 / 063 Anthropic 盘前-350u 教训·资金费 0.5bp/8h / 051 报价≠成交 / 053 执行前决策闸门五问 / 060 LLAMMA 软清算=套利者是清算引擎）→ `notes/day9-incremental-digest-20260813.md` |
| **Day 7 增量精华**（052 库存再平衡后净 Edge 仍负 -196~-221bps·三处互证 / 064 integrator 参数让 25bps 平台费归零·L0006 需复测 / 098 TUT 插针实证·20% 筹码转 Bitget / 132 六策略回测·LINK 快桥唯一正夏普 0.62 / 130 论文修正·清算人 183+ 中位 $20K / 126 HIP-3 股票永续 20 只） | `notes/day7-incremental-digest-20260811.md` · `sources/残酷共学_增量笔记_带索引_20260811.pdf` |
| **下架合约价差套利**（群策略实证：HFT 439bps + OI 累计偏离 + L/S ratio 净方向） | `notes/binance-delisting-arb-verified-20260809.md` · `scripts/binance_delisting_review.py` · `scripts/delisting_monitor.py` |
| **拍卖类调研（Maker LIQ2.0）**（空白候选补齐：Dog→Clipper 荷兰式拍卖、零 DAI flash-callee 参与、实测全系统 0 活跃拍卖 + ETH-A 最近活动 2026-06-05、新 7 参事件签名避坑） | `notes/maker-liquidation-auction-20260810.md` |
| **拍卖哨兵 v1（Maker Clipper）**（LIQ2.0 调研落地：IlkRegistry.list() 动态拉 35 ilk → Dog.ilks 拿 clip → Clipper.count() 轮询，>0 即告警+sales() 明细；多 RPC fallback 防限流；cron 每 30 分钟） | `scripts/maker_clipper_sentinel.py` · `data/maker_clipper.db` |
| **D9 预习：CLMM 集中流动性**（tick 与价格 P=1.0001^tick；虚拟储备公式 x=L(1/√p−1/√pb) y=L(√p−√pa)；Raydium 储备实测资金效率 X21.5x/Y19.5x；出区间=单边资产=网格穿界风险的 AMM 版；可视化 `data/clmm_visual.png`） | `notes/amm-math-clmm-preview-20260811.md` · `scripts/amm_clmm_visualize.py` |
| **LP 动态调区间回测**（D11 广度：BTC 420 天下跌段 ±10% 区间模拟——动态调区间 -11.3% vs 死守 -29.5% vs 持有 -40.2%；**反直觉**：上涨月动态反而输 2.3pct（追价调仓税），下跌月赢 1.7pct（防出区间停收 fee）；触发频率是生死线 0.5%→成本 1314% of fee 归零，5%→37%；半宽越窄动态优势越大；fee 倍数≠净收益） | `notes/lp-dynamic-range-backtest-20260815.md` · `scripts/lp_dynamic_range_backtest.py` |
| **期现套利成本模型**（主流币空间恒负 -27~-32bps，持续性过滤） | `notes/basis-arb-model-first-run-20260809.md` · `scripts/basis_arb_model.py` |
| **长尾币期现测试**（快照假象 vs 持续性：GOAT 54%★ / MEW 17%✗） | `notes/longtail-basis-test-snapshot-vs-persistence-20260809.md` |
| **BitMart 第一桶金**（充值时间差 alpha：确定性失衡时刻+提前埋伏） | `notes/bitmart-first-pot-alpha-20260809.md` |
| **期现套利隐藏爆仓机制**（1倍杠杆统一账户也爆 + 振幅过滤双刃剑） | `notes/basis-arb-hidden-blowup-and-amplitude-filter-20260809.md` |
| **共学增量笔记 108 篇消化**（SVR/Atlas：Aave L2 已切 SVR 喂价 89% 清算奖励被回收→清算哨兵 aave 优先级有机制级证据；LVR σ²/8 与 LP 回测互证；RPC 新鲜度 vs 延迟双维度验证 rpc_health；Qy 庄家行为三层研判；ARK 9/16 主网上线新公链窗口） | `notes/icl-incremental-notes-digest-20260815.md` |
| **Bitget 资金费逃票查证**（官方规则+实测：主流币 8h 结算钳制 ±0.01%，往返费 0.12% 倒挂→100 期 0 期净正，逃票不成立；长尾币 4h 结算高费率全负费率=事件非策略；文档时点 07/15/23 vs 实测 08/16/00 差 1h——以 API 为准） | `notes/bitget-funding-fare-dodge-verify-20260815.md` |
| **资金费率信号方法论**（Z-score + OI 交叉） | `notes/funding-rate-signal-engineering-20260808.md` |
| **币股时钟差**（闭市漂移→开盘收敛） | `notes/tokenized-stock-arbitrage.md` |
| **监控脚本全家桶**（8 个哨兵） | `scripts/` + `daily/2026-08-08.md` 总结 |
| **公众号素材抓取**（直连免登录抓单篇→markdown+图片；search/list 代理模式需 down.mptext.top cookie，微信会话风险自担） | `scripts/fetch_wechat_material.py` |
| **去 AI 味写作桥接**（3 个 skill 不安装直接调用：human-writing 长文 / Humanizer-zh 编辑清理 / ljg-plain 概念解释，含硬规则+选择逻辑） | `templates/writing-skill-bridge.md` |
| **自建节点/基建验收清单**（延迟/吞吐/一致性/资源） | `notes/node-infra-acceptance-checklist-20260808.md` |
| **Solana 研究线**（Rust 双实现 + 执行层监控） | `scripts/solana-rs/`（quote/build/swap/spread）· `scripts/solfi-sim/`（LiteSVM 模拟器，含 slippage 完整环）· 执行层 5 哨兵：`priority_fee_monitor.py`（竞价）· `jito_bundle_monitor.py`（MEV tip）· `drift_funding_monitor.py`（链上 funding）· `failed_tx_monitor.py`（失败率）· `jupiter_route_monitor.py`（路由变化）+ `execution_quality_tracker.py`（达成率） |
| **Jito Bundle mainnet 首笔落地**（D11/D12 主线：bundle_id 0302a15a confirmed；两坑=encoding 参数缺失（默认 base58）+ tip 太低（1000~100000 lamports 全 pending/Invalid，0.005 SOL > 99 分位才落地）；8 轮排查方法论=对照实验隔离 bundle 路径 + tip_floor 分位数定价；脚本已修复可复跑） | `notes/jito-bundle-mainnet-first-land-20260815.md` · `scripts/jito_bundle_demo.py` |
| **Jito Bundle 管线 v2**（D12 升级：demo→参数化管线——tip 自动定价（现场查 tip_floor 99分位×1.5，下限 0.003/上限 0.01 SOL，实测 tip_floor 2 分钟内 0.0009→0.0035 动态变化）；JSONL 结构化日志 data/jito_bundle_log.jsonl；状态机 getBundleStatuses+getInflightBundleStatuses 双查三态区分；--n-tx/--tip-mode/--dry-run 全参数化） | `scripts/jito_bundle_pipeline.py` |
| **Jito Swap Bundle 首笔落地**（D13 主线提前：真实 swap bundle——0.01 SOL→USDC confirmed bundle 2248d538；**核心坑：build v2 手动组装 simulate 通过但 Jito Invalid，官方 /swap/v1/swap 端点+重签名一次成功**；官方端点返回未签名交易需 VersionedTransaction(tx.message,[kp]) 重建；LUT 解析三连坑最终用 Jupiter 响应自带地址列表；simulate 需 replaceRecentBlockhash） | `notes/jito-swap-bundle-first-land-20260816.md` · `scripts/jito_swap_bundle.py` · `data/jito_swap_log.jsonl` |
| **D12 广度回顾：D8-D11 一句话判断**（mempool 排序层=🔴放弃项 / perp funding=🟡观察线 / 聚合器=🟡工具非赛道 / LP 动态调区间=🟢唯一实测方向；横切结论=常驻价差被磨平、肉在事件窗口；喂 D14 三选一决策） | `notes/week2-breadth-review-20260816.md` |

## 📈 实测发现（2026-08-08）

- **主流币跨所价差已被磨平**：BTC/ETH/SOL 毛价差 <2bps，扣成本后净收益恒负 → 跨所搬砖无机会
- **币股闭市漂移真实存在**：美股闭市时 gate 币股普遍溢价 30-100bps（MCDX +103bps）
- **同链跨 DEX 价差 17-20bps**：Raydium vs Jupiter 最优路由（SOL/USDC）——Jito 原子套利的数据基础
- **失败交易反推法**：RHC 机器人失败 tx gasUsed=74643、$0.0045，证明「链下模拟器」才是护城河

# 链上套利残酷共学笔记

这是 2026 年链上套利残酷共学的工作笔记项目，用来沉淀资料、想法、打卡、策略假设、Hermes 工作流和后续自媒体草稿。

## 核心定位

这不是固定课表的课程，不是喊单群，也不承诺收益。它更像一个自学和交流环境。

目标是借助 Hermes、ChatGPT、LI.FI、The Graph、交易所数据、DEX/perp 数据和公开资料，搭出一套个人套利研究流程：

- 找潜在的信息差和市场结构差
- 把想法变成可验证假设
- 计算真实执行成本
- 写数据采集和监控脚本
- 做回测或 Paper Trading
- 记录失败并更新框架
- 在机会到来前，把系统提前准备好

## 当前判断

套利通常是薄利高频、低回撤逻辑，不是行情一来就自动印钱。

跨所套利已经被大团队、交易所优势、API 权限、同机房机器和内部流动性挤压得很厉害。链上 DEX/perp 相对开放，但延迟、滑点、Gas、MEV、合约风险和执行失败都必须算进去。

对个人研究者来说，第一问题不是“怎么更快”，而是：

> What is my edge?

如果 edge 不是速度，也不是深基建，就要去找市场理解、信息差、新资产、新规则、新路径、RWA/币股、预测市场 LP、链上 perp，以及还没被充分研究的工具机会。

## 目录结构

- `notes/`：长笔记和阶段性思考
- `notes/solana/`：Solana 单独研究线
- `daily/`：21 天共学打卡
- `templates/`：打卡、研究、策略、自媒体模板
- `sources/`：资料链接和来源记录
- `hermes/`：Hermes 工作流和提示词
- `social/`：X、长文、公众号、Newsletter 等草稿
- `obsidian/`：Obsidian 知识库对接方案和 MOC 模板

## 每日流程

1. 选一个小问题。
2. 让 Hermes 帮忙找资料或拆任务。
3. 尽量用官方文档、源码或直接数据验证。
4. 写下假设、成本、风险和下一步。
5. 在共学官网发一版短打卡。

如果当天内容值得长期沉淀，再整理一版到 Obsidian：保留来源、标签、假设、证据、下一步，并链接到相关市场、协议、策略或工具页。

## Solana 支线

Solana 单独作为一条研究线：先研究交易结构、DEX/perp、Jito/MEV、priority fee、CU、数据索引、RPC/Geyser 和路由聚合，不急着实盘执行。

入口：[notes/solana/README.md](notes/solana/README.md)

官网打卡入口：

https://intensivecolearn.ing/programs/b43d2e97-ed88-4ca3-b12f-7ef672b01205
