# 数据源选型：为什么直接读链上池子优于聚合器报价

日期：2026-08-05（D1 意外收获）

## 背景

D1 的 Jupiter quote 脚本因网络问题跑不通（quote-api.jup.ag 全系不可达，且 v6 端点已被官方弃用）。改用 Helius RPC 直接读 Raydium SOL-USDC 池子的 vault 余额，一次跑通。

## 第一次实测数据（2026-08-05）

- SOL Vault: 67,845.48 SOL / USDC Vault: 5,033,916.36 USDC
- 池子价格：1 SOL = $74.1968
- 模拟 swap 1 SOL 输出 73.9731 USDC，损耗 -0.3015%
- 损耗拆解：0.30% 基本是池子手续费档位，1 SOL 相对 6.7 万 SOL 的池子深度，价格冲击只有约 0.0015% 可忽略——这直观展示了"滑点 = 手续费 + 价格冲击"的结构，小池子里固定费率才是大头

## 为什么这条路线本来就更好

1. 学习价值：读池子状态逼着理解 AMM 数据结构（vault 余额、恒定乘积、decimals 换算），Jupiter 给的是别人算好的答案，池子状态是自己可验证的事实。
2. 策略价值：聚合器报价是"市场共识价"，共识之内无价差（见 `notes/aggregator-routing.md`）。正经套利监控都是直接读链上状态，quote API 又慢又是二手数据。
3. 工程价值：少一个外部依赖，少一个被墙/弃用的风险点。今天同时踩了"API 被墙"和"v6 端点弃用"两个坑，直连 RPC 把这两个风险都消掉了。

## 留下的问题

- 路径路由（多跳 swap 怎么拆）还是得靠 Jupiter 这类聚合器，代理问题日后要解决
- 下一步读 Orca Whirlpool：价格要从 sqrtPrice 算（`price = (sqrtPrice / 2^64)^2` 再按 decimals 调整），CLMM 的定价读法比恒定乘积复杂，是第 2 周 AMM 数学课的预习
- 脚本应记录"链上读数耗时"，延迟数据以后做策略评估用得上

## 连接

- `notes/aggregator-routing.md`：聚合器作为参照系而非唯一数据源
- `notes/solana/transaction-model.md`：D1 主线笔记
