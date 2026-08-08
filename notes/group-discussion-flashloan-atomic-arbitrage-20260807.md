# 群讨论：原子套利零本金——闪电贷 + Flashbots（2026-08-07）

> 来源：Paxon 群内观点（Hermes 套利共学 Telegram），2026-08-07
> 归档日期：2026-08-07（Hermes 记录）

## 用户观点（原话要点）

- 原子套利不需要本金，不需要保证金。
- 同一笔交易内通过闪电贷（flash loan）借钱 → 按套利路径交易 → 若盈利，归还借款，剩余即毛利，再扣 gasFee 即利润。
- 若发现不赚钱，直接 revert 即可；使用 Flashbots 提交，revert 都不会上链，不消耗 gasFee。
- Uniswap v2/v3/v4 都支持闪电贷。

## Hermes 核实与精确补充（2026-08-07）

### 1. 闪电贷不是免费的，有借款成本

| 来源 | 费用 |
|---|---|
| Uniswap v2 flash swap | 池子交易费率（默认 0.3%） |
| Uniswap v3 flash | 池子费率（0.05% / 0.3% / 1%） |
| Balancer flash loan | 免费（0） |
| AAVE / dYdX / Maker flash | ~0.05%–0.09% |

盈利条件：毛利必须 > 闪电贷费 + gas + 滑点 + 失败准备金。零本金 ≠ 零成本。

### 2. "revert 不上链、不付 gas"的前提是私有提交

- 走 Flashbots bundle / MEV-Share 等私有通道：bundle 整体 revert 则不被打包，确实不付 gas。
- 公开 mempool 裸发交易：revert 的交易照样上链、照样付 gas。
- 正确流程：先本地/eth_call 模拟 → 只有链上 `minProfit` 条件通过才发 bundle。

### 3. 原子性只存在于单链单笔交易内

- 同链 A→B→A 闭环：闪电贷 + 一笔交易内完成，可整体回滚 → 零本金成立（对应 lifi-playbook 模型三）。
- 跨链（模型①②⑤）：两笔交易不在同一原子上下文，无法整体回滚，"买卖只成功一笔"风险依然存在，闪电贷帮不上忙——这是文档把多链预置库存排第一的原因。

### 4. 零本金解决"钱"的问题，不解决"抢"的问题

- 同链 DEX 价差套利是 MEV bot 主战场：人人都能闪电贷套利，竞争门槛是延迟、排序权、私有通道质量，不是资金。
- 竞争推高成功交易的 gas；尝试失败免费，但频繁失败说明策略本身没有 edge。
- lifi-playbook 模型三 Go 条件正好对应：原子合约 + 链上 minProfit 检查 + 私有通道 + 排除路径重叠。

## 关联

- `lifi-playbook-w3player-20260807/03-same-chain-dex-arbitrage.md`（两种执行方式：自有本金 vs 闪电贷）
- `group-discussion-timestamp-alignment-20260807.md`（时间序列对齐是判断"路径是否真盈利"的前置）
