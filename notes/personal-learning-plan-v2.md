# 个人学习计划 v2（21 天版，Hermes 按校准意见生成）

日期：2026-08-05（共学第 1 天）

来源：Hermes 根据 `personal-learning-plan-v1.md` 的校准意见，把 6 周版压缩成 21 天每日任务表。本文档记录结构和产出目标，每日明细由 Hermes 维护。

## 结构

- 每天 = 主线 1.5h（Solana 深入）+ 广度 0.5h（全地图概念）
- 主线节奏：第 1 周 Solana 交易模型 + 环境 + 监控脚本，第 2 周 AMM 数学 + 模拟器 + Jito devnet bundle，第 3 周 pipeline 整合 + 回测 + 方向决策

## 21 天产出总表

1. Solana 交易模型一页笔记（文档）
2. Devnet 环境 + 钱包 + swap tx（环境）
3. DEX + xStocks 双监控脚本，后台跑（代码）
4. 套利利润模拟器，多池子多路径（代码）
5. Jito Bundle pipeline：发现 -> 提交 -> 日志（代码）
6. 历史机会回测报告（数据）
7. 4 方向深度对比表：原子套利 / 币股 D 路线 / 资金费率 / 跨链（决策文档）
8. 主网迁移清单（文档）
9. 21 天学习总结 + 下一步计划（产出）

## 预期管理（Hermes 原文，已对齐群共识）

- Jito bundle 在 devnet 跑通不等于能赚钱。价值是理解 Solana 排序层和交易执行层，是必修课，不是盈利路径。
- 原子套利是群共识里最卷的方向。把 Jito 当基础设施理解，真正可能有 edge 的方向是币股 D 路线、跨链、链上 perp。
- 双监控脚本是最聪明的产物：一个脚本同时监视 DEX 价差和 xStocks 价差，第三周决策时有数据说话，不是猜。

## 第三周决策点

D20 的 4 方向对比表 + D21 的总结报告，对应 Bruce 框架的"第三周选 2-5 个方向深挖"。共学结束后主攻什么，由这三周攒的数据决定，不提前拍脑袋。

## 连接

- `notes/personal-learning-plan-v1.md`：6 周原版 + 校准意见
- `notes/tokenized-stock-arbitrage.md`：币股 D 路线
- `notes/research-backlog.md`：候选方向池

## 每日明细

> 每天 = 主线 1.5h（Solana 深入）+ 广度 0.5h（全地图概念）。打卡产出写入 `daily/`，周末汇总到对应笔记。D = Day。

### 第 1 周：Solana 交易模型 + 环境 + 监控脚本（D1–D7）

| Day | 日期 | 主线（1.5h） | 广度（0.5h） | 打卡产出 |
|---|---|---|---|---|
| D1 | 8.5 | Solana 交易模型：无 mempool、400ms slot、leader schedule、交易生命周期。产出 `notes/solana/` 下一页笔记 | 读群聊记录和零基础学习版，建"全地图"概念清单：原子套利/CEX-DEX/跨链/资金费率/稳定币/清算/MEV | daily/2026-08-05.md（已有）；交易模型一页笔记草稿 |
| D2 | 8.6 | CLI + Anchor 环境检查：solana-cli 版本、devnet 连接、Anchor 安装、devnet SOL 水龙头。记录所有版本号和坑 | 读 `tokenized-stock-arbitrage.md`，理解币股 D 路线和稳定币套利的同构关系 | daily/ 打卡 + `notes/solana/anchor-installation-note.md` 更新 |
| D3 | 8.7 | 第一笔 devnet swap tx：创建 devnet 钱包、从水龙头领 SOL、用 Jupiter API 发一笔 swap、用 Solscan 查 tx 详情 | 读 Binance Web3 Trading API 文档，确认支持的发行方/链/行情实时性 | daily/ 打卡 + tx hash 记录 |
| D4 | 8.8 | 价格监控脚本 v0：用 Helius RPC 或 Jupiter Quote API 拉 DEX 报价，Python 脚本打印价差，本地跑通 | 读群讨论 case（toll-fee-pool / premium-buyin-lp），理解 LP 损益不对称 | daily/ 打卡 + `scripts/monitor_demo.py` 更新（如已有则扩写） |
| D5 | 8.9 | 监控脚本加 xStocks 腿：在脚本里加入币股价格拉取（同一脚本同时监 DEX 价差 + 币股价差） | 读 `funding-fee-arbitrage-1token.md`，理解锚定类套利风险核算框架 | daily/ 打卡 + 双监控脚本输出样例 |
| D6 | 8.10 | 第一周总结：整理 Solana 交易模型笔记、devnet 操作记录、监控脚本结构。对照 v1 校准意见自查完成度 | 读 `research-backlog.md`，标注自己感兴趣的 2-3 个候选方向 | daily/ 打卡 + 周总结笔记 |
| D7 | 8.11 | 缓冲/补课日：补齐本周掉队的任务。若全完成，提前做 D8 的 AMM 数学预习（Uniswap V2 x*y=k + CLMM 区间） | 翻群聊记录，挑 2 篇高价值讨论做来源摘要写入 `sources/links.md` | daily/ 打卡 |

