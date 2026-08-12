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
| **链上取证方法论**（怎么分析一个套利地址） | `notes/aave-liquidator-0x8d64d775-address-research-20260808.md` · `notes/robinhood-arb-0xd7121208-address-research-20260808.md` |
| **赛道选择结论**（清算/原子/跨链怎么选） | `notes/arbitrage-track-selection-20260808.md` |
| **风控总纲**（套利=概率游戏，敞口控制生死线） | `notes/arb-risk-black-swan-20260809.md` |
| **137 篇增量批次消化**（LI.FI 0.25% 成本地板 / 无套利带 / Robinhood V4-hook 开窗根因 / 0xd712 失败成本门槛公式 / Solana LP 集中度） | `notes/colearn-incremental-137-digest-20260810.md` · `sources/残酷共学_增量笔记_带索引_20260809.pdf` |
| **Day 6 报价对比实验**（L0006：Base→Arb USDC 三档×三桥；无规模折扣 25bps 恒定 + 快6s≈1bps + 「时长假象」across 100k 档 1s→900s）⚠️ **2026-08-12 复测勘误：25bps 是默认参数渠道费，带 `integrator=jumper.exchange` 全档归零（socket/lifi 照收）→ 跨链门槛下移 25bps** | `notes/day6-lifi-quote-compare-20260810.md` · `scripts/day6_lifi_quote_compare.py` · `notes/l0006-integrator-retest-20260812.md` · `scripts/l0006_integrator_retest.py` |
| **验证日：066+128**（066 最小价差公式复算：EVM 0.6114% 精确复现、Solana priority fee 30h 全 0 → 门槛=费率地板 Raydium 0.50%；128 WETH/USDG 双池核验：深池 0x52e65B 3.04e18 vs 浅池 0xb2a6aD 5.82e15 = 522 倍，bot proxy 0x19c8 吻合） | `notes/backtest-verify-066-128-20260810.md` · `scripts/066_smin_recalc.py` · `scripts/066_smin_recalc_fee_sweep.py` |
| **网格策略趋势市回测**（「在金」1300U 幸存者偏差验证：OKX BTC 1h 13 个月，下跌月亏损率 88% vs 非下跌月盈利 100%；0 手续费仍净亏 → 趋势月库存浮亏>震荡月 gross edge；10x 杠杆 -10% 月即爆仓；手续费 vs 格距生死线 = L0007 成本拆解落地） | `notes/grid-trend-backtest-20260811.md` · `scripts/grid_trend_backtest.py` · `data/grid_monthly_backtest.csv` |
| **Day 7 全景笔记**（认知主线：看起来赚了≠真的赚了——网格1300U/Polymarket榜一/gas反杀/OPENAI假价差四案例→5问筛选框架；工程7项全跑通；研究线#13/#14；广度14条归档；明日D8衔接） | `notes/day7-complete-20260811.md` |
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
| **Day 7 增量精华**（052 库存再平衡后净 Edge 仍负 -196~-221bps·三处互证 / 064 integrator 参数让 25bps 平台费归零·L0006 需复测 / 098 TUT 插针实证·20% 筹码转 Bitget / 132 六策略回测·LINK 快桥唯一正夏普 0.62 / 130 论文修正·清算人 183+ 中位 $20K / 126 HIP-3 股票永续 20 只） | `notes/day7-incremental-digest-20260811.md` · `sources/残酷共学_增量笔记_带索引_20260811.pdf` |
| **下架合约价差套利**（群策略实证：HFT 439bps + OI 累计偏离 + L/S ratio 净方向） | `notes/binance-delisting-arb-verified-20260809.md` · `scripts/binance_delisting_review.py` · `scripts/delisting_monitor.py` |
| **拍卖类调研（Maker LIQ2.0）**（空白候选补齐：Dog→Clipper 荷兰式拍卖、零 DAI flash-callee 参与、实测全系统 0 活跃拍卖 + ETH-A 最近活动 2026-06-05、新 7 参事件签名避坑） | `notes/maker-liquidation-auction-20260810.md` |
| **拍卖哨兵 v1（Maker Clipper）**（LIQ2.0 调研落地：IlkRegistry.list() 动态拉 35 ilk → Dog.ilks 拿 clip → Clipper.count() 轮询，>0 即告警+sales() 明细；多 RPC fallback 防限流；cron 每 30 分钟） | `scripts/maker_clipper_sentinel.py` · `data/maker_clipper.db` |
| **D9 预习：CLMM 集中流动性**（tick 与价格 P=1.0001^tick；虚拟储备公式 x=L(1/√p−1/√pb) y=L(√p−√pa)；Raydium 储备实测资金效率 X21.5x/Y19.5x；出区间=单边资产=网格穿界风险的 AMM 版；可视化 `data/clmm_visual.png`） | `notes/amm-math-clmm-preview-20260811.md` · `scripts/amm_clmm_visualize.py` |
| **期现套利成本模型**（主流币空间恒负 -27~-32bps，持续性过滤） | `notes/basis-arb-model-first-run-20260809.md` · `scripts/basis_arb_model.py` |
| **长尾币期现测试**（快照假象 vs 持续性：GOAT 54%★ / MEW 17%✗） | `notes/longtail-basis-test-snapshot-vs-persistence-20260809.md` |
| **BitMart 第一桶金**（充值时间差 alpha：确定性失衡时刻+提前埋伏） | `notes/bitmart-first-pot-alpha-20260809.md` |
| **期现套利隐藏爆仓机制**（1倍杠杆统一账户也爆 + 振幅过滤双刃剑） | `notes/basis-arb-hidden-blowup-and-amplitude-filter-20260809.md` |
| **资金费率信号方法论**（Z-score + OI 交叉） | `notes/funding-rate-signal-engineering-20260808.md` |
| **币股时钟差**（闭市漂移→开盘收敛） | `notes/tokenized-stock-arbitrage.md` |
| **监控脚本全家桶**（8 个哨兵） | `scripts/` + `daily/2026-08-08.md` 总结 |
| **公众号素材抓取**（直连免登录抓单篇→markdown+图片；search/list 代理模式需 down.mptext.top cookie，微信会话风险自担） | `scripts/fetch_wechat_material.py` |
| **去 AI 味写作桥接**（3 个 skill 不安装直接调用：human-writing 长文 / Humanizer-zh 编辑清理 / ljg-plain 概念解释，含硬规则+选择逻辑） | `templates/writing-skill-bridge.md` |
| **自建节点/基建验收清单**（延迟/吞吐/一致性/资源） | `notes/node-infra-acceptance-checklist-20260808.md` |
| **Solana 研究线**（Rust 双实现 + 执行层监控） | `scripts/solana-rs/`（quote/build/swap/spread）· `scripts/solfi-sim/`（LiteSVM 模拟器，含 slippage 完整环）· 执行层 5 哨兵：`priority_fee_monitor.py`（竞价）· `jito_bundle_monitor.py`（MEV tip）· `drift_funding_monitor.py`（链上 funding）· `failed_tx_monitor.py`（失败率）· `jupiter_route_monitor.py`（路由变化）+ `execution_quality_tracker.py`（达成率）|

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
