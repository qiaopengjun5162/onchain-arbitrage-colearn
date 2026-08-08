# Solana 研究线

## 定位

Solana 先作为独立研究线，不急着实盘套利。

研究目标是理解：

- Solana 交易结构
- compute units 和 priority fee
- Jito / MEV / bundle / block engine
- DEX 和路由聚合
- perp / funding / liquidation
- RPC、Geyser、indexer 和实时数据
- 模拟盘与实盘达成率差异

## 当前判断

Solana 值得做，但不要一上来卷最薄的速度型 MEV。

原因：

- 速度型 MEV 会很快变成 RPC、节点、Jito、低延迟、模拟准确性和交易落地率竞争。
- 个人研究者更适合先做数据层、监控层和执行质量分析。
- 如果策略本身不够厚，单纯升级语言、硬件或机房意义有限。

## 优先问题

1. Solana 上什么数据是容易拿到、但还没被很好整理的？
2. Jupiter/Raydium/Orca/Meteora 的路由和池子变化能否形成可监控信号？
3. Drift 等链上 perp 的资金费率、清算和仓位变化有什么结构？
4. Jito bundle、priority fee、CU、交易失败率如何影响真实执行？
5. Paper Trading 里哪些收益会在实盘中消失？

## 推荐顺序

### 第一阶段：地图

- Solana transaction / account model
- fee / priority fee / compute unit
- DEX: Jupiter, Raydium, Orca, Meteora
- perp: Drift
- oracle: Pyth
- infra: Jito, Helius, Triton, Geyser

### 第二阶段：数据

- 价格
- 池子深度
- 路由变化
- priority fee
- 失败交易
- funding
- liquidation
- 大额交易

### 第三阶段：验证

- 历史回放
- 实时观察
- Paper Trading
- 小资金测试边界

### 第四阶段：工具化

- watcher
- route snapshot
- funding monitor
- liquidation monitor
- execution quality tracker
- Hermes research agent prompt

## 安全边界

- 不在任何笔记中保存私钥、助记词、API Secret。
- 不用主钱包跑第三方 bot。
- 第三方二进制和闭源工具只做隔离环境研究。
- 任何实盘前必须先写清成本模型、失败条件和最大可承受损失。
