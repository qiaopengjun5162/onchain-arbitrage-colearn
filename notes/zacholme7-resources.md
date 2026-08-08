# Zac Holme (Zacholme7) — Rust MEV/套利开发者资源

日期：2026-08-06
来源：https://github.com/Zacholme7
说明：Paxon 学习过这位大佬公开的代码，对套利有懵懂概念，但只是学习未实际部署。

## 个人简介

Zac Holme，Rust 生态 MEV/套利开发者，sigp（SSV 协议）成员。作品集中在以太坊/Base 生态的套利机器人和链上数据基础设施。

## Pinned 仓库

| 仓库 | 说明 | Stars | 语言 |
|---|---|---|---|
| [PoolSync](https://github.com/Zacholme7/PoolSync) | DeFi 池扫描器 | 85 | Rust |
| [BaseBuster](https://github.com/Zacholme7/BaseBuster) | Base L2 套利机器人 | 80 | Rust |
| [sigp/anchor](https://github.com/sigp/anchor) | SSV 协议的 Rust 实现 | 68 | Rust |
| [NodeDB](https://github.com/Zacholme7/NodeDB) | Revm DB，从 Reth DB 拉最新状态 | 43 | Rust |
| [syncoor](https://github.com/Zacholme7/syncoor) | EVM 链历史+实时事件日志同步 | 8 | Rust |
| [Mev-aholic](https://github.com/Zacholme7/Mev-aholic) | MEV 资源清单（eth.md + sol.md） | 78 | - |

## BaseBuster 要点

- Base L2 套利机器人，"mid-tier"
- **作者自述**："This bot has bought me a couple coffees, but my hourly wage would be like 0.02$ an hour. This is not a infinite money glitch!!!"
- 已移除部分 alpha，当前不编译，但代码里有大量有价值的信息
- 创建于 2024-06-28

> 诚实披露：即使是大佬的实战 bot，时薪也只有 0.02 美元——套利不是印钞机，这是最好的现实教育。

## Mev-aholic 资源清单（已抓取）

### Solana (sol.md)

**套利**：
- https://github.com/0xNineteen/blog.md — Rust 宏套利教程
- https://github.com/ARBProtocol/solana-jupiter-bot
- https://github.com/buffalojoec/arb-program
- https://github.com/0xNineteen/solana-arbitrage-bot
- https://github.com/egaotan/solana-arbitrage
- https://github.com/egaotan/solana-arbitrage-contract-v6.0
- https://github.com/AxelAramburu/MEV_Bot_Solana
- https://github.com/ARBProtocol-DevRabby/solana-arbitrage-bot
- https://github.com/cutupdev/Solana-Arbitrage-Bot

**清算**：
- https://github.com/mrgnlabs/eva01
- https://github.com/egaotan/solana-liquidate
- https://github.com/01protocol/zo-keeper

**可视化**：
- https://fd.juicystake.io/

### Ethereum (eth.md)

**套利**：paco0x/amm-arbitrageur、flashbots/simple-arbitrage、thasarito/simple-arbitrage-rs、KuTuGu/FrontrunBot、BowTiedDevil/degenbot、mev-squad/Atomic-Arbitrage、dexloom/loom、flashbots/hindsight、RenatoDev3/rusty-john、eeish/unibot-rs、kyzooghost/arbitrage-graph-engine、Zacholme7/BaseBuster 等

**三明治 (Sando)**：libevm/subway、mouseless0x/rusty-sando、refcell/subway-rs、0xethghost/sando-rs

**清算**：yieldprotocol/yield-liquidator、aave-liquidation、liquity/liqbot、grim-reaper 等

**符号执行**：Koukyosyumei/rhoevm、palkeo/pakala、ethereum/hevm、trailofbits/manticore

**工具/基础设施**：alloy-rs/alloy、bluealloy/revm、paradigmxyz/reth、paradigmxyz/artemis、0xKitsune/cfmms-rs、darkforestry/amms-rs、mevcheb/optimal-sandwich 等

**其他资源清单**：autistic-symposium/mev-toolkit、0xOsiris/Mev_Book、0xemperor/Awesome-MEV、0xalpharush/awesome-MEV-resources、HilliamT/awesome-mev-searching、flashbots/mev-research

**Sleuthing 工具**：sorellalabs.xyz/explorer、libmev.com、eigenphi.io、mevwatch.info、zeromev.org、relayscan.io

**写作者**：medium.com/@solidquant、degatchi.com、substack.com/@eigenphi

## 对共学的价值

1. **Solana 套利资源清单**（sol.md）直接服务个人 Solana 主线——9 个套利 bot、3 个清算 bot
2. **BaseBuster 的诚实披露**是对"套利暴富"幻觉的解毒剂
3. eth.md 的 Sando/符号执行/工具分类是 MEV 深水区的系统索引
4. eigenphi.io（MEV 可视化）正是官方路线图 L0001 挑战版任务提到的工具

## 概念框架：从代码反推的套利 bot 构成

学习这些代码后，对"套利 bot 到底由什么组成"形成的基础认知（仅学习，未部署；Paxon 自述"懵懂概念"）：

1. **数据层（NodeDB + syncoor）= 眼睛**：实时拿到链上状态（最新账户/池子余额）和事件日志（Swap/Transfer）。没有这层，后面都是盲猜。
2. **机会扫描（PoolSync）= 雷达**：周期性比对各池子价格，发现偏离即候选机会。决定"在哪找价差"。
3. **套利执行（BaseBuster）= 手**：发现价差后，构造原子交易（一笔 tx 内买低卖高），抢在别人前面上链。决定"能不能吃到"。
4. **MEV 深水区（Mev-aholic/eth.md）= 进阶手段**：三明治、back-run、清算，拼的是 mempool 可见性 + 排序权，更 aggressive，也是风险与合规灰区。

**关键认知（来自 BaseBuster 作者自白）**：即使实战 bot，时薪也只有 0.02 美元——套利不是印钞机，技术能跑通 ≠ 有正收益。这层现实预期比代码本身更值钱。

**与本项目主线的对应**：
- 咱们 LI.FI 主线 ≈ 跨链版的"机会扫描 + 执行"（跨所/跨链价差）
- 咱们 Solana 主线 ≈ 理解"执行层"如何工作（Jito/MEV/bundle/priority fee）
- 当前阶段（研究向、未实盘）和 BaseBuster 的"咖啡级收益"现实一致——先建立流程，不急着部署。

## 待跟进

- 逐个评估 sol.md 里的 9 个 Solana 套利仓库，挑 1-2 个深入阅读（可排入 D11-D13 Jito 学习）
- BaseBuster 虽不编译，架构和策略思路可读（对应 mev-flashbot-sandwich-rs 的价值）
