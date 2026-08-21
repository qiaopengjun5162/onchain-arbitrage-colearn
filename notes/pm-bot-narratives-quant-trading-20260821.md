# 群分享速记：PM 机器人叙事 ×3 + quant-trading 工具核验（2026-08-21）

## 1. 春日部彼得（crbpite8）——PM 套利机器人「泄露」第二版

> https://x.com/crbpite8/status/2090735630271877269（2026-08-21，带返佣链接）

- **又是 FrondEnt/PolymarketBTC15mAssistant**（今天第二个人推同一个 repo）——**已核验过是 TA 交易助手不是套利机器人**（见 `shiboss-pm-bot-verify-20260821.md`）
- 新加的吹点：「502 次预测胜率 98%、总利润 $54,840、单笔 +$7,914（+170%）靠捕捉币安延迟」
- **定性：同一 repo 的返佣推广变体**（Polymarket 官网链接带 `?via=YINGGE888` + Telegram 跟单 bot `ref_YINGGE888`）
- **核验要点**：胜率 98% + 跟单 bot 返佣 = 典型收割话术；「捕捉币安延迟」与 repo 实际功能（TA 信号）不符；不采信

## 2. 断浪 WaveKing（waveking1314）——21 岁交大学生 Claude Code 撸 PM 套利 bot

> https://x.com/waveking1314/status/2044373138046431613（2026-04-15）

- 叙事：Claude Code 2 天撸出 PM 50+ 盘口价差监控 + OpenClaw 同步币安分析，一夜 +$1,940，启动资金 $1,400
- 对标 planktonXD：年 61,000 笔 / 利润 $106,000（套利）
- 风控：流动性异常自动停机、紧急清仓人工确认、砸盘回撤 3%
- **定性：幸存者叙事样本**（无 tx hash、无链上证据、无回测）——按 Bruce 规律「没有永赚博主」+ 十老板样本同类，看机制不看数字
- **可提取的机制**：Claude Code 生成策略 + 监控 PM 定价失效 + OpenClaw 执行 = AI 补第 4 级（脚本）短板的实操案例；「流动性异常自动停机」与我们机器执行风控同构

## 3. 折耳根 Ace（_zheergen）——quant-trading 工具合集

> https://x.com/_zheergen/status/2082638028057804999（2026-07-30）

- **核验 ✅**：je-suis-tm/quant-trading，**10,601 stars 属实**（Python，今天还在更新）
- 内容：技术指标（MACD/RSI/Bollinger/Parabolic SAR）、形态突破（Heikin-Ashi/Shooting Star/London Breakout/Dual Thrust）、统计套利（Pair Trading 协整）、期权波动率（Straddle/VIX）、Monte Carlo/组合优化
- **定性：工具库，学习信号逻辑可以，策略本身是公开经典 = 无 edge**（与 awesome-systematic-trading 结论同构：工具地图不是策略金矿）
- 与我们关系：Pair Trading 协整实现可作币股配对参考；其余是经典教学

## 结论

- 三条叙事线全部落位：PM 机器人（标题党返佣推广）/ 交大学生（幸存者叙事）/ quant-trading（工具核验✅无 edge）
- 今日第四次验证「公开分享的策略/工具 = 滞后信息 = 无 edge」——与 Bruce 规律互证
- 唯一增量：WaveKing 的「AI 撸 bot 2 天」案例佐证 AI 补脚本短板的路径（我们已走通 Rust 双实现 + Jito pipeline）
