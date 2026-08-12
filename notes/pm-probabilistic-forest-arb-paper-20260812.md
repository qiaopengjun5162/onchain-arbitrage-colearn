# PM 论文 digest：Unravelling the Probabilistic Forest（2026-08-12）

> 来源：Paxon 群分享 arXiv:2508.03474（AFT 2025，Flashbots FRP-51 资助），PDF 归档 `sources/papers/pm-probabilistic-forest-arb-2508.03474.pdf`
> 作者：Saguillo / Ghafouri / Kiffer / Suarez-Tangil（IMDEA Networks + Oxford Internet Institute）
> 数据：Polymarket 2024-04-01 至 2025-04-01 一年、86.6M 笔 bids、17.2K conditions（NegRisk 8.56K + Single 8.66K）
> 状态：已精读核心章节（3 定义 / 6 检测 / 7 套利者 / 8 结论）

## 一句话

第一篇对 Polymarket 套利的大规模实证测量：**一年全市场被实际吃掉的套利利润 ≈ $3,960 万**，但只有约 1% 的大选相关机会被执行——钱集中在少数事件期 + 少数账户，论文是「事后地图」不是「操作手册」。

## 两类套利定义（与 127 号笔记直接呼应）

1. **Market Rebalancing Arbitrage（市场内）**：同一 market/condition 的 YES 价格之和 ≠ $1
   - 单条件：YES+NO ≠ 1；NegRisk 多条件：ΣYES ≠ 1
   - Long（Σ<1 买入全套 YES）或 Short（Σ>1 买入全套 NO / Split 后卖 YES）
2. **Combinatorial Arbitrage（跨市场）**：两个依赖市场（如「谁赢州」+「赢多少」）的条件子集间存在逻辑蕴含 → 构造必赢组合；利润 = 两个依赖子集市值之差

## 检测方法（可复用）

- 找依赖市场对：时间相近 + 主题嵌入（Linq-Embed-Mistral）+ **LLM（DeepSeek-R1-Distill-Qwen-32B）判逻辑依赖** → 全年只筛出 13 对美国大选依赖市场对（O(2ⁿ⁺ᵐ) 暴力不可行，靠启发式剪枝）
- 机会检测：区块级成交 VWAP 均价（无成交 carry-forward 5K 块 ≈ 2.5h）；只统计所有 outcome ≤ $0.95 的未定窗口；**profit ≥ $0.05/美元才计入**
- 非原子套利（论文明确）：盘口挂单非原子，只有部分腿可能成交 → 尝试套利本身有执行风险

## 核心数字

| 项目 | 数字 |
|---|---|
| 有机会的条件数 | 7,051 / 17.2K（2,628 NegRisk + 4,423 Single） |
| 单条件已实现利润（买 <$1） | $5,899,287 |
| 单条件已实现利润（卖 >$1） | $4,682,075 |
| NegRisk 市场内：买 YES | $11,092,286 |
| NegRisk 市场内：**买 NO** | **$17,307,114（最大头！）** |
| NegRisk 市场内：卖 YES / 卖 NO | $612K / $4.3K |
| 跨市场（13 对依赖，仅 5 对被吃） | 合计 ~$95K（pair2 $60K / pair4 $18.5K / pair1 $15.8K / pair3 $629） |
| **全部策略合计（已实现）** | **$39,587,585 ≈ $4,000 万**（ε=$1/笔假设） |
| Top1 账户 | $2,009,631（4,049 笔） |
| 极端案例 @Tutaaa91 | 双买 YES+NO 各 <$0.02 → 单笔 $58,983 |

## 关键结论（与我们研究线的交叉）

1. **「买 NO」是被验证的最大策略**（$17.3M，Polymarket 官方推文也确认过）——不是买 YES 抄底，是系统性买低估的 NO
2. **Sports 单条件市场是「机会多、被吃少」的空白区**：机会数量上 Sports 主导，但利润图里 Sports 几乎缺席（「a less explored venue for arbitrageurs」）——与我们「研究覆盖度=竞争拥挤度」判断同构
3. **约 99% 的机会没被执行**：论文检测到的机会大多在低流动性时刻、$100 量级、非原子 → 扫得到 ≠ 吃得到
4. **零手续费假设**：论文期间 Polymarket 不收交易费，$40M 是零费上限；现在已有 taker 费（我们 polymarket-leaderboard-gross-pnl 实测 0.012-0.014/股）→ 现实净空间更小
5. **与 127（Helios）互证**：论文用成交 VWAP 检测 Σ<1；127 证明 CLOB 盘口是硬镜像（YES_ask+NO_ask ≥ 1+spread）——**盘口层面可执行的 Σ<1 组合基本不存在，VWAP 方法会跨过盘口价差高估可捕获性**。这解释了「试 rebalance 扫不到机会」的结构性原因

## 对我们的增量

1. **PM rebalancing 扫描的正确姿势**：不是对「成交均价」扫描，而是对「bid/ask 盘口可执行组合」扫描（YES_bid_sum < 1 或 NO_bid_sum < n-1 且扣费后为正）——可直接用 polymarket skill 的 orderbook API 做
2. 事件期是唯一主战场：2024 大选（Nov）+ Biden 退选后的 VP pick（Aug）贡献了最大利润；日常扫描 ≈ 0
3. Sports 低估机会是相对空白区（可做 exploratory，注意 099 的「机会统计」框架：频率/幅度/半衰期/容量）
4. 「买 NO」>「买 YES」的偏好值得单独研究（可能与 NO 盘深度差、散户追 YES 有关）

## 待办

- [ ] （可选）写一个 PM rebalancing 盘口扫描器原型：遍历活跃市场，计算 YES_bid_sum / NO_bid_sum，扣 taker 费后 >0 才告警（接 polymarket skill）
- [ ] 论文 Table 1 Top10 地址与 leaderboard 榜一地址交叉（我们的 activity API 已能拉）
