---
title: Morpho 闪贷灌金库 sNUSD 套利实战
date: 2026-08-13
type: note
status: research
tags:
  - market-map
  - flashloan
  - morpho
  - oracle-arb
  - evm
  - one-shot
source: notes/morpho-flashloan-vault-snusd-arb-case-20260813.md
related:
  - Robinhood Chain 三角套利实战
  - Aave 清算者 0x8d64 解剖
  - MEV
---

# Morpho 闪贷灌金库 sNUSD 套利实战

> tx `0x82a206c9…0c4e72`（Ethereum #25747425，2026-08-13）｜一次性 oracle/DEX 价差套利

## 结论

Morpho Blue **0 费闪贷 $27.7M** 灌进 Lulo USDC 金库触发 allocator 自动部署 3 市场，同时在近空 V4 池以 **$0.686** 扫走 1,034.6 sNUSD（oracle 公允 **$1.0638**，35% 折价），抵押后**满额 91.5% LTV 借出 $1,006.94**。单笔净赚 ≈ **$297**，gas 仅 $0.87。模式 = 免费闪贷 + 金库分配器当杠杆支点 + oracle/DEX 错价。

## 路径

```
闪贷 +$27,722,557.78 → 灌金库 → allocator 铺 3 市场（PT-reUSD/sNUSD/siUSD）
→ 买 sNUSD -$709.93（1,034.6 枚 @ $0.6862）
→ 抵押 + 借出 $1,006.94（99.99% 满额 LTV）
→ 撤出金库 → 还闪贷（0 费）→ 利润 $166.67 打回 bot，头寸留 CalldataChunk
```

## 为什么有 edge

- **oracle ≠ DEX**：MorphoChainlinkOracleV2 **vault 模式**（读 sNUSD 自身兑换率，~$1.06 公允）vs 近空 V4 高费池标价 $0.686——低流动性错价，被搬平即失效
- **借息是计时炸弹**：当时 m2 借息 ~105% APR，仓位必须快进快出
- **可复制骨架**：闪贷灌金库触发 allocator → 借错价抵押品 → 满额借出 → 还闪贷；猎物特征 = 新上线生息代币 + vault 模式 oracle + 近空池

## 取证要点（方法论沉淀）

- Morpho 新版 `market(bytes32)` 返回 6×uint128 头寸数据；市场四要素用 **`idToMarketParams(bytes32)`**（0x2c3c9157）直读
- ChainlinkOracleV2 vault 模式识别：BASE_FEED=0 + BASE_VAULT≠0
- 坑：USDC 6 位 / sNUSD 18 位小数混算易错一个数量级，先统一再对账

## 风险

- 错价池不可再生（一次性策略）
- 105% 借息吃权益
- oracle 回落即清算（CalldataChunk 隔离头寸，单笔风险可控）

## 下一步

- 扫「新生息代币 + vault 模式 oracle + 近空池」三元组 = 同构猎物雷达
- 关注该 bot 后续平仓 tx（还款/赎回路径 = 退出方式实录）
