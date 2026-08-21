---
title: Hermes 插件生态核验
date: 2026-08-21
type: note
tags:
  - onchain-arbitrage
  - tool
---

# Hermes 插件生态推荐核验（2026-08-21 群分享）

> 来源：https://x.com/GitTrend0x/status/2090608391735652365（2026-08-21）
> 归档日期：2026-08-21 ｜ 核验方法：GitHub API（代理）

## 核验结论（先说结果）

帖子推 5 个 Hermes 插件/技能，**全部真实存在**（1 个拼写笔误已修正），质量分层明显：

| 插件 | repo | stars | 核验 | 评价 |
|---|---|---|---|---|
| **Web 作战室** | outsourc-e/hermes-workspace | 6,471 | ✅ | 🟢 精品：原生 Web 指挥中心（聊天/终端/记忆/技能/Kanban/多 Agent Swarm） |
| **技能自进化** | AMAP-ML/SkillClaw | 2,469 | ✅ | 🟢 精品：从 session 数据自动进化技能库 |
| **全家桶插件** | 42-evey/hermes-plugins | 408 | ✅ | 🟡 23 个生产级插件（目标/桥接/模型路由/成本/记忆） |
| **文学编程** | tlehman/litprog-skill | 251 | ✅ | 🟡 代码+散文可执行笔记本，跨 Hermes/Claude/OpenCode |
| **像素办公室** | teknium1/hermes-pixel-office | 70 | ✅ | 🟡 可视化趣味（session/subagent 动画小人） |
| **模型切换** | jdtimothy/nous-models-plugin | 1 | ✅（帖中 jdtymothy 为笔误） | 🟡 桌面插件看 Nous Portal 模型价格折扣秒切 |

## 对我们共学工作的价值

- **outsourc-e/hermes-workspace（6.4k stars）最值得试**：Web 作战室 = 我们 Hermes 工作流的可视化入口，多 Agent Swarm + Kanban 与我们 Kanban 分工模式契合
- **SkillClaw（2.4k stars）**：技能自进化 = 我们的 skill 体系（已积累 20+）可以自动去重/改进——但注意「自动改技能」有风险，需人审（改坏 skill 比没有 skill 更糟）
- 其余按需：模型切换（我们多 provider 场景有用）、像素办公室（趣味）
- ⚠️ 通用纪律：装第三方插件前先核验（本帖就是例子：1/6 拼写错），插件=执行第三方代码，安全边界要检查

## 结论

- 帖子有推广性质但内容基本属实，精品两个（workspace/SkillClaw）
- 对当前任务无紧急依赖，列为「工具库备选」；若要提升 Hermes 工作流效率，优先试 workspace