### 第 2 周：AMM 数学 + 模拟器 + Jito devnet bundle（D8–D14）

| Day | 日期 | 主线（1.5h） | 广度（0.5h） | 打卡产出 |
|---|---|---|---|---|
| D8 | 8.12 | AMM 数学 1：Uniswap V2 x*y=k 推导，恒定乘积下 swap 价格冲击公式，Python 手算验证 | 读 `mempool-and-ordering.md`，理解 Solana 排序层博弈（Jito 拍卖 vs 公共 mempool 的差异） | daily/ 打卡 + AMM 推导笔记 |
| D9 | 8.13 | AMM 数学 2：CLMM 集中流动性（Uniswap V3 / Orca Whirlpool），tick/区间/流动性分布的 Python 可视化 | 读群讨论或外部资料，了解 Hyperliquid / Drift / Zeta 链上 perp 的资金费率机制 | daily/ 打卡 |
| D10 | 8.14 | 套利利润模拟器 v0：Python 脚本，输入池子参数 + 价格 + Gas，输出多池子多路径的扣费后利润。纯模拟不链上操作 | 读 `aggregator-routing.md`，理解路由聚合器（Jupiter/1inch）的路径拆分逻辑 | daily/ 打卡 + `scripts/` 下模拟器初版 |
| D11 | 8.15 | Jito 基础：读 Jito 文档，理解 bundle 提交流程（sendBundle/getTipAccounts）、devnet 配置、失败的常见原因 | 读 `lp-dynamic-range.md`，理解 LP 区间调整策略和做市商博弈 | daily/ 打卡 |
| D12 | 8.16 | devnet 第一笔 Jito bundle：构造一个简单 swap bundle（无套利意图，只为验证流程），提交到 devnet，记录 bundle_id 和结果 | 回顾本周 D8-D11 的广度笔记，给每个方向写一句话判断：卷度 / edge 可能性 / 个人匹配度 | daily/ 打卡 + bundle tx 记录 |
| D13 | 8.17 | Jito bundle 加套利逻辑：在模拟器输出里选一个正利润路径，构造真实 bundle 提交 devnet（可以利润为 0，重点跑通发现 -> 提交 -> 日志闭环） | 读币股相关群讨论更新，跟踪发行方对照表的完成度（如果 Hermes/Codex 在建） | daily/ 打卡 |
| D14 | 8.18 | 第二周总结：汇总 AMM 笔记、模拟器、Jito bundle 结果。对照 21 天产出总表自查：监控脚本 ✓ / 模拟器 ✓ / Jito pipeline 半完成 → 调整 D15-D19 节奏 | 用群聊/笔记更新 `sources/links.md` | daily/ 打卡 + 周总结笔记 |

### 第 3 周：Pipeline 整合 + 回测 + 方向决策（D15–D21）

