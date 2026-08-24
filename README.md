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
| **AI Agent 工作流工具观察：Ailu + 微信 CLI 情报库**（Ailu=Obsidian Agent 创作中枢已开源 AGPL：CC Switch 统一配置/手动沉淀记忆/本地预览公众号+X 上传 5:2 封面与 25 图限制/Cloudflare Tunnel+腾讯云东京固定 IP 绕开备案；微信 CLI 预告开源含 AnySearch KOL 推广待核验；wechat-relay 架构对 Agent×Payments webhook 有复用） | `notes/ai-agent-workflow-tools-20260821.md` |
| **QQQ/TQQQ 十五年核验：数字真实逻辑有诈**（yfinance 实测 QQQ +1512%/年化 20.4% 吻合、TQQQ 229x 属合理区间偏保守；硬伤=起点即答案/−79% 回撤反人性/卖保险文导向券商流量；对照系=QQQ 是被动基准 20%、TQQQ 是每日重置复利极限=赌单边与我们吃横盘相反） | `notes/qqq-tqqq-15yr-verify-20260821.md` |
| **陈皓《如何超过大多数人》digest**（思维模型类分享：反向陷阱清单 14 条自查 + 认知→知识→技能→领导力四层超越模型；与共学机制映射：费曼复述/知识图谱/证据体系=对抗碎片化·收藏家·「知道≠做到」三大坑） | `notes/coolshell-outperform-most-people-20260821.md` |
| **资金费套利执行认知**（Paxon 群分享：利润=费率收入−价差恶化−手续费−滑点；费率=慢变量/价差=快变量→价差是生死线；机器执行=价差恶化即跑人只定阈值；当前场景「价差5点+费率差1h1点」双模式：套收敛/套费率；混合模式=风险叠加非对冲） | `notes/funding-arb-execution-delta-spread-20260821.md` |
| **RISE 链生态应用首波上线**（Galaxy 支持的 ETH L2「交易链」（Vitalik+Stani 站台）：订单簿=原生 EVM 原语/5 Ggas·50k TPS·1ms 更新；RISEx=全链上订单簿 perps（portfolio margin/AutoYield）；=HL 直接竞争者（三板斧可迁移）+跨所价差候选（观察级）；附带：x402 官方数据 2 亿笔/$50B 量） | `notes/rise-chain-ecosystem-20260821.md` |
| **Solana Explorer 新功能（@solana_devs 87.9k）**（Verified Programs 搜索 + 原生程序 IDL 包 + RPCv2 指令预览 + Verified Builds V2——取证效率提升：未知名程序直接查 IDL/搜索验证；工具类更新无策略含义） | `notes/solana-explorer-update-20260821.md` |
| **Ramp × x402：Agent 支付接入企业账本**（@solana 官方 BREAKING：agent 钱包注资 + x402 支付 + 企业级记账/支出控制；x402 已结算 3500 万+ 笔=生态非概念验证；🔴 直接相关 Paxon 的 Agent×Payments Hackathon 方向=「可审计结算」层现成组件，做架构时直接参考） | `notes/ramp-x402-agent-payments-20260821.md` |
| **扫链方法论（HunterOnlyETH 32.8k）**（meme 扫链两维度=速度×准确度（反应力+中英阅读理解）；纪昌学射三阶段练习=不断练习琢磨反思迭代；真实经验=与母语英语者比扫链的劣势/新市场前十天空窗；对我们的映射=速度=延迟竞争（BAM 35ms）/准确度=付费方五问，「机器执行+人定阈值」比单人扫链更结构化） | `notes/chain-scanning-method-hunter-20260821.md` |
| **VolaSet 协议观察 + Solana 官方两帖**（VolaSet=波动率结算基础设施化（任何 ERC-20 建 Pool/Pool Edge 0-5%=统计优势）=卖保险家族新样本（观察级）；@solana 官方：①Solana School 秋季班（8/31-10/16 可申请）②新韩资管 KRW 代币化基金（BUIDL 模式，四方 MOU=Solana RWA 生态扩张=币股方向宏观利好）） | `notes/volaset-solana-official-20260821.md` |
| **Jito BAM 拍卖 50ms→35ms 变更**（核验生效：getEpochInfo epoch=1020 进度 12.1%=已生效；背景=350ms 时隙时序；**Block Engine 拍卖仍 50ms=我们 pipeline 不受影响**；未来接 BAM 需适配 35ms 窗口；BAM=块空间拍卖重构（SEV-SNP/第三方节点扩展期）；350ms 时隙=延迟竞争升级） | `notes/jito-bam-35ms-20260821.md` |
| **SOL 巨鲸浮盈核验——软造假第三例**（Ai 姨帖：SOL 20x 51.7 万枚持仓/浮盈 596 万全真，但 totalRawUsd=-3870 万累计亏损被隐藏（净亏 3270 万）；与 HYPE(-8368万)/ETH(-2907万)同款套路=「浮盈真+累计亏隐藏」是巨鲸浮盈帖标准手法；HL 三板斧 10 秒定生死） | `notes/sol-whale-verify-20260821.md` |
| **实操第一课：从「牛市来了」到完整筛选流水线**（Paxon 要实操：全市场扫描 960 币无合格候选→BTC/ETH/SOL 费率 0.01%/8h 年化 11% 离进场线差 5 倍→$10K 算账回本 4 天=给交易所打工→BTW7 面板否决（四所无现货只能裸空）→COINX 否决（Gate 受限+深度 $1.8K 玩具仓）→bStock 线可用（COIN +222bps 是合理定价非错价，机会在开盘收敛异常）；沉淀进场三条件+操作五步；新上线 bstock_conv 开盘收敛监控（周一至五 21:00-22:55 每 15 分钟，≥150bps 才推）） | `notes/first-sf-trade-rehearsal-20260822.md` |
| **D18 回测报告：跨池价差 12 天正式回测**（2608 行数据：双腿成本 50/60/80bps 胜率 29.9%/13.0%/0.0%、p50 利润全负、累计回撤 -2.9 万 bps；12 天无一次 ≥80bps；事件窗口标注=08-15/16 频率 3 倍但幅度上限没变→事件窗口子假设出局；常驻跨池价差正式出局，保留跨链/事件驱动/费率窗口） | `notes/d18-backtest-event-window-20260822.md` |
| **D19 四方向深度对比表 v1**（原子套利/币股RWA/资金费率/跨链全景对照：①费率事件窗口＝②币股闭市漂移 > ③跨链 > ④原子套利；原子套利排除（竞争门槛=延迟/排序权非资金，无个人edge，错误单思想由异常挂单雷达承接）；币股因 HIP-3 pre-IPO 新战场+SEC 批代币化股票升并列 P0；9 月阶段 2 从费率双模式判定开始） | `notes/d19-four-direction-comparison-20260823.md` |
| **币安 ETF 合约套利全思路（JXiaoLoong 78 段长文）**（杠杆 ETF 与其标的「每日涨幅差」套利：做多 ETF + K 倍做空标的赌收敛；每日 4 点重置跨天不回归；**周末无 AP 抹平+无重置 = 黄金窗口（最多 3 天等收敛，极端 4%+）**；资费差套利 K 倍修正 a%−K×b%；SOXL/SOXS 重置前 1.5% 无法回归被没收=越近重置风险越大；实盘 1000+u 自述未验证；与 bStock 闭市漂移/TQQQ 每日重置互证） | `notes/binance-etf-contract-arb-20260823.md` · `scripts/binance_etf_spread_monitor.py` |
| **成本模型模板 v1（含 gas 语义检查）**（8 项成本清单：gas/协议费/桥费/滑点/资金费/提币/预付bid会计陷阱/失败重试；gas 语义检查表=052 Monad 教训（gasLimit 退回？最低 gas price？状态延迟？bid 不算利润守卫？）；统一公式 净收益=屏幕价差−Σ成本−安全缓冲；使用记录表 08-07→08-23 五案例） | `notes/cost-model-template-gas-semantic-20260823.md` |
| **群分享五连核验（Lighter V0.3.1/套利筛选法/PM窄赛道/标的归集/逆势资金配置）**（Lighter 无 LICENSE 不装；traderwanwan 四档收益枚举法（极佳/普通/差/黑天鹅）吸收；PM 窄赛道案例 referral 打折；CryptoPainter 逆势加仓不照搬（先回测铁律）；共同信号=低竞争窄赛道+严格筛选+归集先行印证 D19 方向） | `notes/group-share-five-verify-20260823.md` |
| **群分享三连核验（ETF套利/a-stock-data/Pendle Boros）**（a-stock-data 验真（Apache 2.0+SKILL.md，帖子数字过时 13→19 源）不装（A 股不在赛道）；Pendle Boros OCR 验证=费率/cash carry 一键包同赛道竞品不装；共同信号=三条独立指向费率/股票套利事件窗口，印证 D19 P0） | `notes/group-share-triple-verify-20260823.md` |
| **48K纯白 支撑压力位教程**（技术分析备查：支撑/压力是「反应区域」不是墙；图表记忆/位置互换/测试次数≠强度/到压力先看反应再决定；与执行框架互补（人定阈值部分的技术面输入），不引入方向交易） | `notes/support-resistance-tutorial-20260823.md` |
| **qinbafrank 加密供给侧改革 + SEC 代币融资豁免**（8/19《Regulation Crypto Assets》：covered investment contracts 专门发行路径（启动豁免 $500万/4年、融资豁免 $7500万/年）+ 条件性安全港；= 优质资产供给增加，空气币空间被挤压，跑路成本上升；与 SEC 批代币化股票/HL Tokenized Equity $465M 合并为「美国监管拥抱加密资产证券化」证据链，币股 RWA 线长期顺风） | `notes/sec-supply-side-reform-20260823.md` |
| **Hermes + Tailscale 服务器初始化工作流（brucexu.eth）**（新服务器 5 分钟两步：装 Tailscale 接入内网 2 分钟 + 告诉 Hermes 按功能初始化 3 分钟，自动化完成安全加固/最佳实践/监控；关键=凭 Tailscale 内网身份互信，无需来回传 Key——与安全铁律（密钥不明文传）互证；多服务器场景备查） | `notes/hermes-tailscale-server-init-20260823.md` |
| **taoli tools 实操认知（Paxon 花一天研究）**（「大部分时间不成交」=常驻价差磨平直接证据（D17/D18 互证）；「适合大资金做年化」=卖保险容量逻辑（净年化 4-10%=现金管理，小资金无意义）；「大波动才成交」=事件窗口才是肉；**第 10 个角度：工具成交率=市场有效性/波动窗口温度计**——不部署（年化向≠我们阶段），但可当波动窗口 signal） | `notes/taoli-tools-practice-cognition-20260823.md` |
| **Term Finance 治理攻击链上取证（~$8.5-9.3M）**（**金库份额质押投票权俘获**：$951 买 0.4852 股份额质押拿 90.66% 投票权（质押供应量仅占总供应 0.019%，99.94% 持有者从不质押）；TokenVoting 恶意提案→对每个独立金库逐个提款（Tx1 pcETH 2,841 WETH $6.8M + Tx2 pcUSDC/pcHYUSDC $2.5M）；与 BonkDAO/Compound 同族但**成本低 5000 倍**（投票参与率≈0 是根本）；待办=事件雷达加治理攻击类别+质押率检查清单） | `notes/term-finance-governance-attack-forensics-20260823.md` |
| **Crypto老鹰 PM 5min 脚本推广核验（返佣矩阵#1）**（repo Novals83/5min-btc-polymarket 真实但**无 LICENSE 不装**；300→14000 叙事未验证；5min 盘「最后 2 分钟进场/顺势/95-5 反向微仓」=runes_leo 赢家研究变体；老鹰二次推广+双 referral=返佣矩阵实锤） | `notes/laoying-pm-5min-script-verify-20260823.md` |
| **runes_leo PM 赢家行为研究（14,441 地址筛出 12 赢家）**（三套 PnL 口径交叉核验；**赢家分三类**：两侧做市（smalltimezzz 月 10.7 万笔 taker 1%）/ 最后半天 pace 方向（EffyBig taker 91%）/ 早进场铺仓砍仓（PredictionYogi 23 次亏损退出）；**48h 盘占部署 44-67%**=结算周期快=验证快；12 赢家合计月 PnL 仅 ~$8 万（单人天花板低）；方法论=先分赢家类型再优化，别混两种 edge） | `notes/pm-winners-behavior-20260823.md` |
| **Hermes + Telegram 多任务工作台（brucexu.eth）**（Desktop 非 macOS 版；channel 右键开新窗（从消息开会焦点锁定）；27 寸 4K 一屏四列 + Rectangle 快捷键；**4 并发任务=上限**（瓶颈在人不在 Hermes）；我们就在 TG+Hermes 环境可直接套用，工作流优化备查） | `notes/hermes-telegram-workstation-20260823.md` |
| **Crypto老鹰 PM 15min BTC 助手推广核验（同日第 2 条）**（repo 真实 861★ 但**无 LICENSE + 创建当天后 8 个月无更新**半成品；单日 $5 万/98% 胜率无独立验证；「币安行情延迟价差」思想=我们 D18 事件窗口的时间维版本（同 ETF 涨幅差/闭市漂移：同一资产两市场定价不同步）；老鹰同日双条推广+同 referral=返佣矩阵实锤） | `notes/laoying-pm-15min-assistant-verify-20260823.md` |
| **0xPINK3 PM 量化战绩（$130,992/132天）**（自述未验证打折看；**「仓位构建>胜率」增量认知**：50% 胜率够用、逐步构建仓位、先一侧敞口有利再补反向对冲锁定——与 runes_leo 赢家三类「早进场铺仓+砍仓」完全吻合，与我们「期望>胜率」一致；PM 涨跌盘市场热度真实=老鹰推广同市场对照） | `notes/pm-position-building-20260823.md` |
| **CryptoRounder 偏度/曲率交易跑赢 BTC**（短帖未给机制；映射=**事件窗口是尾部的收益化**（我们的事件驱动=偏度交易现货版）；币本位口径=「vs BTC 持有」可作回测新基准；无直接可执行项，D19 对比表 v2 候选） | `notes/skew-kurtosis-trading-20260823.md` |
| **财经老王 PM 极简重注案例（$500→$177K/64笔）**（只等高度确定+重仓$5-10万+电竞/网球窄赛道+吃定价偏差持有至终场；**「确定性>出手次数」第 3 次互证**（taoli 不成交/runes 12 赢家/本案例 64 笔）；电竞盘=未覆盖的低竞争细分；但重仓无护栏=幸存者偏差极端样本，我们用 execution_guard 保险丝；referral 推广打折） | `notes/pm-concentrated-betting-20260823.md` |
| **Crypto老鹰 PM 新闻套利推广核验（同日第 3 条）**（「新闻→概率变→订单簿滞后 30-90 秒」=**时间差套利家族第 5 案例**（闭市漂移/ETF重置/币安延迟/下架事件）；ΔP=α·news·e^(-λt) 机制真实但 α/λ 标定才是核心帖未给；月 5-7 万与 #2 帖单日 5 万互相矛盾；**老鹰同日 3 连推+同一 referral=内容农场级返佣矩阵**） | `notes/laoying-pm-news-arb-verify-20260823.md` |
| **Zcash 屏蔽池数据爆炸（Paxon 核验✅）+ 特朗普账户程序化交易（WSJ）**（Zcash nullifier 集合/commitment tree 只增不减、UTXO 不能丢弃=隐私链状态膨胀难题（Ztreexo 提案未落地）；评估隐私链须查状态增长模型；特朗普账户月 1000+ 笔=程序化交易实证，反衬加密常驻价差磨平 vs 股票流动性深——强化「肉在事件窗口」） | `notes/zcash-state-bloat-trump-trades-20260823.md` |
| **Solana 官方周报（2026-08-23）**（**币股 RWA 线 3 连击**：$LLY/$MRNA 股票代币上线（Backpack 发行）+ Shinhan KRW 代币化基金 + Securitize×Neuberger $230B HINC；**350ms slot 首次削减**（Jito 竞争窗口变短，D20 评估）；币股线宏观利好第 4 条证据链，标的池扩张） | `notes/solana-weekly-20260823.md` |
| **Solana 原生币股 LLY/MRNA 价差核验**（Backpack 发行真 RWA（1:1 可赎回）非合成；快照 LLY -26bps / MRNA +210bps 但**深度玩具仓**（流动性 $150-300K、24h 量 <$23K，距 $1M 门槛 30-100 倍）+ 周六闭市漂移非错价 = 不进场；MRNA 日线跟随美股收敛健康；jup.ag 全系 TLS 挂 → DeFiLlama+GeckoTerminal 新数据源路径；**已部署开盘收敛 watchdog**（cron 1da3deea43ef，周一至五 21:00-22:55）） | `notes/solana-native-bstock-lly-mrna-20260823.md` · `scripts/solana_stock_convergence_watchdog.py` |
| **今日分享批量归档：量化工具+交易哲学+生态观察**（HL 订单生命周期面板=NautilusTrader 26k★（研究=生产）/ Hermes 自进化生态（观察）/「犯错少=高手」=错误单线互证 / Lighter 价差套利工具 V0.3（同方向实证，不接入只借鉴）/ 行情频道推荐=监控覆盖度自检通过） | `notes/daily-share-archive-20260822.md` |
| **错误限价单事件：别人的错误=我们的猎物**（1inch 用户挂限价单忘关，转币瞬间以低于市价 5-6% 成交亏 300U；Paxon 观点「有人犯错就有套利机会」→ 提炼错误单雷达三档：CEX 深盘僵尸单（可立即做）/Solana 订单簿 DEX/暴涨触发窗口；泼冷水=单子存在时间极短必须机器扫，本质是价差唬人镜像） | `notes/mistaken-limit-order-arb-line-20260822.md` · `scripts/anomalous_order_radar.py` |
| **周会实录：TUT 爆仓一手复盘 + 群友策略地图**（Ethanlxl 复盘 TUT/BICO 狗庄屠宰=费率诱导→时仓积累→几分钟拉 50-80%→爆仓→BG/GT 罕见赔付（按爆仓前 3 点价）；「压路机前捡钢镚」/杠杆 0.2-0.5x 才安全/价差 50-80% 捡尸体=一单顶三月/币安限制开仓=最强信号；king W3 USD 荷兰拍吃磨损（公开即死）；feiye 废弃合约捡漏（无机器人竞争）；=执行框架实盘验证+新候选方向） | `notes/weekly-meeting-tut-postmortem-20260821.md` |
| **DUSD 地址核验**（MachineShare 合约=Makina Finance 收益稳定币份额（USDC 记账/queued exits）；价格 $1.036 溢价 3.6% 但 24h 量仅 $19.5+退出排队=账面溢价不可套；ATH $1.39→1.036 溢价是波动非稳定；与 sUSDe/USDL 同族；地址核验流程跑通：RPC code→blockscout 合约名→CoinGecko 市场→Pharos 画像） | `notes/dusd-addr-verify-20260821.md` |
| **Aave V3 批量清算取证 + 龙王地址核验**（ETH 交易=闪贷清算 bot 一笔清 6 仓位（LiquidationCall 指纹+0.1gwei flashbots+dust 全清），=我们清算方向实证样本；龙王=真实盈利账户（累计+210 万，BTC 长空吃资金费+CXMT/UNITREE pre-IPO 主战场），「资金费吃得比仓位大」=套费率不套方向活案例） | `notes/aave-v3-batch-liquidation-forensics-20260821.md` + `notes/dragon-addr-verify-20260821.md` |
| **巨鲸情报/浮盈双核验**（Ai 姨 135k 囤 ETH 情报=链上余额当场验证 ✅ 真（3092/7201/1045 ETH 全吻合）但本质=情报+Bitget 广告；鸟哥 ETH 巨鲸浮盈=同 HYPE 帖同款软造假（浮盈 918 万真但累计亏 2907 万隐藏）；方法论=情报帖查余额/浮盈帖查 totalRawUsd） | `notes/whale-intel-verify-20260821.md` |
| **桂林交易心法 + 普通人量化路线图**（qinbafrank 154k 引陈桂林：系统战胜不了人性/最完善系统=最大限度战胜情绪/技术简单控制最重要=机器执行人只定阈值同构；Mr.RC 5984 likes 长文：五阶段数学底座（概率→统计→线代→凸优化→随机微积分）+「估计误差是敌人/工具民主化确信度没有/数学是护城河」；阶段5=币股期权前置课程） | `notes/guilin-trading-mindset-quant-roadmap-20260821.md` |
| **金融知识体系终极指南 digest**（Vincent 1.2 万字六章：经济vs金融本质/基础产品+衍生工具四大特征（杠杆=合约价值/保证金、零和博弈例外=套保/做市/税收套利）/市场层级+监管/学习路径/2008 危机链/行为偏差应对；「为什么别人愿意和你交易」5 问=套利豪仔付费方+L0008 共识拥挤度同一核心=找付费方找限制；fxtwitter article.content 抓 X 长文方法） | `notes/finance-knowledge-system-digest-20260821.md` |
| **Crypto老鹰 PM「锁利机器人」核验——声称 vs 链上严重不符**（吹「12 个月 7877 笔 61.9 万刀」；Polymarket data-api 分页拉全量实锤：**全部 800 笔在今天 3 分钟内**（12:34-12:36）/活跃 1 天/总投入 $33,939/大量 $0.002 尘量单=批量撒单；返佣三件套（via=YINGGE888+PolyCop 跟单）与今日另 3 条 PM 推广同源=同一推广矩阵；YES+NO 锁利原理真实但竞争白热化；核验方法沉淀：proxy wallet+时间戳聚合拆穿长期盈利叙事） | `notes/pm-yesno-lock-verify-20260821.md` |
| **「信息差套利」5 仓库核验**（Sac 帖 1848 likes：5 repo 全真（remote-job 47.8k★/ai-money-maker 4.1k★/awesome-systematic-trading 13.5k★/goofish-monitor 14.2k★/TG 群 23k★）；但「套利」是泛化用词=信息差收集非真套利；唯一增量=goofish-monitor 监控架构作雷达 UI 参考） | `notes/info-gap-repos-verify-20260821.md` |
| **市场玩家结构与 Alpha 五来源**（套利豪仔 digest：三层结构=基础设施/Sell Side/Buy Side；Alpha 五来源=Risk/Liquidity/Funding Constraints/Predictable Flows/Informational Advantage；「报酬是谁支付的+他为什么愿意付」5 问验证法与 L0008 同构=认知层第三支柱；4 方向可逐个回答付费方） | `notes/market-structure-alpha-5-sources-20260821.md` |
| **PM 机器人叙事 ×3 + quant-trading 核验**（春日部彼得=同 repo 返佣推广变体（FrondEnt PM 助手，胜率98%+跟单bot 话术不采信）；WaveKing 交大学生=幸存者叙事（AI 补脚本短板案例+流动性异常停机可提取）；折耳根 quant-trading=10.6k★ 属实但公开经典无 edge；今日第四次验证公开策略=滞后信息） | `notes/pm-bot-narratives-quant-trading-20260821.md` |
| **BSC execute 闪贷还贷取证**（4byte 签名 `execute(uint256,uint256,uint256)`；**owner() 归属法**=to 合约 owner 是 from=用户自己的执行器；借 PancakeSwap LP 池 37.76 WBNB 闪贷凑抵押→全额还清 USDL→赎回 WBNB，LP 池持平闪贷费 0.01%；**闪贷≠套利**=用途决定性质） | `notes/bsc-flashloan-repay-forensics-20260821.md` |
| **BSC redeemCollateral 交易取证**（4byte 签名定罪 `redeemCollateral`=抵押品赎回非套利：540.556 USDL burn→0.919 WBNB 协议费 3.7%，无循环/闪贷/比价；BEP-20 Transfer 变体签名 `c2b068` 一字节差异坑；BSCScan V1 废弃走公共 RPC） | `notes/bsc-redeem-collateral-forensics-20260821.md` |
| **HIP-3 市场实测 + CSOP 海力士 ETF 套利**（OAK 直抓 119 市场/XYZ 占 100% 量；**跨 deployer 同标价差实测 <0.02% = 已磨平**（UNITREE XYZ vs Paragon 0.01%/SNDK XYZ vs Entropy 0.02%）——与 Solana 跨池同构，机会只在 pre-IPO 事件窗口（SPCX $177.9M OI 最大）；0xJA 海力士 ETF：弹性杠杆 7/27 生效/平均 1.8x/三时钟错位/swap 跟踪误差/1.6% 管理费=产品参数可改同族案例） | `notes/hip3-market-scan-csop-etf-20260821.md` |
| **HIP-3 Pre-IPO Perps + Entropy 核验**（NFTCPS 返佣推广帖：HIP-3 框架真实且巨大=$120-290B 累计量/Cerebras 定价<3%/Anthropic·SpaceX·OpenAI 都有 perps；但数字注水（50万 HYPE 按旧价 $62 折算，现价 $74）不采信空投叙事；=币股闭市漂移新战场+pre-IPO 事件窗口候选） | `notes/hip3-preipo-perps-entropy-20260821.md` |
| **群分享速记：十老板复盘 + PM bot 标题党核验**（十老板 1万→1.3亿八年复盘「留在牌桌上」=风控通俗版；NFTCPS 吹「PM 套利机器人公开」实为 FrondEnt/PolymarketBTC15mAssistant=TA 交易助手非套利bot，817 stars 真实但公开信号无 edge） | `notes/shiboss-pm-bot-verify-20260821.md` |
| **Hayden 相关配对 AMM + Cody 实测**（Hayden 2019 来首篇博客《Correlated Pairs》：相关配对降无偿损失/愿持有即免对冲；Cody NVDA/SPY 3 年实测无偿损失 -10.8% 需年化 11.5% 弥补=现阶段 LP 币股跑不通；SEC/DTCC 已批代币化股票=我们🥇币股线方向性利好） | `notes/hayden-correlated-pairs-amm-cody-20260821.md` |
| **Hermes 插件生态核验**（GitTrend0x 推 5 插件全真实：outsourc-e workspace 6.4k★/SkillClaw 2.4k★ 精品，jdtymothy 拼写笔误已修；装第三方插件先核验） | `notes/hermes-plugin-ecosystem-verify-20260821.md` |
| **Bruce 投资归因规律 digest**（X 帖：3 年样本归因——观点一致时不发生/没有永赚博主/稳定营收=耐心·不贪·独立思考·仓位·安全，归零=爆仓+被盗；L0008 5 问加第 6 问「共识拥挤度」；4 方向优先级定版：币股漂移🥇/费率事件🥈/消息下架🥉/清算4，常驻跨池出局） | `notes/bruce-investment-rules-20260821.md` |
| **D17 历史机会回测：跨池价差 11 天分布**（2408 行快照清洗 12 条损坏；**常驻价差=不可执行实锤**——无一次≥80bps，p50=34bps，双腿成本 50/60bps 下 p50 利润仅 5-8bps；机会在事件窗口不在常态；常驻跨池从 4 方向候选划掉） | `notes/d17-corridor-spread-histogram-20260821.md` |
| **awesome-systematic-trading 合集核验**（X lumxss 推广：97 库/40+ 策略/55 书/23 视频全属实；13.5k stars；价值=工具地图+回测框架选型，非策略金矿；最大可落地=Hummingbot Solana connector（做市）+ HFTBacktest（高精度回测）；先看能力缺口再对号入座） | `notes/awesome-systematic-trading-collection-20260821.md` |
| **Solana 盲套利 Bot 取证：R32xAccFis**（WEN 生态：自研程序 7obtMdiXQ + Orca + Meteora DYN + DLMM 多池；Custom 6004=利润保护主动放弃非 bug；75% 失败率是设计——每次探测 $0.0013 成功一次回本；18 slots 连发 20 笔=窗口内高频探测；circular.fi=Solana 版 Arkham） | `notes/solana-blind-arb-bot-R32xAccFis-20260821.md` |
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
| **无套利带雷达 v2**（Raydium 锚点校准：池 58oQChx 活跃确认；深度过滤=腿价偏离锚点≥300bps 标 suspect 不告警；Jupiter 池列表 API 不可用→偏离代理；实测全配对在走廊内，100 SOL 档 Raydium↔Quantum 61.4bps 顶到 60bps 走廊上沿；**v4 08-24 单一区块快照绑定**=044 纪律：每腿绑 slot+blockhash8，同源跨块=MISMATCH 强制 suspect，跨源只查陈旧（Helius/Jupiter 节点时钟偏差 50-180 slot 不可比），CSV 增 slot/state 列旧表头自动归档） | `scripts/no_arb_corridor_radar.py` · `data/corridor_series.csv` |
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
| **共学增量笔记 90 篇消化**（状态跳变=第10类机会、v3 腿 Quoter 纪律、LI.FI 路由每周翻转+L2 native USDC deny list、funding 躺平收租回测证伪+OI 过滤、HL 代币化股票结构性基差 52bps、天然价差中位数基线、ADL 剪刀仓风控） | `notes/icl-incremental-notes-digest-20260816.md` · `sources/残酷共学_增量笔记_带索引_20260816.pdf` |
| **共学增量笔记 91 篇消化**（RWA 基差套利框架=Tokenized Stock×HL HIP-3 log(P/X)分解+周末价格发现权争夺、资金费短窗口高估9.3倍+换手率判据、Monad gasLimit 不退回成本模型、测量自我污染滑点指纹 51bps 作废、原子性≠执行权竞价让渡95%、OEV/SVR 双聚合器机制、充提状态套利、机会评分可审计化、ADR 扩散vs收敛=强制收敛机制） | `notes/icl-incremental-notes-digest-20260817.md` · `sources/残酷共学_增量笔记_带索引_20260817.pdf` |
133:| **共学增量笔记 132 篇消化（08-22+08-23 两批）**（清算套利手册=Base/Morpho 唯一实盘证据链 81.7% 落袋率+预言机 30s 节奏可预测；竞品拆解=3.5 万区块还原 108 笔对手 tx 三差距；EV 模型=延迟 300ms 利润 0.95→0.11U；Jito 拍卖机制=50ms tick+锁冲突分组+tip/CU 排序；common-value 拍卖「成交了利润归别人」；starkxun 四周九方向零成立；报价须绑定 block_hash；ShredStream 09-05 下线迁 DoubleZero） | `notes/icl-incremental-notes-digest-20260824.md` · `sources/残酷共学_增量笔记_带索引_20260822.pdf` · `sources/残酷共学_增量笔记_带索引_20260823.pdf` |
134:| **小池价差持续性分析（Solana 线）**（14 天 2931 行 corridor_series：100 SOL 档频次重建深度阶梯 Raydium 964>HumidiFi 562>…>BinaryFi 3；11 个出轨事件全部单样本 ≤30min 消失、零持续出轨 → 「薄池价差持续更久」无法验证=常驻出轨不存在；与 D17/D18 互证机会只在事件窗口；CLMM/Whirlpool 千 bps outlier=薄池报价噪音） | `notes/solana/corridor-exit-duration-20260824.md` · `scripts/corridor_exit_duration.py` |
135:| **资金费双模式判定函数（D19 落地，71aef87）**（decision() 纯函数：套收敛/套费率/不进场/danger 风暴四模式 + stability<0.6 诱饵过滤；exit_rule 机器执行退出纪律=价差恶化≥费率积累×1.5；--from-json 批量 + --exit-check；已接 run_funding_spread.sh cron watchdog；08-24 Hermes 重复实现已删） | `scripts/funding_dual_mode_decision.py` |
136:| **Morpho prey radar v1（清算哨兵事件驱动化落地）**（预言机偏离扫描：GraphQL 拉市场含下架 → eth_call price() selector 0xa035b1fe（0x57e871e7 会 revert）→ DeFiLlama 现货 → deviation 分层 ≥2% INFO/≥5% SIGNAL/冻结论价机 BROKEN_ORACLE；**oracle 缩放=代币 decimals 决定**（18位→1e24/9位→1e33/8位→1e34/比值→1e36），候选档自动探测；**HERMES×24 下架市场冻结论价机埋雷实锤**（code 203B、price() 恒 1e45、lltv98%/util100%/名义供给$1.08B）；mGLO SIGNAL 638bps；24h 去重 watchdog cron 6c9d49f28ba7） | `scripts/morpho_prey_radar.py` · `notes/morpho-prey-radar-v1-20260824.md` |
137:| **Bruce 套利系列①：跨所反向对冲 digest**（四做法=两永续价差收敛/现货-永续基差/两永续资金费差/跨所库存套利 + 统一公式=两腿盈亏+实际资金费−手续费/借币/充提/调仓；「同 USDT 金额≠对冲」「库存调回成本最易漏」「预测费率非锁定收益」全部与库内互证；Taoli 推广打折看：免费 5ku 学习够、付费群=主要卖点、不装；下一篇 TUT 小额实操预告） | `notes/brucexu-arbitrage-series-1-reverse-hedge-20260824.md` |
138:| **0xBinTang PM 5 分钟涨跌盘双买套利**（Up 22.5¢+Down 59.8¢=82.3¢→兑$1 锁 17.7¢/对；92,344 次预测/$5,440 万量/$588,548 利润=转述未独立核验；机制真实=概率森林论文「~99% 机会未被执行」同族；**已落地检测器** `scripts/pm_binary_dual_buy.py`：slug={btc|eth|sol|xrp}-updown-5m-{窗口epoch}，ask-ask+taker费+容量门槛，实测常态互补定价≈1.0 无信号=稀有事件，cron 20995c6cc361 每 2min 攒频率） | `notes/pm-binary-dual-buy-20260824.md` · `scripts/pm_binary_dual_buy.py` |
139:| **跨所永续价差收敛率回测（Bruce 收敛假设实证）**（Bybit×OKX 14 天 4032×2 根：SOL/DOGE 价差 ±8bps 内零事件=被磨平；KAITO max 310.8bps 但 ≥30bps 事件 4h 严格收敛率 0%、收窄一半也仅 25-43%；**事件窗口版追加：12 个 5m 内 ≥50bps 瞬态突变 2h 严格收敛 0%、收窄一半 33%——事件驱动假设在 CEX 永续也被证伪**（DEX 有锚点拉回、CEX 两所各自价格发现无锚点）；**TUT(Bybit×Gate)反例：收敛率 ~100% = 庄家控盘拉回=屠宰场诱饵**；执行含义=反向对冲只做事件驱动或改套费率模式） | `scripts/cross_exchange_convergence_test.py` · `notes/cross-exchange-convergence-test-20260824.md` |
140:| **Morpho HF 清算触发扫描器（010 手册第 2 步）**（GraphQL marketPositions 持仓级 HF + priceVariationToLiquidationPrice 触发跌幅；**USDe→USDC $286M 抵押品贴清算线：跌 0.49% 触发 $14.85M、跌 1.83% 触发 $125M 鲸鱼仓、跌 2% 累计 $260M 连环**；mGLO $19.84M 与 prey radar SIGNAL 联动；与 prey_radar 组成预言机层+持仓层双哨兵；cron 4c26244b6d9e 每 30min） | `scripts/morpho_liquidation_hf.py` · `notes/morpho-hf-liquidation-scanner-20260824.md` |
141:| **群分享四连发核验**（①ai_quant_trade 6,347 星核实=股票 AI 库非加密，低优先；②HyperLiquid 实盘面板=订单生命周期可视化理念值得抄，HL 费率源可加监测；③PM 卖 No 机器人 $1万→$97.8万/90.2% 未核验=钱包未定位，机制与 RN1 053 互证（卖人群过度支付溢价），「卖 No 阶梯盘」列入 PM 线候补，作者自认非套利有尾部；④fomoscan=返佣引流不注册） | `notes/group-share-four-links-20260824.md` |
| **D14 第二周总结**（AMM 数学✓/模拟器✓/Jito pipeline 半完成自查：mainnet 闭环跑通待实盘纪律；周认知=常驻价差磨平肉在事件窗口、成本模型按链定制、测量自指污染否定、原子性≠执行权、币股线升级 RWA 基差；D15-D19 节奏调整表） | `notes/week2-summary-20260818.md` |
| **TencentDB Agent Memory 团队记忆 digest**（协作带宽=权限内可理解可用上下文；四类资产 Chat/Wiki/CodeGraph/Skill × L0-L3 分层 × 渐进式暴露；相关≠可复用 231/22361 强关系；逻辑返工1350>>缺上下文269；SWE-bench 60→80%自报需谨慎；六原则；与 Hermes memory/skills/session_search 对照=个人版已实践；qintopia 团队记忆蓝图） | `notes/tencentdb-agent-memory-team-memory-20260818.md` |
| **DSH 学习资源合集+插件清单**（姚金刚 12 篇资料书单=官方→Cordis 论文→机制→工程→生态；SuSu 20 插件分类=核心必备5+界面9+能力11+监控14+多Agent 17；Su 长文=四模式选型/一切皆插件 Cordis/创造模式三步/「创造模式不懂自己」早期信号；与 08-15 dsh 实操验证互证） | `notes/dsh-learning-resources-plugins-20260818.md` |
| **1inch Aqua 激励套利拆解**（X Article @NeoWeb3Nova：Aqua Maker/LP Incentive Program 奖励按 processed volume 分配非 parked TVL、1000 万 1INCH+50 万 USDC 池、wallet cap/wash-trading filter/自交易可暂停市场；@w3_888 两周 3 万 U 自述=Incentive Arbitrage 不是撸毛不是价差套利；「无风险」被作者自己纠正；与 08-16 w3_888 旧归档同一人 gross vs net 存疑） | `notes/oneinch-aqua-incentive-arb-20260819.md` · `sources/oneinch-aqua-incentive-arb-article-20260819.txt` |
| **宇树/长鑫 CEX vs 券商**（现金结算合成衍生品≠股票代币：oracle 参考价+USDT 对赌「股票猜涨跌」；时间线 7/14 HIP-3 Pre-IPO 5 美元→7/16 发行价 8.66 元→7/31 MEXC 先上→8/4 HL 开盘 73.33→币安最后；长鑫炒到发行价 6 倍/宇树 4 倍（市场隔离）；8h 资金费；纳斯达克 23h 制 12/6 上线；互证 083 RWA 基差+日书打新/Bybit 改参数） | `notes/cex-vs-brokers-stock-perps-20260819.md` · `sources/宇树长鑫币安合约_CEXvs券商_Clabs_20260819.txt` |
| **跨所资金费套利风控框架**（BTW 观察：+68.86% 暴拉/资费年化 124%/KOL 推广=收割前兆；SF 刚拉完基差虚高有风险、横盘吃资费最稳；CrossEx 跨所保证金实战参数——蚂蚁仓/抗 2 倍涨幅≈无杠杆/1 倍涨幅强平/U 本位/买卖一价；数学验证：保证金≥(1+MMR)×名义；TUT 剧本互证=正资金费率是诱饵，CrossEx 也防不了插针，2 倍杠杆照样爆；**合规风险=Gate 受限辖区含中国大陆/香港，CrossEx 方案挂起；BNC 实测否决=无现货/深度 $500 级/费率被操控**） | `notes/crossex-funding-arb-risk-20260820.md` · `scripts/funding_spread_scanner.py` |
| **聪明钱/钱包监控工具评估**（@WY_mask 6 工具对照自建能力：Arkham 免费层=实体归因补强 onchain-address-forensics 🟢；GMGN 胜率筛选借鉴 meme cohort 🟡；Nansen/Cielo/DeBank 与 whale_dump_radar/meme-dev 四本账重叠不订阅 🔴；Bubblemaps 可视化辅助；判据=能力缺口而非工具好坏） | `notes/smart-money-tools-eval-20260820.md` · `sources/smart-money-wallet-tools-20260819.txt` |
| **跨链套利：桥延迟+跨链 MEV**（D15 遗留广度：桥延迟三层=消息秒级/流动性分钟级/最终性小时级；实测对比 across 1s vs Stargate 1-3min vs OFT 1-2 USDC；L0006 时长假象互证；Wormhole 守护者 vs LZ oracle+relayer；跨链桥 exploit 占 Top10 一半=尾部风险；跨链 MEV=消息时机套利+求解器竞拍；结论=桥延迟是要建模的成本项非打败对象） | `notes/crosschain-bridge-latency-mev-20260820.md` |
| **群讨论蒸馏：资金费三大认知跃迁**（xtest「5x 杠杆日化 7.5%」=算术毒药：5x 强平距离 19.5% vs 山寨日波动 20-40%，真实净年化 4-10%=现金管理；TUT/BTW 屠宰场三件套=正资金费+山寨+KOL 喊单，CrossEX 统一保证金扛不住插针；单边暴涨里价差套利必死=腿不同步+滑点吃穿+中性策略退化单边押注残差即爆仓源；与我们的数学验证/L0008 #3 完全互证） | `notes/group-funding-arb-cognition-20260820.md` |
| **打卡日书 0817 补充 digest**（91 篇精选之外 93 章：HL funding 250 天回测 SOL −1.2% 净年化、Bybit 杠杆 ETF 改周期实证、OKX 闪赚 30%+ 互证、V2 大额利润非线性 $50K 转亏、出场用卖出时点储备、可执行利润漏斗 100K→980、LI.FI 拆账平台费占 87%、BigInt 精度模板、跨链 quote 比率≠现货价差） | `notes/icl-daybook-0817-supplement-digest-20260819.md` · `sources/残酷共学_打卡日书_提取文本_20260817.txt` |
| **Ponytail 规则分发机制拆解**（AI 编码 agent「懒人规则集」105.6k stars/2 个月；真正价值=一套规则分发 20+ 宿主的三级架构：核心单一源 skills/ + AGENTS.md compact 版锚点 + plugin/skill/instruction 三 tier 降级 + 指令构建器按模式过滤动态注入 + 每宿主一测试防漂移 + platform-native 知识配套；Hermes plugin 218 行 Python 全拆解=pre_llm_call 注入/pre_gateway_dispatch 命令重写/register_skill 命名空间；qintopia-agent-os 借鉴清单 8 条；泼冷水=benchmark 自报/提示词非约束/适配器矩阵是持续税） | `notes/ponytail-rule-distribution-20260819.md` |
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
| **Jito Arb Pipeline 雏形**（D13 剩余：发现→判定→执行三段串——DexScreener 深池→模拟器 Pool 模型跨池搬判定→正利润路径自动接 Jupiter quote→swap→bundle；⚠️ CLMM reserve 字段不可靠改 priceUsd 锚定+流动性反推；DexScreener priceUsd 显示噪音默认价格锚定只评估滑点/费率、--prices 注入真实价差；实测默认 0 信号=常驻价差磨平） | `scripts/jito_arb_pipeline.py` |
| **HL funding 监控脚本**（D9 广度落地：metaAndAssetCtxs 232 资产 1h funding 快照 + fundingHistory 主流 10 币历史，1h 结算×24×365 换算年化；--snapshot/--history/--top；D15+ 挂 cron 观察窗） | `scripts/hl_funding_monitor.py` · `data/hl_funding_snapshot.csv` |
| **LP 回测牛市段验证**（D11 笔记补牛段：OKX 2024-06→2025-06 BTC +54.9% 8760 根；上涨月动态输 3.0pct/下跌月赢 1.4pct=互证 D11；全程动态 +49.6% > 死守 +37.3%（fee 5.1x 复利）；持有 +54.9% 最强；结论升级「下跌赢/上涨输/全程累计仍赢」；脚本加 --csv/--days；⚠️ OKX history-candles 分页坑 cursor 取页内最旧一条） | `notes/lp-dynamic-range-backtest-20260815.md` · `data/grid_btc_1h_bull_cache.csv` |
| **D14 三选一决策材料**（第一条全流程线候选对照：币股闭市漂移★（2494 样本/dev_bps 中位 63bps/97.4%≥30bps，阶段1🔄7/30天）vs 费率事件窗口（等事件）vs PM 事件（容量小）；决策建议+待补数据清单） | `notes/d14-decision-material-20260816.md` |
| **1inch「无风险套利」教程核验**（W3 推文 8.9万views：ETH 1000 USDC→1003.42 USDT +0.34% 截图；核验=常态价差仅0.045% CoinGecko 实测、0.34%是脱锚事件窗口非常态、常态扣gas净亏、最小有效规模$3.3k、「无风险」=接飞刀尾部风险；结论：真实玩法但claim有水分，fusion resolver已磨平价差，不值得开发） | `notes/oneinch-usdc-usdt-claim-20260816.md` |

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

