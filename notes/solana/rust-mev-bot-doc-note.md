# rust-mev-bot 文档摘记

资料：

- Quickstart: https://rust-mev-bot.solboxs.com/getting-started/quickstart
- GitHub: https://github.com/SaoXuan/rust-mev-bot-shared

## 定位

这份资料可以作为 Solana MEV bot 的学习样本，用来观察一个第三方工具如何组织：

- 配置
- 私钥
- RPC
- Jito 相关参数
- DEX 选择
- 交易金额
- 风险参数
- 日志和运行状态

但它不应该直接作为可信执行工具。

## 可学习点

### 1. Bot 配置维度

文档体现了一个 Solana MEV bot 至少需要关心：

- wallet / private key
- RPC endpoint
- Jito tip
- trade amount
- DEX / route
- slippage
- profit threshold
- logging
- retry / failure handling

这些字段可以反推我们自己的研究数据结构。

### 2. 执行链路

Solana MEV 不是只看价差，还要处理：

- 交易模拟
- priority fee / tip
- bundle 或低延迟通道
- compute units
- 交易失败
- RPC 延迟
- 机会过期

### 3. 文档风险

风险点：

- 第三方二进制需要高度谨慎。
- 任何要求填私钥的工具都必须隔离验证。
- 收益宣传不能当作证据。
- GitHub 里如果没有完整核心源码，不能把它当作可审计项目。

## 研究用法

可以让 Hermes 做这些任务：

- 提取配置字段，整理成 MEV bot 数据模型。
- 对照 Jito/Solana 官方文档，核验每个字段的真实作用。
- 设计一个不需要私钥、不交易的 watcher。
- 写执行风险清单。
- 写“为什么第三方 MEV bot 不能直接跑”的安全笔记。

## 不做什么

- 不导入主钱包。
- 不用真实资金跑未审计工具。
- 不复制收益宣传。
- 不在公开笔记里发布可直接执行的套利参数。

## 下一步

1. 对照 Jito 官方文档，整理 bundle、tip、block engine 的基本概念。
2. 对照 Solana 官方文档，整理 priority fee 和 CU 如何影响落地。
3. 先写一个只读型 Solana watcher 需求文档。
