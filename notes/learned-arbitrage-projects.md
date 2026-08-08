# 学习过的开源套利项目（Paxon 个人清单）

日期：2026-08-06
说明：Paxon 学习过的公开套利代码汇总，大部分只是学习未部署。持续追加。

## 1. Zac Holme (Zacholme7) — Rust MEV/套利

见 `notes/zacholme7-resources.md`（完整归档）
- BaseBuster（Base L2 套利 bot，时薪 0.02 美元的自白）
- Mev-aholic（eth.md + sol.md 资源清单）
- PoolSync / NodeDB / syncoor（数据基础设施）

## 2. tonyke-bot/burberry — paradigm/artemis 改良 fork

- URL: https://github.com/tonyke-bot/burberry
- Stars: 153 | Rust | 2024-03 创建，2025-05 最后更新
- 定位: paradigm/artemis 的 fork + "awesome modifications"
- 结构:
  - `src/`: engine.rs（核心引擎）、action_submitter/（动作提交）、collector/（收集器）、executor/（执行器）、macros.rs、types.rs
  - `examples/`: map.rs、subscribe_mempool.rs（mempool 订阅）
- 依赖: alloy（Ethereum 生态）、telegram 通知 feature、async-stream
- 价值: artemis 是 paradigm 的 MEV 框架，这个 fork 加了 action_submitter/collector/executor 分层——学习**套利引擎如何组织模块**的好样本
- **引擎事件流（artemis 标准架构，burberry 沿用）**：链上数据源(mempool/block) → Collector(收集) → Engine+Strategy(决策, `examples/map.rs`) → Executor(执行/模拟) → ActionSubmitter(上链, flashbots/公开)。事件驱动、模块解耦，每个模块只做一件事。
- **与四层概念框架的对应**：burberry 是「数据层→机会扫描→套利执行→MEV深水区」里**套利执行层**的标准化样本。对比 BaseBuster（同一层，但实战 bot、代码已不编译、混着 alpha）——burberry 更适合学"引擎内部怎么组织"，BaseBuster 更适合学"真实收益的残酷现实"。两者互补：**先读 burberry 建立模块心智，再用 BaseBuster 的 0.02 美元时薪校准预期**。
- 待跟进: `engine.rs` 精读（策略状态机）；`examples/map.rs` 看一个完整套利策略怎么写。

## 3. fuzzland/sui-mev — Sui 链套利 Bot

- URL: https://github.com/fuzzland/sui-mev
- Stars: 775 | Rust | 2025-04-02 创建（单次 commit，即 release 定型；作者 shouc = fuzzland 创始人）
- 定位: Sui Arbitrage Bot（fuzzland 团队，Sui 生态头部安全/审计公司）
- 运行: `cargo run -r --bin arb start-bot -- --private-key {}`
- 支持 DEX: BlueMove、FlowX、Aftermath、Cetus、Kriya、Abex、Navi、Turbos、Deepbook、Shio（10 个 Sui 生态 DEX）
- 架构: `bin/`（arb 套利主程序 + relay 中继） + `crates/` + `scripts/`
- **Relay 设计**: 有验证者节点的话，让验证者把 mempool 交易推送到 relay server，再转给 bot——本质是"用验证者节点的私有交易可见性"做 MEV 访问，Sui 生态的私有通道
- **Sui 特殊性**: Sui 用 Narwhal-Bullshark 共识 + 对象模型，没有传统公共 mempool；交易按 object 分片，机会集中在 shared object（如 Deepbook 订单簿）。所以"拿到机会"靠的不是订阅公共 mempool，而是 relay 私有流
- **Sui 特有的运行细节**: `scripts/merge_gas.sh`（合并 gas 对象——Sui gas 模型用 Coin 对象，需合并才有足够 gas）、`pool_related_ids.txt`（要监控的池子 object ID 清单）、`rust-toolchain.toml`（固定工具链）
- **与四层概念框架的对应**: sui-mev 是**完整的端到端 bot**——`relay`=数据层+MEV深水区（私有交易流），`arb`=机会扫描+套利执行。和 BaseBuster 同属"实战 bot"一类，但跨链（Sui/Move vs Base/EVM），且是发布即定型的"参考实现"而非长期迭代项目
- 价值: 跨链对照——Sui 的 MEV 通道设计与 Solana Jito 类似（验证者/leader 私有通道），对理解"无公共 mempool 链如何做 MEV"有参考意义；**三链 MEV 通道模型**见下方对照表与概念图

## 对照：三个项目的学习角度

| 项目 | 链 | 学习角度 | MEV 通道模型 |
|---|---|---|---|
| BaseBuster | Base (EVM) | 套利 bot 的现实收益预期（时薪 0.02 美元） | 公共 mempool → flashbots bundle / 公开提交 |
| burberry | Ethereum | 套利引擎模块分层（engine/collector/executor） | 公共 mempool 订阅 + ActionSubmitter（flashbots/公开） |
| sui-mev | Sui (Move) | 无公共 mempool 链的 relay 私有通道（对照 Solana Jito） | 验证者节点 relay 私有交易流 → bot → 上链 |

**三链 MEV 通道对照（概念图见下）**：EVM 有公开 mempool（抢跑靠订阅+竞价）；Solana 无公开 mempool、交易发给当前 leader、Jito bundle 是私有提交通道；Sui 同样无公开 mempool、靠验证者 relay 私有流。三者"看到机会"和"提交交易"的机制完全不同，但都收敛到同一目标——在别人之前把套利交易放上链。

## 待跟进

- burberry 的 engine.rs 精读（套利引擎状态机）
- sui-mev 的 relay 机制对照 Jito bundle（D11-D13）
- 持续追加新学习的项目
