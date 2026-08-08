---
title: 0xbdb3ba 统计套利案例
date: 2026-08-07
type: case
status: active
tags:
  - 失败复盘
  - stat-arb
  - 机构垄断
  - MEV
source: notes/case-stat-arb-0xbdb3ba-450k.md
---

## 链上事实（RPC 验证）

- tx `0x6dc21...d53ee`，block 25322434
- gas：limit 15.3M / used 10.15M（单 tx 消耗 10M+ gas）
- gasPrice 895.25 gwei（极高，竞争激烈）
- **txFee ≈ 9.088 ETH ≈ $17,000（1.7 万 U）**
- input 10,596 bytes（50+ 单腿 swap 打包一笔 tx），logs 448 条，涉及 30+ 代币
- 毛收益 ≈ +$423,017；扣 gas ≈ 净 +$406,000（约 40.6 万 U）

## 机制解读

- **stat arb（CEX-DEX 统计套利）**，非普通 DEX 搬砖：同一笔交易内完成 50+ 单腿 swap，跨 30+ 资产重新平衡
- WETH +2621 是中间库存不是利润——净收益 = 所有腿汇总（约 42 万）
- **gas 1.7 万 U 本身是门槛**：能承受的只有机构级玩家。Greenfield 报告：stat arb 市场 Wintermute + 0xbdb3ba 合计占优先费支出 83%，集中度极高

## 与共学认知的呼应

1. **优先费 = MEV 利润代理指标**：这笔 gas/利润 ≈ 4%——Greenfield 估 stat arb 平均利润率约 10%（90% 交优先费），大机会 30% 量级，吻合
2. **统计套利已被垄断** — 个人套利者不该碰的方向的实证
3. **套利本质是找摩擦** — 0xbdb3ba 的 edge 不是信息（机会公开），是**执行规模 + 库存 + 延迟**——不可复制的结构性优势

## 对个人研究者的启示

这是「为什么个人走 stat arb 没戏」的硬证据。对应 [[套利策略全景]] 竞争格局金字塔：stat arb 站在金字塔顶端（量化基金层），个人唯一可切入的是独立开发者层（长尾/新链窗口/组合创新/时区差）。

## 可复用脚本模式

`eth_getTransactionByHash` + `eth_getTransactionReceipt` → 解析 Transfer 事件 → 按合约净流量折算。可复用做链上收益核算。

## 连接

- [[套利策略全景]] — 竞争格局：stat arb 在顶端
- [[MEV]] — 优先费 = MEV 利润代理
- [[我的 Edge]] — 结构性优势不可复制
