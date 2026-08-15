---
title: DeepSeek Harness (dsh)
date: 2026-08-15
type: note
status: active
tags:
  - tool
  - agent-framework
  - automation
source:
  - "https://github.com/deepseek-ai/deepseek-harness"
related:
  - "[[Hermes Agent]]"
---

# DeepSeek Harness (dsh)

> DeepSeek 开源 agent harness（2026-08-13 发布，dev preview）。口号 **"Everything is a Plugin"**，底层 Cordis 微内核，TypeScript，MIT。

## 为什么值得记

- **架构**：连 Agent Loop 本身都是插件——Codex/Claude Code 是「整机」（核心固定只能加外围），dsh 是「面包板」（核心可整体替换）。接口定义/服务实现/消费者三层分离，换实现层不动模型工具。
- **会话日志即架构**：模型可见即被记录，JSONL 落盘可跨进程恢复、可回放每一步工具调用。
- **多 Agent 编排是一等公民**：subagent（spawn/fork/ACP）、workflow（模型写 JS 扇出子代理）、goal（跨轮长跑任务）。

## 本机实操验证（2026-08-15）

- headless 一行式任务跑通：`dsh --profile headless "任务"`
- 让 dsh 并行分析 2 个脚本 → 真实挑出 bug（hl_funding_monitor 无重试/无校验/无锁；amm_v2_verify 无边界校验）→ 已修复
- ⚠️ **坑**：headless 下「后台 subagent」会被主代理 turn/end 杀掉，必须用「阻塞式 subagent 等全部返回」

## 在套利研究中的位置

- 批量「AI 代码审查 / 并行调研」工具：脚本质量检查、多源信息并行收集
- 与 [[Hermes Agent]] 互补：Hermes 管共学工作流，dsh 可做一次性深度任务
- 呼应「AI 加速器不是方向盘」：工具只管执行，策略角度靠人发现

## 使用建议

- 脚本化任务用 headless + 阻塞式 subagent
- 凭证只存 `~/.dsh/.credentials.yaml`（0600），不进聊天/配置
- dev preview，API 会破坏性变更，别建长期依赖
