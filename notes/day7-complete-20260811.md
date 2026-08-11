# Day 7 全景笔记：从「看起来赚了」到「真的赚了」的认知闭环（2026-08-11）

> 本笔记整合 Day 7 全部产出（官方线/个人线/研究线/广度），按认知脉络而非时间线组织。详细版，供复盘与 L0008 复用。
> 关联：`daily/2026-08-11.md`（打卡版）· 各专题笔记（文末清单）

## 〇、今日一句话

**「看起来赚了 ≠ 真的赚了」——成本与毛利同量级时，所有毛口径数字都是幻觉。** 今天用四个独立案例（网格 1300U / Polymarket 榜一 / gas 反杀 / OPENAI 假价差）把这个方法论钉死了，并沉淀成可复用的 5 问筛选框架。

## 一、认知主线：四个案例 → 一个方法论

### 案例 1：网格 1300U（状态选择偏差）
- 来源：@zaijin338191「在金」4 所 6 账户网格系统 1200U→1300U
- 验证：OKX BTC/USDT 1h 真实行情 10080 根（2025-06→2026-08），13 个月独立回测
- 数字：**下跌月亏损率 88%（8 月亏 7）vs 非下跌月盈利 100%（5/5）**；月净收益 vs |月涨跌| 相关 **-0.48**；0 手续费全期仍净亏 **-$1,122**（趋势月库存浮亏 -$2,330 > 震荡月 edge +$1,208）；10x 杠杆下 2026-01（月跌仅 -10.2%）即爆仓
- 结论：结构性不对称（趋势月浮亏 > 震荡月 edge），非参数问题；「一个月测试」撞上 2026-07/08 低波动月不构成证据；等 Arcus 开源自按实参复跑
- 副产品（L0007 成本拆解落地）：8bps 手续费吃掉 0.1% 格距——费用 vs 格距生死线

### 案例 2：Polymarket 榜一（税前口径 + 返佣依赖）
- 来源：@runes_leo 推文 → 公开 API 实测重建（data-api /activity 事件流）
- 数字：手续费公式逐档验证正确（100 股×0.07×p×(1-p)：p=0.5→$1.75 / 0.99→$0.07）；**每股手续费实测 0.0122-0.0142**（推文说 0.011-0.014 ✓）；Djdjdjekekek 11 天返佣 $74.6K（taker $57.5K+maker $17.1K）；**HomeRunHazard 月榜 +$454K 但近 11 天纯交易 -$121K**——榜单与真实方向相反的实锤
- 结论：榜单 pnl 是税前 gross；返佣按费用比例返=返佣多是坏信号；「真实到手 24-45%」只对 edge≈费用的吃单 bot 成立，有真 edge 的地址到手 82-92%（修正推文）
- 方法论：activity 事件流三分账（TRADE/REDEEM/REBATE）可审计任何地址

### 案例 3：gas 反杀（固定成本不缩放）
- 来源：Paxon 实测 0.004 ETH 跨链（毛利 +0.01U / 成本 -0.11U = 11 倍）
- 数字：毛利价差率 +0.133% vs 成本率 -1.46%；**最小有效规模 = 固定成本 ÷ 价差率 = $83 打平、$1000 进 LI.FI 最优点**
- 结论：毛利为正 ≠ 套利成功；规模是套利参数不是可选项；门槛公式判定 NO-GO 与实测一致

### 案例 4：OPENAI Pre-IPO 假价差（不可转换 = 无闭环）
- 来源：Paxon 提供的现货 OPENAI/USDT vs OPENAIUSDT Pre-IPO 永续对比
- 判据：**套利闭环成立前提 = 可转换/可交割/可赎回**；两者全无 → 价差巨大但无无风险套利空间
- 与 Binance Alpha「聚合器 vs 单池」同构——**假价差判据：先问「买到的能不能拿去卖」**（资金闭环检查）

### 沉淀：评估任何赚钱案例的 5 问（L0008 筛选前置）
1. 税前还是税后？（口径）
2. 成本占毛利多少？（>50% 数字即幻觉）
3. 返佣/补贴依赖度？（返佣多=费用多=坏信号）
4. 样本窗口是什么市场状态？（必须覆盖趋势月/极端行情）
5. 仓位达到最小有效规模吗？（固定成本÷价差率）

## 二、工程产出（7 项，全部实测跑通）

| 产出 | 位置 | 状态 |
|---|---|---|
| 网格趋势回测 v2（数据缓存+手续费扫描+宽窄区间） | `scripts/grid_trend_backtest.py` | ✅ 13 月跑通 |
| AMM 数学验证（x*y=k 精确复现 Raydium 73.9612，费率反推 0.30%） | `scripts/amm_v2_verify.py` | ✅ |
| Polymarket 排行榜验证（activity 事件流三分账） | `scripts/polymarket_leaderboard_fee_verify.py` | ✅ |
| 无套利带雷达 v2（锚点校准+深度 suspect 过滤） | `scripts/no_arb_corridor_radar.py` | ✅ cron 30min |
| TUT Rust 时间对齐 v2（inner join on ts） | `scripts/tut_backtest/rust/src/main.rs` | ✅ 双日验证 |
| 多链价差监控 v0（slot0 直读+净价差判定） | `scripts/multi_chain_spread_monitor.py` | ✅ |
| tvscreener 验证（币股双腿数据源） | venv 安装 | ✅ |