| Day | 日期 | 主线（1.5h） | 广度（0.5h） | 打卡产出 |
|---|---|---|---|---|
| D15 | 8.19 | Pipeline 整合 1：把监控脚本 + 利润模拟器 + Jito 提交串成一条流水线（发现机会 -> 算利润 -> 构造 bundle -> 提交） | 读群友关于跨链套利的讨论，理解 Wormhole/LayerZero 桥延迟和跨链 MEV 的基本逻辑 | daily/ 打卡 |
| D16 | 8.20 | Pipeline 整合 2：加日志和时间戳，让 pipeline 完整运行一次（devnet），记录端到端延迟 | 检查 `notes/research-backlog.md` 和群聊，确认还有哪些方向是自己不了解的，标记为盲区 | daily/ 打卡 + pipeline 运行日志 |
| D17 | 8.21 | 历史机会回测：用 Jupiter Quote API 的历史数据（或 Dune/Flipside），拉过去 N 天的价差数据，算模拟利润分布（不调参，先看数据长什么样） | 读 Bruce 的第三周选题框架，对照自己的数据和直觉，初步排出 4 个候选方向的个人优先级 | daily/ 打卡 + 回测数据快照 |
| D18 | 8.22 | 回测报告：清洗 D17 数据，产出含利润分布/胜率/最大回撤/异常值分析的 Markdown 报告 | 读稳定币套利相关资料（Curve 池、多锚定币价差），和币股 D 路线对照 | daily/ 打卡 + 回测报告初版 |
| D19 | 8.23 | 4 方向深度对比表 v1：原子套利 / 币股 D 路线 / 资金费率套利 / 跨链套利。每个方向填：原理、数据来源、关键风险、个人 edge 判断、所需基建 | 翻看本周广度笔记和盲区标注，追问"除了这 4 个还有没有漏掉的" | daily/ 打卡 + 对比表 |
| D20 | 8.24 | 主网迁移清单：共学结束后如果要把 pipeline 从 devnet 搬到主网，需要准备什么（RPC 节点/账户/Gas 预算/监控告警/风控规则/最小测试资金） | 检查前三周所有的广度笔记，挑出最重要的 3 个方向标注"共学后深挖" | daily/ 打卡 + 迁移清单 |
| D21 | 8.25 | 21 天总结：汇总所有笔记、脚本、数据和打卡，产出一份结构化总结报告。包含：学到了什么 / 验证了什么 / 否定了什么 / 下一步主攻方向 / 需要的资源 | 全地图最终版：标注自己在每个方向的了解程度（0-5）/ 兴趣度（0-5）/ 可行性（0-5） | daily/ 打卡 + 总结报告 + 全地图最终版 |

## 打卡规则

- 每天在 `daily/2026-08-XX.md` 写一条打卡，用 `templates/daily-checkin.md` 模板。
- 打卡内容：今日做了什么（具体到文件名/tx hash/命令）、遇到什么问题、明天的计划。短但可验证。
- 周末（D7/D14/D21）追加周总结，汇总产出和未完成项。
- 所有笔记产出按目录规则放：Solana 专属 → `notes/solana/`，通用笔记 → `notes/`，脚本 → `scripts/`。

## 参考资料地图

| 资料 | 路径 | 用到哪一天 |
|---|---|---|
| Solana 交易模型 | solana.com/docs | D1 |
| Anchor 文档 | anchor-lang.com | D2 |
| Jupiter API | station.jup.ag/docs | D3-D6, D17 |
| Helius RPC | helius.dev | D4-D6 |
| Binance Web3 API | web3.binance.com | D3, D5 |
| Jito 文档 | jito-foundation.gitbook.io | D11-D13 |
| Uniswap V2/V3 白皮书 | uniswap.org/whitepaper.pdf | D8-D9 |
| 币股套利笔记 | `notes/tokenized-stock-arbitrage.md` | D2, D5, D19 |
| 研究候选池 | `notes/research-backlog.md` | D6, D16, D19 |
| 共学 21 天框架 | 群公告 + Bruce 发言 | 全程对照 |
