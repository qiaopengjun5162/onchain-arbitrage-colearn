# goal-driven：master 监督 subagent 的无限循环框架（立党）

> 来源：https://x.com/lidangzzz/status/2085535251632394586（Paxon 分享 2026-08-08）
> 关联：用户主力项目 qintopia-agent-os / qintopia-agent-studio（多 Agent 框架，合作者 detroxryo）
> 项目：https://github.com/lidangzzz/goal-driven

## 原理（一句话）

**master agent 不断监督 subagent 工作，直到 subagent 完成工作且 master 亲自认证 meet the criteria；否则无限循环，逼迫 subagent 持续改进。**

- 纯粹目标驱动（goal-driven）：设好 goal + criteria（判据，如「生成 1000 个复杂 test case」）
- 不达标 → 收集一切错误信息 → 改进 → 再试 → 直到彻底实现

## 设计意图

- 允许 **>100 小时、极高 token 消耗** 去解决极难问题：
  - 编译器 / interpreter / transpiler 设计
  - 复杂数学问题、复杂系统问题、电子仿真
- 适合「可验证的复杂任务」——criteria 必须能客观判断成功/失败

## 已证明的三个成果（作者自述）

1. 全自动设计 **sqlite 的 Rust 实现版本**（sql parser 稳定）
2. 全自动设计 **C++ 实现的 TypeScript Compiler**（「去年只有微软几个人实现」）
3. 全自动实现 **Lean4 的 TypeScript 版本编译器**（「微软发明 + 整个数学学术界维护」）

## 评论区关键信息

- **Codex CLI v0.128.0（2026-04-30）正式引入 `/goal` 目标模式**——大厂也在做同样的事
- 「搭配一个 grillme 的 skill，把 goal 聊清楚，再让总 agent 挥鞭 sub-agent 去做，否则烧光 token 做出来的东西还是一坨」——**目标定义质量决定产出质量**
- 「相当于找了 3 个员工」

## 对 qintopia-agent-os 的对照分析

| 维度 | goal-driven | qintopia（用户项目） |
|---|---|---|
| 核心 | master 监督 + criteria 认证循环 | 多 Agent 框架（路由/调度/结算方向） |
| 终止条件 | criteria 客观判据（test case 数等） | 待对照 |
| 适用 | 可验证的极难问题（编译器/证明器） | Agent × Payments 基础设施 |
| 成本 | 100h + 高 token（无预算上限） | 需考虑成本控制（用户偏好） |

**可借鉴点**：
1. **criteria 认证机制**：master「亲自认证」而非 subagent 自报——对应我们 AGENTS.md 里「child summaries are self-reports」的验证铁律（delegate_task 的 summary 必须验证）
2. **无限循环 + 错误信息收集**：失败不放弃，把错误喂回改进——与「systematic-debugging」技能同构
3. **目标定义先行**：评论「goal 聊清楚否则烧 token 做一坨」= 用户「人需判断力驾驭 AI」理念的工程化表达

**风险/局限**：
- 只适合「可验证」任务（测试能客观判成败）；不可验证的任务（如「写得好不好」）会死循环
- 成本无上限是特性也是陷阱——用户如果借鉴，需加预算/时长硬边界

## 待做

- [ ] 看 goal-driven 源码实现（master 循环怎么判定 criteria、怎么收集错误）
- [ ] 对照 qintopia-agent-os 的调度层设计，评估是否借鉴 criteria 认证机制
