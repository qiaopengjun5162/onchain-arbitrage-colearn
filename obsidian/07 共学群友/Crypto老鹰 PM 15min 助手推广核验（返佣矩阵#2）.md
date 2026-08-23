---
title: Crypto老鹰 PM 15min 助手推广核验（返佣矩阵#2）
date: 2026-08-23
type: note
tags:
  - onchain-arbitrage
  - colearners
---

# Crypto老鹰 PM 15min BTC 助手推广核验（2026-08-23 群分享归档 #2）

> 来源：https://x.com/laoyingkhq/status/2091374128909476321（3474 views / 25 likes）
> 归档：2026-08-23 ｜ ⚠️ **老鹰同日第 2 条 PM 推广**（第 1 条 = 5min BTC 脚本，见 `notes/laoying-pm-5min-script-verify-20260823.md`）
> 关联：`notes/pm-winners-behavior-20260823.md`（runes_leo 赢家研究）、`notes/term-finance-governance-attack-forensics-20260823.md`

## 帖子内容

- 叙事：「PM 套利机器人源码泄露」→ GitHub 开源仓库从零教搭建，免费
- 战绩：15min BTC 短线市场单日 $5 万+；某交易者 502 次预测 98% 胜率赚 $55,840；最炸裂单笔 BTC 2/2 凌晨 1:15-1:30 ET 涨跌市场赚 $7,914（收益率 170%），核心=抓币安行情延迟价差
- 链接：GitHub（FrondEnt/PolymarketBTC15mAssistant）+ **双 referral**（Polymarket via=YINGGE888 + PolyCop_BOT）

## 核验结果（GitHub API + clone）

| 项 | 结论 |
|---|---|
| 仓库存在 | ✅ 真实：861★ / 342 fork / 2026-01-29 创建 |
| LICENSE | ❌ **无 LICENSE = 版权保留，不能拷**（skill 铁律） |
| 活跃度 | ⚠️ 2026-01-29 创建后**当天就停止推送**（pushed=创建日），8 个月没更新——「从零到一教学」仓库半成品嫌疑 |
| 内容 | 📄 只有 README + package.json + src/（42KB 小仓库），README 5KB |
| 单日 $5 万/98% 胜率/170% | ⚠️ 老鹰一贯夸大叙事，无独立验证；「币安行情延迟价差」理论上有道理（D18 事件窗口同族）但**8 个月未更新的仓库跑出单日 5 万**存疑 |
| 跟单 PolyCop_BOT | ⚠️ referral 推广，跟单=交钱给别人执行，不采用 |

## 判定

**仓库不装（无 LICENSE + 8 个月无更新），叙事打折，但「币安行情延迟价差」思想有值**：
- 「抓币安延迟」= 我们 D18 事件窗口/涨跌幅差套利的**时间维版本**（不是空间价差，是时间差）——币安 API 推送延迟 → 15min 涨跌市场定价滞后，抢定价修正
- 与 JXiaoLoong「ETF 涨幅差」、bStock「闭市漂移」同族：**都是「同一资产在两个市场定价不同步」**
- 老鹰今天连续 2 条 PM 推广（5min + 15min 脚本）+ 同一 PolyCop_BOT referral = **返佣矩阵实锤**，列入「群友推广黑名单参考」（与 08-21 锁利机器人核验合并）

## 下一步

- [ ] 「交易所行情延迟 → 15min 涨跌市场定价滞后」记为 PM 线观察点（若后续做 PM 扫描器升级考虑）
- [ ] 老鹰推广一律：先验 repo + LICENSE + 更新活跃度 + 数字来源，跟单/付费一律不采用（并入已有待办）
