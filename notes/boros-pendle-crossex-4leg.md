# Boros by Pendle——跨所套利四腿策略（24.3% APR）开源工具

> 来源：https://x.com/pendle_grandma/status/2085369602360344631（Yoko | Pendle，2026-08-06）
> 工具：https://crossexboros.com（开源交易 UI，Pendle CTO @gabavineb 开源）
> 归档：2026-08-07（Hermes 记录，用户分享）
> 关联：`notes/2026-08-06-group-sharing.md`（Gate CrossEx 笔记）、`notes/arbitrage-playbook-text-version.md`

---

## 一句话

Pendle CTO 开源的跨所套利 UI，把「Hyperliquid 空 ETH + OKX 多 ETH」的四腿策略做成一键工具，标注 **24.3% APR 固定收益**，到期日 9 月 25 日。

## 策略结构（四腿）

| 腿 | 方向 | 交易所 | 备注 |
|---|---|---|---|
| 交易所腿 1 | 空 ETH | Hyperliquid | CrossEx 跨所综合保证金（需 KYC） |
| 交易所腿 2 | 多 ETH | OKX | 杠杆 25x（可按自己风控调低） |
| Boros 腿 1 | 空 ETH | Hyperliquid FR 市场 | 资金费率方向 |
| Boros 腿 2 | 多 ETH | OKX | 与交易所腿配合 |

**本质**：跨所资金费率套利（正费率：空永续 + 多现货/合约对冲），用 CrossEx 综合保证金避免单边爆仓，再叠加 Boros（Pendle 的收益/费差产品）腿。

## 关键点

- **开源 UI + AI prompt 都写好了**——门槛被刻意降低（官方定位：「帮助更多人接触原本门槛很高的跨所套利」）
- 每一步都有市场链接直接点击——保姆级操作
- 24.3% APR 是**宣传口径**，需 DYOR 验证：费率会变、9 月 25 日到期后的续期条件未知

## 与知识库已有内容的关联

- **同一工具家族**：8/6 群分享的 yourQuantGuy 开源前端（gate-crossex）也是 CrossEx 生态——Pendle 这个是官方 CTO 出品的另一入口
- **CrossEx 机制**（来自群分享）：跨所统一保证金，传统跨所波动 20% 单边爆仓，CrossEx 需价差拉大 20% 才爆仓
- **Paxon 计划**（8/6 记录）：实际安装跑一下 gate-crossex 验证体验——Boros 是同一验证的官方替代品

## 风险（对照共学知识）

- 跨所套利已知风险：逼空、ADL、抵押品折价、保证金率、仓位集中、价差不收敛、两头挨打
- 25x 杠杆是高危默认值——宣传 APR 不能直接当收益
- CrossEx 是 Gate 产品，有监管/交易所信用风险
- 资金费率套利扣成本后年化可能远低于宣传（共学实测结论：纯费率套利扣成本后可能不到 3%）

## 备注

- 官方推广文（Yoko | Pendle 是官方账号），立场乐观，APR 数字需打折
- 待办（来自 8/6 群分享）：实际装跑验证 CrossEx 体验——Boros 的 UI 比 gate-crossex 前端更「保姆级」，可优先试
