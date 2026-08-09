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
| **链上取证方法论**（怎么分析一个套利地址） | `notes/aave-liquidator-0x8d64d775-address-research-20260808.md` · `notes/robinhood-arb-0xd7121208-address-research-20260808.md` |
| **赛道选择结论**（清算/原子/跨链怎么选） | `notes/arbitrage-track-selection-20260808.md` |
| **风控总纲**（套利=概率游戏，敞口控制生死线） | `notes/arb-risk-black-swan-20260809.md` |
| **下架合约价差套利**（群策略实证：HFT 439bps + OI 累计偏离 + L/S ratio 净方向） | `notes/binance-delisting-arb-verified-20260809.md` · `scripts/binance_delisting_review.py` · `scripts/delisting_monitor.py` |
| **期现套利成本模型**（主流币空间恒负 -27~-32bps，持续性过滤） | `notes/basis-arb-model-first-run-20260809.md` · `scripts/basis_arb_model.py` |
| **长尾币期现测试**（快照假象 vs 持续性：GOAT 54%★ / MEW 17%✗） | `notes/longtail-basis-test-snapshot-vs-persistence-20260809.md` |
| **BitMart 第一桶金**（充值时间差 alpha：确定性失衡时刻+提前埋伏） | `notes/bitmart-first-pot-alpha-20260809.md` |
| **期现套利隐藏爆仓机制**（1倍杠杆统一账户也爆 + 振幅过滤双刃剑） | `notes/basis-arb-hidden-blowup-and-amplitude-filter-20260809.md` |
| **资金费率信号方法论**（Z-score + OI 交叉） | `notes/funding-rate-signal-engineering-20260808.md` |
| **币股时钟差**（闭市漂移→开盘收敛） | `notes/tokenized-stock-arbitrage.md` |
| **监控脚本全家桶**（8 个哨兵） | `scripts/` + `daily/2026-08-08.md` 总结 |
| **自建节点/基建验收清单**（延迟/吞吐/一致性/资源） | `notes/node-infra-acceptance-checklist-20260808.md` |
| **Solana 研究线**（Rust 双实现） | `scripts/solana-rs/`（quote/build/swap/spread）· `scripts/solfi-sim/`（LiteSVM 模拟器，含 slippage 完整环）· `notes/priority-fee-monitor-20260809.md`（执行成本监控） |

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

官网打卡入口：

https://intensivecolearn.ing/programs/b43d2e97-ed88-4ca3-b12f-7ef672b01205
