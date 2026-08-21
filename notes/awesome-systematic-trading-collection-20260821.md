# awesome-systematic-trading 合集核验（群分享 2026-08-21）

> 来源：X 帖 https://x.com/bkdgiffug/status/2090666455511802141（lumxss 推广）
> Repo：https://github.com/paperswithbacktest/awesome-systematic-trading
> 归档日期：2026-08-21 ｜ 归档人：Hermes
> 关联：`notes/smart-money-tools-eval-20260820.md`（工具评估方法论）、`notes/backtest-playbook.md`

## 核验结论（先说结果）

**帖子内容属实**：97 库/40+ 策略/55 书/23 视频 全部对得上。Repo 13.5k stars / 1.6k forks / 129 commits，维护活跃。这是量化交易领域最全的 awesome 清单之一（vs 同类 wangzhe3224 版 4.9k stars）。

## 对我们共学有用的（按研究线筛）

### 🟢 直接相关（套利/做市/执行）

| 工具 | 类型 | 为什么有用 |
|---|---|---|
| **Hummingbot** (CoinAlpha) | 做市/套利客户端 | 官方文档有 Solana connector（gateway connect solana，支持 Token-2022）——我们 Solana 线做市的现成参考 |
| **bTrader** | 三角套利 bot (Binance) | 三角套利参考实现，与我们的跨池/三角研究线对应 |
| **HFTBacktest** (nkaz001) | HFT 精确回测 (Python+Numba) | 我们执行层研究缺的「高精度回测」工具，薄池/微价差场景适用 |
| **Blackbird / bitcoin-arbitrage / R2** | 跨所价差套利 | 经典跨所套利参考（历史项目，看思路不看代码） |
| **OctoBot** | TA+arbitrage bot | 套利模块参考 |

### 🟡 方法论参考（回测框架）

- **vectorbt**（向量化回测，pandas+Numba 万级策略秒测）——我们网格/价差回测可换用
- **backtesting.py / backtrader / nautilus_trader**——事件驱动框架，币股漂移/费率窗口线可用
- **Freqtrade / Jesse**——crypto 回测框架（Freqtrade 支持 Telegram 控制，与我们 cron 生态契合）
- **vnpy / QUANTAXIS / WonderTrader**——国产全栈框架，学习架构用

### 🔴 与我们重叠度低（不投入）

- 传统资产（Bonds/Equities/REITs）策略占大头——我们专注 crypto 链上
- ML 类（RL in Finance 课程等）——研究线暂不需要
- 55 本书里大部分是传统量化入门（可与陈皓文章「信息密度」标准对照挑书）

## 策略清单里的套利条目

- Trading WTI/BRENT Spread（商品价差，`-0.199` 夏普/11.6% 年化）——价差交易思路参考
- Soccer Clubs' Stocks Arbitrage（`0.515` 夏普/14.2%）——非相关市场套利案例

## 结论

- 这是一个**传统量化+部分 crypto 的导航页**，对共学价值 = 工具地图 + 回测框架选型参考，**不是套利策略金矿**（链上 MEV/盲套利不在其覆盖范围，那部分我们已自建）
- 最大可落地项：**Hummingbot Solana connector**（做市线）+ **HFTBacktest**（执行层回测）——建议按需各挖一篇
- 与 08-20 工具评估同方法论：先看能力缺口（我们要做市/高精度回测），再对号入座，不收藏不落灰

## 下一步

- [ ] Hummingbot Solana connector 实测（连 devnet 或 read-only 验证）
- [ ] HFTBacktest 在我们 TUT/价差数据上跑一遍对比现有 backtest-playbook
