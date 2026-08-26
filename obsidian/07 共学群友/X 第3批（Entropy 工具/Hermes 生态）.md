---
title: X 第3批（Entropy 工具/Hermes 生态）
date: 2026-08-26
type: note
tags:
  - onchain-arbitrage
  - colearners
---

# 群分享归档：X 链接第 3 批（Chosmos110 Entropy 套利工具 + GitTrend0x Hermes 生态）2026-08-26

> 触发：用户 08-26 连续分享（第 9、10 个 X 链接）
> 方法：fxtwitter 抓取 + GitHub API 核验 repo 真实性
> 关联：`group-share-x-links-batch2-20260826.md`（yourQuantGuy entropy 开源预热）、08-25 六连发⑤（Lighter 200U→2U 小实盘）

## ⑦ Chosmos110（臭臭 panda）— Entropy↔Lighter 套利工具 V0.1.0（推广帖）

**来源**：https://x.com/Chosmos110/status/2092201846211588359（08-25 10:46 UTC，62 likes，配视频）

**内容**：
- Entropy（@entropyIO，HIP-3 PERP DEX，**融资 $14M + 质押 50 万 hyperliquid:native**）的 **IO:SNDK 与 Lighter 的 SNDK 存在价差** → 自制 V0.1.0 工具自动套利，「运行效果良好，实盘见 TG 群」
- 推广三件套：邀请链接 `entropy.io/?r=pandazhai` + Google 表单 + TG 实盘群 + GitHub repo

**GitHub 核验**：`lihanyu81/Entropy---Lighter-Arbitrage-Tool` — **6 stars / 3 forks / 无 license** / 08-25 刚推 → 真实存在但小 repo 零审查

**核验对照**：
- 机制 = 同币（SNDK）跨两个 HIP-3 DEX 的 perp 价差套利——在我们框架内（价差收敛），**无新机制**
- SNDK = 与 Solana 质押衍生品相关（LST 家族）；Entropy/Lighter 都是 HIP-3 RWA/质押 perp DEX——**币股 RWA 候补方向生态成员**（08-25 六连发⑤ Lighter 小实盘同生态）
- 工具不装：无 license + 6★ + 邀请码引流；「实盘效果良好」无独立核验

**判定**：机制可学、生态观察；Entropy/Lighter 的 SNDK 价差可考虑加入 scanner 观察列表（币股 RWA 线推进时）；工具本身不碰

## ⑧ GitTrend0x — Hermes 生态五件套合集（真实 repo，营销腔）

**来源**：https://x.com/GitTrend0x/status/2092433262182543400（08-26 02:05 UTC，11 likes）

**内容**：5 个 Hermes 插件/skill repo 合集（引用帖为同账号另一条 Hermes 合集）

**GitHub 核验（全部真实存在）**：
| repo | stars | license | 定位 |
|---|---|---|---|
| CorsenAI/hermes-connector | 12 | MIT | Chrome 扩展+本地 companion，绑定 Hermes session 与选定标签页 |
| tlehman/litprog-skill | **253** | 无 | 文学编程技能（跨 Hermes/Claude Code/OpenCode） |
| markoblogo/abvx-agent-skills | 15 | MIT | 可审计编码技能包（diffs+证据链+审查闭环） |
| Lethe044/hermes-life-os | **182** | MIT | Personal OS + 记忆 + cron 模式全家桶 |
| adnw-vinc/hermes-nextcloud | 47 | MIT | Nextcloud 文件/笔记/日历/联系人桥接 |

**核验对照**：
- 与我们直接相关（Hermes 重度用户）；帖文是 GitHub trending 搬运+营销腔（「谁先装上谁锁定 2026 下半场最强武装」）打折看，但 repo 真实且部分有真实社区
- **abvx-agent-skills（可审计编码）与 wquguru 方法论帖互证**（审计闭环=拒绝黑盒验收的工程化）
- hermes-life-os 与我们的 daily-rhythm/共学自动化同思路（个人 OS 化）

**判定与可执行项**：
- [ ] 可挑 1-2 个试用：litprog-skill（253★ 社区最大）或 abvx-agent-skills（可审计编码与我们方法论最合）——不急着全装
- [ ] hermes-connector 的「浏览器会话=Agent 第一公民」与我们 browser 工具工作流相关，可参考
- 其余归档备查

## 红旗

- ⑦ 全篇推广（邀请码+表单+TG 群），工具无 license 零审查，实盘数字不可核验
- ⑧ 营销腔合集帖，star 数真实但「最强武装」类表述夸大；无 license 的 repo 注意使用边界
