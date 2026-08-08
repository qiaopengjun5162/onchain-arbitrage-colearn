# Solana 资料地图

## 官方基础

- Solana Docs: https://solana.com/docs
- Solana Foundation Developer Courses: https://github.com/solana-foundation/developer-content/tree/main/content/courses
- Solana Explorer: https://explorer.solana.com/
- Solana Playground: https://beta.solpg.io/
- Solana Cookbook 中文版: https://solanacookbook.com/zh/
- creatorsand/solana-co-learn: https://github.com/creatorsand/solana-co-learn
- Anchor Docs: https://www.anchor-lang.com/docs
- Anchor Installation: https://www.anchor-lang.com/docs/installation
- Anza Wallet Adapter GitHub: https://github.com/anza-xyz/wallet-adapter
- Anza Wallet Adapter Example: https://anza-xyz.github.io/wallet-adapter/example/
- Solana issue #27598 - cargo-build-bpf/sbf: https://github.com/solana-labs/solana/issues/27598
- Solana issue #34987 - solana-program rustc mismatch: https://github.com/solana-labs/solana/issues/34987
- Transaction Fees: https://solana.com/docs/core/fees
- Compute Optimization: https://solana.com/developers/guides/advanced/how-to-optimize-compute
- Geyser Plugins: https://docs.solanalabs.com/validator/geyser

研究重点：

- 交易如何构造和落块
- 如何按官方课程系统补 Solana 开发基础
- fee、priority fee、compute unit 如何影响执行
- 如何拿到账户、交易、slot 和实时流数据
- 如何用官方 Explorer 核验交易、slot、账户和程序信息
- 如何用 Solana Playground 快速写、跑和分享小型 Solana / Anchor 示例
- 如何用 Cookbook 查账户、程序、交易、PDA、Token、Anchor 和本地开发示例
- 如何参考社区共学仓库设计自己的 Solana 学习路线和练习任务
- 如何用 Anchor 理解 Solana 程序开发、账户约束、IDL、测试和客户端交互
- 如何安装 Rust、Solana CLI、Anchor CLI/AVM、Node/Yarn，并跑本地 validator 和 Anchor 项目
- 如何在前端连接钱包、选择网络、签名交易和发送交易
- 如何排查旧版 Solana CLI 的 `cargo build-bpf` / `cargo build-sbf` 工具链路径问题
- 如何排查 `anchor build` 中 `solana-program` 要求的 Rust 版本和实际 SBF Rust 工具链不一致的问题

## MEV / 执行层

- Jito Docs: https://docs.jito.wtf/
- rust-mev-bot Quickstart: https://rust-mev-bot.solboxs.com/getting-started/quickstart
- rust-mev-bot shared GitHub: https://github.com/SaoXuan/rust-mev-bot-shared

研究重点：

- bundle
- block engine
- private / low-latency transaction path
- priority fee 和 tip
- 模拟准确性
- 交易落地率

注意：

第三方 MEV bot 资料只作为学习样本，不作为直接运行建议。

## DEX / 路由

- Jupiter Developer Docs: https://dev.jup.ag/
- Titan DART Swap API Access: https://titan-exchange.gitbook.io/titan/developer-doc/dart-swap-api/get-api-access
- Raydium Docs: https://docs.raydium.io/
- Orca Docs: https://docs.orca.so/
- Meteora Docs: https://docs.meteora.ag/

研究重点：

- quote / route
- swap API access / rate limit / transaction building
- 池子深度
- 价格冲击
- 路由切换
- 新池子
- DLMM / CLMM 机制

## Perp / 资金费率

- Drift Docs: https://docs.drift.trade/

研究重点：

- funding
- liquidation
- oracle
- insurance fund
- keeper / filler
- 盘口和仓位数据

## Oracle / 数据

- Pyth Docs: https://docs.pyth.network/
- Helius Docs: https://docs.helius.dev/
- Helius Dashboard: https://dashboard.helius.dev/login?redirectTo=/dashboard
- Triton One Docs: https://docs.triton.one/
- Solscan: https://solscan.io/
- WebSocketKing: https://websocketking.com/
- Solana Notion 资料页: https://attractive-spade-1e3.notion.site/Solana-fca856aad4e5441f80f28cc4e015ca98

研究重点：

- 价格源
- WebSocket / enhanced transaction
- webhook
- DAS / RPC
- Geyser / streaming
- 延迟和稳定性
- RPC/API/Webhook 项目管理和用量观察
- 人工核验交易、账户、Token、程序调用和资金流
- 手动测试 WebSocket 连接、订阅消息和实时数据格式
- 人工阅读或导出 Notion 资料后，拆成长期 Obsidian 笔记

## 待补充

- Phoenix
- OpenBook
- Kamino
- Marginfi
- Sanctum
- Tensor / NFT MEV
- SolanaFM / Explorer API
- Dune / Flipside / Artemis / TopLedger
