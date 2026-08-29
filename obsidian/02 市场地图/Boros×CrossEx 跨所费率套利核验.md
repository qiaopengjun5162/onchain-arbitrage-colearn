---
title: Boros×CrossEx 跨所费率套利核验
date: 2026-08-08
type: note
tags:
  - onchain-arbitrage
  - market-map
---

# Pendle Boros × CrossEx 跨所费率套利核验（2026-08-28）

> 触发：https://x.com/pendle_grandma/status/2093279824198463709（Pendle 官方账号推：Boros×CrossEx 20-40% APR 固定收益 + PENDLE 红包活动）
> 方法：浏览器渲染 boros.pendle.finance/crossex/ 全机制拆解 + 与库内 08-20 CrossEx 框架互证
> 结论：**机制真实、数字拆解透明（27% APR），但 13.9x 杠杆违背我们「抗 2 倍涨幅=几乎全保证金」铁律；PENDLE 红包=引流；CrossEx 辖区问题待重新确认**

## 一、机制拆解（boros.pendle.finance/crossex/ 实测）

**Boros = Pendle 的费率掉期市场**：把某交易所的浮动资金费率换成固定利率（Short YU 收固定 / Long YU 付固定），到期结算（示例：2026-09-25 到期）。

**当前 LIVE 示例（BTC · 27 天 · +27.0% APR）四腿结构**（$10 万/腿名义，~$7.2k 资金）：
1. **Short BTC perp @ Hyperliquid**（CrossEx）— 收浮动费率（HL 费率贵）
2. **Long BTC YU @ Boros** — 付浮动费率，**收 8.1% 固定**
3. **Long BTC perp @ Gate**（CrossEx）— 付浮动费率（Gate 费率便宜）
4. **Short BTC YU @ Boros** — 收浮动费率，**付 4.8% 固定**

**数学**：浮动腿互相抵消 → 净 8.1% − 4.8% = 3.2% spread → 1.9% 扣费后 → **×13.9 杠杆 = 27.0% on capital**

**执行**：开源终端本地跑（pendle-finance/arbitrage-with-crossex），只连自己的 Gate 账户（API key 本地，scoped to trade）；四腿预填一键执行；到期自动结算，可滚入下一窗口。

## 二、谁付钱

- **HL 侧浮动费率**：付费方 = Hyperliquid 上拥挤的杠杆方（BTC 在 HL 费率贵=多头/空头拥挤）
- **Gate 侧**：费率便宜方（对冲腿，成本端）
- **Boros YU 对手方**：愿意付固定利率的人（市场另一端）——Boros 是 Pendle 生态的费率掉期市场，流动性来自社区
- **PENDLE 红包（50 PENDLE × 51 名额，13 天）**：引流激励——鼓励社区实盘使用工具（宣传属性，收益数字要打折看）

## 三、与库内框架互证（08-20 CrossEx 笔记）

- 同构：跨所费率差套利、Delta neutral、卖保险逻辑 ✅
- **冲突点 1：13.9x 杠杆 vs 「抗 2 倍涨幅 = 0.97x 杠杆」铁律**——页面自己的风险节都承认「A hedged trade can still be liquidated」。13.9x 是收益放大器也是爆仓加速器；对冲 ≠ 免死（TUT 剧本教训：最后一分钟插针爆单腿）
- **冲突点 2：CrossEx 辖区**——库内结论「Gate 受限辖区含中国/香港，CrossEx 不可用，改走同所统一账户」；Pendle 现在大推说明平台活着，**需重新确认用户辖区是否可用**
- 补充点：Boros YU 是**固定到期**（27d 窗口），不是随时可平——到期前退出有流动性/定价风险

## 四、红旗与判定

1. **杠杆是主要风险**：即使机制透明，13.9x 不符合我们的风控框架（蚂蚁仓/抗 2 倍）。若要用：降杠杆到自己的安全参数（0.97x 级），那 27% 就变成 ~1.9% 收益——**数字的幻觉来自杠杆**
2. **PENDLE 红包** = 工具推广期激励（51 个名额快满，14% 已派）——「热情群友反馈」是营销叙事的一部分
3. 收益宣传（20-40% APR）是**当前窗口**的 live 数字，随费率差变化——不可作为常态预期
4. **不装不跑原则**：开源仓库可审（install.sh 一键装，先读代码再决定）；辖区可用性未确认前不实操

## 五、可执行项

1. 重新确认 CrossEx/Gate 辖区可用性（用户主站注册测试）——若可用，Boros 工具进入实操评估候选（按安全参数重算）
2. 记录 Boros YU 费率掉期市场 = 新工具层（把浮动费率变固定——事件窗口的新维度：到期窗口/固定利率差本身可交易）
3. Boywus Gamma 做市科普（同日帖）——认知类，与 glassnode「做市商 Gamma 8.23 万转负」概念互证，归入做市/方向 7 学习材料
