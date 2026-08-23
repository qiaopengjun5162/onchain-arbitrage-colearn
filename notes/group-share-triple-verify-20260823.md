# 群分享三连核验：币安 ETF 套利 / a-stock-data / Pendle Boros（2026-08-23）

> 归档日期：2026-08-23 ｜ 归档人：Hermes ｜ 来源：共学群 3 条 X 分享
> 处理顺序：先核验真伪 → 再提取可执行项（铁律：核验是手段不是目的）

## ① JXiaoLoong 币安 ETF 合约套利（重量级）

- 全文 78 段已抓取归档：`notes/binance-etf-contract-arb-20260823.md`
- **一句话**：杠杆型 ETF 与其标的的「每日涨幅差」可套（做多 ETF + K 倍做空标的），**周末无 AP 抹平 + 无重置 → 最多 3 天等待收敛，是结构性黄金窗口**
- 与我们互证：周末窗口 = bStock 闭市漂移同构（D14 实证）；涨幅差重置 = TQQQ 每日重置同构（D14 验证）
- ⚠️ 实盘 1000+u 为作者自述（OpenWhale 自家产品），未独立验证

## ② XAMTO_AI a-stock-data（A 股数据工具，推广帖）

- 帖：https://x.com/XAMTO_AI/status/2091155427576737962（285 likes / 20k views）
- 项目：https://github.com/simonlin1212/a-stock-data
- **核验结果**：✅ 真实。git clone 成功，Apache 2.0 LICENSE + SKILL.md 齐全，README 说明 11 层架构 / 54 端点 / 19 数据源 / 零鉴权（帖子说 13 源/28 端点 = **过时数字**，实际 V3.7.1 更多）
- 本质：A 股数据聚合 Skill（K 线/研报/龙虎榜/北向/资金流/公告），给 Claude Code/Codex 当数据底座
- **与我们的关系**：低。A 股 ≠ 我们主线（crypto 套利/币股 RWA）；但「多源数据统一接口」思路与我们 `funding_spread_scanner` 多所聚合同构。**不装**（不在我们赛道），参考其架构思想
- 后续若做 A 股方向（暂无计划）可回看

## ③ pendle_grandma Pendle Boros（策略推广帖）

- 帖：https://x.com/pendle_grandma/status/2091411808267460690（Yoko | Pendle 官方成员，16 likes）
- 配图 OCR（macOS Vision）✅：Boros by Pendle 资金费率套利界面——ETHUSDT Long 33 天，支付 APR 1.61% / 收取 3.5%（净 +1.89%/年化级），Settled PNL +65.98% 展示
- **核验**：boros.pendle.finance 真实（Pendle 官方子产品），帖为官方成员推广（DYOR/NFA 免责）
- 本质：Pendle 的 **cash carry / 资金费率套利懒人包**——自动开永续+现货对冲吃资费，和我们的费率线同赛道
- **与我们的关系**：中等。同赛道竞品工具（我们手工框架 vs 它一键包）；不装（我们要自己掌握执行细节，且 PNL 展示是营销数字），**但其「资金费率+cash carry 组合」验证了我们对费率线 P0 的判断**
- 注意：Boros 是**托管式/一键式**策略包，与我们「机器执行+人定阈值」哲学互补不冲突

## 三连核验后的共同信号

**三条帖子独立指向同一结论：股票/费率类套利的「事件窗口 + 机制错位」是当前公开讨论的主流——币安 ETF 合约（周末窗口）、Pendle Boros（cash carry）、HIP-3 pre-IPO（上市事件）都在我们 D19 对比表的 P0 两条线（费率 + 币股 RWA）内。方向判断被外部市场印证。**

## 下一步

- [ ] 币安 ETF 涨幅差监控（周末窗口子策略，见 binance-etf-contract-arb 笔记）
- [ ] Pendle Boros 观察：不装，但留意其 APR 数据源（boros.pendle.finance）作为费率市场温度计
- [ ] a-stock-data 不采用，记录备查
