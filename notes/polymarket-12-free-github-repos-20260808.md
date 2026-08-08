# Polymarket 12 个免费 GitHub 仓库清单（Crypto老鹰分享）

> 来源：https://x.com/laoyingkhq/status/2085989895978590449（Paxon 分享 2026-08-08）
> ⚠️ **推广性质**：链接带邀请码（polymarket.com/zh/?via=YINGGE888、PolyCop_BOT?start=ref_YINGGE888）= 拉人头返佣模式；但仓库清单本身是真实可用的公开资源，按「内容可用、邀请链接忽略」处理
> 关联：`notes/polymarket-twap-settlement-20260808.md`（TWAP 结算变更）、`notes/polymarket-negrisk-no-recycle-arbitrage.md`、`notes/polymarket-arbitrage-math-framework.md`

## 数据分析（4 个）

| 仓库 | 用途 | 亮点 |
|---|---|---|
| **SII-WANGZJ/Polymarket_data** | 最大公开数据集之一 | **107G 真实交易数据 / 11 亿+笔**，上海大学 5 位教授维护 |
| evan-kolberg/prediction-market-backtesting | 回测模拟器 | 交易想法放到历史市场跑，看盈亏/胜率/回撤 |
| ent0n29/polybot | 交易员行为分析 Bot | 输入地址分析真实交易行为，找重复模式和策略 |
| warproxxx/poly_data | 历史数据抓取 | 拉几乎所有历史市场数据 + 统计图表 |

## 交易 Bot（5 个）

| 仓库 | 用途 |
|---|---|
| alsk1992/CloddsBot | **118 套策略**：Binance-Polymarket 延迟套利、智能路由、Penny Clipper、DCA、均值回归 |
| lihanyu81/polymarket_lp_tool | 限价单管理，最大化流动性奖励（呼应 TWAP 新规的 rewardsMinSize/rewardsMaxSpread） |
| HarrierOnChain/Prediction-Markets-Trading-Bot-Toolkits | **Polymarket-Kalshi 套利**、体育交易、复制交易、spread farming、做市 |
| yangyuan-zhen/PolyWeather | 天气交易 Bot（天气预报/机场数据/航空气象观测 → 温度报告） |
| MrFadiAi/Polymarket-bot | Smart Money 策略：找顶级交易员按胜率筛选 → 跟单列表 |

## 额外工具（3 个）

| 仓库 | 用途 |
|---|---|
| pydantic/pydantic-ai | AI Agent 构建工具（数据分析/策略研究/自动化工作流） |
| mvanhorn/last30days-skill | 过去 30 天网页趋势分析（交易前信息面研究） |
| aarora4/Awesome-Prediction-Market-Tools | 100 个预测市场工具合集（看板/AI Agent/Bot/学习资源） |

## 对我们研究的价值（按优先级）

1. **SII-WANGZJ/Polymarket_data（107G 数据集）**：如果要做 Polymarket 套利研究（NegRisk/机制套利），这是最全的数据源——比 Dune 便宜（免费 + 原始数据）
2. **evan-kolberg 回测模拟器**：可复用「预测市场回测」思路到我们自己的策略验证流程
3. **HarrierOnChain（Kalshi 套利）**：跨平台预测市场套利 = 我们跨所价差的 Polymarket 版本
4. **polymarket_lp_tool**：TWAP 结算变更后（$1M 流动性奖励硬门槛），做市/限价单管理是唯一能吃到奖励的方式——直接命中我们刚归档的 TWAP 笔记

## 筛选原则（对齐知识库「缺啥补啥」）

- 不盲目收集全部 12 个——按需取用：**套利/数据/回测**三个方向优先
- 推广性质内容：邀请码链接一律忽略；仓库本身开源可核验（GitHub 公开）
- 待做：若要深挖 Polymarket 套利，先拉 107G 数据集子集（不用全量，按市场/时间片取）

## 待做

- [ ] （低优先级）拉 Polymarket_data 的数据结构说明，评估子集可用性
- [ ] （可选）回测模拟器思路借鉴到共学策略验证流程
