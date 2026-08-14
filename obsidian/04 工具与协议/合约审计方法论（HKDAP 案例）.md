---
title: 合约审计方法论（HKDAP 案例）
date: 2026-08-14
type: note
status: research
tags:
  - audit
  - security
  - stablecoin
  - forensics
source: notes/hkdap-audit-digest-20260814.md
related:
  - 研究拆解工作流
  - 链上套利工具栈与执行现实
---

# 合约审计方法论（HKDAP 案例）

> BlockSec 审计香港首个持牌港元稳定币 HKDAP 的 13 条发现 + 可复用取证手法。

## 案例一句话

HKDAP（Anchorpoint：渣打香港+HKT+Animoca，HKMA 持牌）以太坊主网合约：KYC 撤销失效（fail-open）、治理单签、transfer 路径绕过、主网部署 debug 版——**牌照≠代码达标，一切以链上代码为准**。

## 审计取证五招（可复用）

1. **角色注册表枚举**：读注册表存储，枚举全部角色 + 持有者 + 授权范围
2. **authorizationMatrix 直读**：每操作签名门槛从治理合约矩阵读出（单签/双签），不看文档
3. **升级历史还原**：proxy implementation 时间线 + 每次 upgradeTo 的签名人；**角色轮换会让旧签名人从注册表消失**，只能查交易历史
4. **存储槽直读**：公链上「只读角色锁」形同虚设——任何数据都能读槽位
5. **事件 vs 状态对账**：销毁事件指向 address(this) 但余额 0 = 索引器陷阱——结论以状态为准

## 关键认知

- 「牌照和文档怎么写并不作数，只取决于代码」——宣称 vs 链上证据，永远信后者
- 根因：手写 ERC-20/审批引擎/代理，弃用 Safe+OZ AccessManager+Timelock 成熟积木——缺陷几乎全在自己实现的部分
- 新「持牌/受监管」币风险模板：手写 ERC-20？无时间锁？单签？13 条即现成 checklist

## 衔接

- 稳定币套利方向：HKDAP 标记观察（B 端币 DEX 流动性未知，不投入）
- 与 `evm-arbitrage-tx-forensics` skill 互补：交易取证（三件套）+ 合约审计（本页）
