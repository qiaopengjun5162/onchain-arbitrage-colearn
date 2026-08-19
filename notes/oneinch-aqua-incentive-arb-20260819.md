# 1inch Aqua 激励套利拆解：撸毛的终局其实是套利

> 来源：X Article @NeoWeb3Nova（Neo Yun，专注链上 AI，amshe.fun），2026-08-19
> 原文：https://x.com/NeoWeb3Nova/status/2089920914661982670 → `sources/oneinch-aqua-incentive-arb-article-20260819.txt`
> 归档日期：2026-08-19（Hermes 记录）

## 一句话结论

1inch Aqua Maker / LP Incentive Program 不是撸空投也不是价差套利，而是**激励套利（Incentive Arbitrage）**：协议为冷启动花真金白银补贴「真实成交量」，玩家优化头寸去捕获补贴——套利的不是币价，是协议的补贴。

## 核心机制拆解

| 层 | 机制 | 关键点 |
|---|---|---|
| 资产层 | Aqua 允许资产留在钱包，靠 allowance 让同一批资产同时支撑多个做市 Position | 只有真实 Swap 命中报价才移动资产 |
| 收益层 | LP 赚成交产生的 Swap Fee + 活动补贴 | 补贴：基础奖励池 1000 万枚 1INCH + 最多 50 万 USDC DAO 激励 |
| 分配层 | **奖励按 Maker Position 实际承接的 processed volume 分配**，不是 parked TVL | 成交越多 → processed volume 越大 → 激励越多 |
| 防刷层 | wallet cap + taker-maker exclusion + wash-trading filter | 若某市场奖励率高到自交易可获利 → 该市场可被暂停 |

## 关键数字与事实

- @w3_888：7 月底开始研究，目标「撸 10 万 U」；8/11 自述**两周收益超 3 万 U**；8/15 发「无风险套利教程」
- 官方自己写明了套利临界点：【协议奖励 > 制造成交量的成本】——1inch 知道存在机制套利者
- 两类 LP 对比（作者推演）：普通撸毛党 $10,000 开仓拿 $500 Reward，但 Inventory Loss -$800 → 净亏 $300；激励套利玩家按「奖励池大小/竞争/成交量/inventory risk」动态调仓
- 8/2 该玩家自己发帖：Aqua 活动有**资产价格核对问题**，错误创建 LP Pair 会亏钱，称「血泪教训」
- 提醒他人：领奖励前必须处理 LP allowance，否则资产可能被自动兑换

## 与库内对照

- **OKX 闪赚（`notes/okx-flash-earn-hedge-arb-20260817.md`）**：同类——活动补贴期事件驱动家族。闪赚=本币活动期高年化，Aqua=按成交量补贴。共同点：补贴期有限、需要主动优化头寸、宣传年化≠实际年化
- **新订单簿补贴期候选（Lighter×Robinhood）**：Lighter 1100 万 LIT 激励 + 积分 2x 也是同类补贴捕获；「新订单簿补贴期」可以升级为通用的「**活动补贴期扫描器**」：找补贴定价高于风险的协议冷启动窗口
- 群里已有人参与（日书 0817 [39] mdzzdsbhz「参与1inch aqua套利」）——本案例在共学群内不是孤例

## 泼冷水（诚实评估）

- 分享者 56 followers，自己也还在研究中（原文是「研究套利」的探索帖，非实盘复盘）
- @w3_888 教程**未公开完整策略**；「两周 3 万 U」是自述，无仓位/成本/回撤明细，按 gross vs net 五问标注**样本不足**
- 作者本人纠正了「无风险套利」说法：Aqua 官方明示风险（价格变化/IL/Inventory Risk/合约风险），价格变化甚至可能让 LP 最终全部持有交易对中的某一种资产
- 奖励按 processed volume 分配 → 头寸优化是核心竞争力，但这也意味着**竞争激烈后补贴会被迅速磨平**（充分竞争=研究覆盖度）

## 对我们研究线的增量

1. **「激励套利活动雷达」候选**：OKX 闪赚 / Lighter 积分 / 1inch Aqua / Polymarket 补贴 —— 同类监控项可合并为一张「活动补贴期清单」（补贴池规模 + 分配规则 + 风险条款 + 结束时间）
2. **processed volume vs TVL 的分配机制**是判断活动值不值得进的核心字段：按成交量分配 → 需要做市能力；按锁仓分配 → 吃 TVL 就行
3. 防刷条款（wash-trading filter、自交易可暂停市场）→ 扫描器评估活动时要读「防刷条款」，判断我们是否还能参与

## 待办

- [ ] 确认 1inch Aqua 当前支持哪些链/哪些 Pair 奖励池还在（活动生命周期验证）
- [ ] 若做「活动补贴期雷达」，先定数据源（各协议公告/官方文档）+ 字段模板