## 工具（2026-08-22 新增）

- `scripts/funding_basis_viz.py` — 历史费率×基差可视化（OKX 公开 API）：`python scripts/funding_basis_viz.py --symbols BTC,ETH,SOL --days 30`，输出图+文字摘要（当前值/区间/分位）；cron `a8e4a979cdb0` 每周一 9:00 自动推三巨头面板
- `scripts/abnormal_order_radar.py` — CEX 异常挂单雷达（错误单扫描第 1 档）：`python scripts/abnormal_order_radar.py --threshold-pct 2.0 --min-usd 5000`；实测结论=CEX 主流币深盘无错误单（做市商维护干净），主战场在链上订单簿/暴涨窗口，脚本保留复用
- `scripts/bstock_convergence_watchdog.py` — bStock 开盘收敛异常监控（cron ba79519e36cb，周一至五 21:00-22:55 每 15 分钟，≥150bps 才推）
- `scripts/anomalous_order_radar.py` — CEX 异常挂单雷达（错误单套利线第 1 档）：扫 Bybit 永续 + Binance 现货 40 币深盘 500 档，三级分类——L1 穿价单（ask≤best_bid，瞬间可吃）/ L2 近中价偏离（卖低于中价/买高于中价，≥$3K）/ L3 远墙（偏离≥2% 且名义≥$5K，常驻鲸鱼墙只落盘不推送）；`--quiet` watchdog 挂 cron（每 15 分钟，有 L1/L2 才推）；落盘 `data/anomalous_order_scan.jsonl`（L2 频率）+ `data/anomalous_walls.jsonl`（L3 聚合 top10，自动轮转）；实测（08-22）平静市况 L1/L2≈0、L3 常驻（SOL ±2-5% 有数百万美元墙）——雷达价值在波动窗口

官网打卡入口：

https://intensivecolearn.ing/programs/b43d2e97-ed88-4ca3-b12f-7ef672b01205