关键工程发现：
- **Raydium SOL-USDC 池费率是 0.30% 不是 0.25%**（x*y=k 精确复现反推，与 08-07 笔记一致）
- **TUT 数据 Binance/Bitget 起始时间不同**（09:00 vs 00:00）——按 index 对齐会算虚假价差，inner join 是唯一正确方式
- **Jupiter 池列表 API 不可用** → 深度过滤用「价格偏离锚点 ≥3%」代理
- **tvscreener CryptoScreener 含 BITGET:RSPYUSDT 等 tokenized 股对**——币股时钟差双腿数据源一个库打通

## 三、研究线更新

- **#13 低容量结构性价差量化**（新增）：薄池价差持续性 + 容量上限 + 小所价差；接 backrun 薄池扫描
- **#14 Meme 微观结构**（新增）：5M 壳价 cohort（nine_DeFi 假设）+ Dev 行为哨兵（四本账）+ 增发监控；博弈研究非实盘建议
- 候选方向标注：币股 ★★★ / 低容量 ★★★ / 链上 perp ★★

## 四、广度归档（今日 +14 条）

金哥网格 / Polymarket Leo / tvscreener / 另一面 A股复盘 / 李胜利 Hyperliquid / nine_DeFi 妖币 / 另一面缠论 / hunterweb303 Dev 出货 / brucexu Hermes 报告 / Solana_zh 预测市场教程 / SiyuYeAndy Raft / BlockBloomer BTC 资金费率 / OPENAI Pre-IPO / Paxon 认知分享

高价值提取：
- **BTC 资金费率套利**（BlockBloomer）：同所 delta 中性完整实操（统一账户现货多+永续空 1x）；历史 7578 次结算 85.58% 正、最差月 -0.53%、2026 2-4 月连续负——backlog #2 现成答案；「连续负费率期」= 最大尾部风险
- **Dev 出货状态机**（hunterweb303）：建仓→藏仓 59%→试探 0.4-1%→主卖 40%→子钱包清仓→Locker 分润；四本账 = 信息差套利状态机
- **Raft 多 Agent 通信设计**（SiyuYeAndy）：Freshness Hold + Inbox 信号/正文分离 + 单 Agent 单上下文——qintopia-agent-os 直接参考
- **缠论分类学**（另一面）：「走势不可预测但可完全分类」——中枢 ≈ 无套利带走廊的跨域映射

## 五、DOS 多链搬砖三步落地（专题）

1. **找多链币**：实证发现 BSC+ETH 双链深池的多链币极稀缺（ZRO/ALT/W/PENDLE/ENA 在 BSC 全无主流池）；DOS 是「新币上币窗口」特殊案例
2. **监控多链价格**：`multi_chain_spread_monitor.py`（slot0 直读，BSC 0.5292 vs Gate 0.529 精确一致）
3. **搬砖判定**：毛价差 136bps → 净 7.6bps（BSC→ETH 桥费 $0.69 是杀手）→ **NO-GO**；真正窗口=ETH 折价时走 ETH→BSC 便宜方向（桥费 $0.02）

## 六、认知演变（今天最后一段）

- 「跟单这种简单策略更快」→ 对，但幸存者偏差/执行滞后/容量三层坑；跟可审计地址 + 小金额跑通
- 「几百个池子数据同步慢」→ 架构问题：缩小监控面 + Geyser/gRPC 流式推送替代轮询（不要全节点路线）
- 「Robinhood 没有内存池没有贿赂」→ 半对半错：PFOF 把 MEV 变成做市商内部化价差；但竞争密度低的市场确实适合个人——与 #13 低容量方向一致

## 七、明日衔接（D8）

- 官方线：L0008 机会候选清单 v1（5 问筛选前置，素材已备）
- 个人线：AMM 数学 2（CLMM 可视化）；backrun 薄池扫描（与 #13 合并）
- 补课剩余：雷达 v2 ✅ / TUT 对齐 ✅ 已清；剩 backrun
- 待办挂起：0xd21258ed 地址取证（Blockscout 422 需修参数）；资金费率 85.58% 跨所验证（OKX funding 历史）；微信 iLink 限流排查

## 八、专题笔记索引

- `notes/grid-trend-backtest-20260811.md`（案例 1）
- `notes/polymarket-leaderboard-gross-pnl-20260811.md`（案例 2）
- `notes/gas-bridge-fee-eats-arb-case-20260811.md`（案例 3）
- `notes/gross-vs-net-three-cases-20260811.md`（5 问方法论，L0008 素材）
- `notes/amm-math-v2-preview-20260811.md`（D8 预习）
- `notes/solana-week1-summary-20260811.md`（个人线周总结）
- `notes/meme-dev-harvest-pattern-20260811.md`（Dev 状态机 + 玩家侧）
- `notes/tvscreener-verified-20260811.md`（选项 B）
- `notes/dos-bridge-arb-20260811.md`（多链搬砖）
- `notes/binance-alpha-arbitrage-20260811.md`（假价差 #1）
- `notes/research-backlog.md`（#13/#14）
