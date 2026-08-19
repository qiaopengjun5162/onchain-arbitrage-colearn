---
title: Ponytail 规则分发机制
date: 2026-08-19
type: 开源项目拆解
status: 已验证
tags: [agent-framework, ruleset, distribution, qintopia]
source: https://ponytail.dev/ + github.com/DietrichGebert/ponytail
related: [[学习过的开源套利项目]], [[Zacholme7 资源归档]]
---

# Ponytail 规则分发机制

> 结论先行：ponytail（AI 编码 agent「懒人规则集」，105.6k stars / 2 个月，MIT，v4.9.0）真正值得研究的**不是规则本身，而是「一套规则分发到 20+ 个 agent 宿主」的三级架构**——这是 2026 年 AI agent 生态的通用分发范式，对多 Agent 框架有直接借鉴价值。

## 一句话

ponytail 让 agent 写代码前走 7 级「懒惰阶梯」（YAGNI → 代码库复用 → 标准库 → 平台原生 → 已装依赖 → 一行 → 最小代码），但它同时做了一件更聪明的事：**把这一套行为打包成分发架构，让 20+ 个 agent 宿主都能吃到**。

## 核心架构：单一规则源 + 薄适配器 + 三级分发

```
skills/ 6×SKILL.md（完整版规则） + AGENTS.md（32 行 compact 版） + docs/platform-native.md（知识配套）
        │
        ▼ 指令构建器（运行时按模式过滤，动态生成注入文本）
hooks/ponytail-instructions.js（Claude/pi 版） + __init__.py build_injected_context()（Hermes 版）
        │
        ▼ 宿主适配器（薄壳）
Plugin-tier（Claude Code/Codex/Grok/OpenCode/pi/Hermes/Qoder/Copilot CLI）
Skill-tier（Swival/OpenClaw）
Instruction-tier（Cursor/Windsurf/Cline/Antigravity/Zed/Jules/Amp/Junie/CodeWhale/Kiro）
```

设计原则：**核心行为只写一份，宿主适配器全部「指向既有文件」**，按宿主能力降级分发（有钩子用钩子、有技能装技能、只有指令文件就吃 AGENTS.md），不做内容复制。多数 plugin.json 薄到只有一个 `{"name": "ponytail"}`。

**AGENTS.md 是分发矩阵的锚点**：Jules/Amp/Zed/Junie/CodeWhale/Antigravity/Copilot 等 10+ 宿主原生读取它——这是 2026 年 agent 生态的事实标准载体，新宿主零配置接入。

## Hermes 适配拆解（218 行 Python，插件 API 完整范例）

- plugin.yaml 声明：`pre_llm_call` + `pre_gateway_dispatch` 钩子、6 命令、6 技能
- **pre_llm_call**：每轮 LLM 调用前注入规则文本——按当前模式（lite/full/ultra）正则过滤 SKILL.md 的强度表行 + 示例行，一份源服务 4 种模式
- **pre_gateway_dispatch**：拦截 `/ponytail-review` 等斜杠命令 → 权限检查 → 重写成普通 agent prompt
- **register_skill**：6 个 SKILL.md 注册为 `ponytail:<skill>` 命名空间技能
- 配置链：env > ~/.config/ponytail/config.json > 默认 full；会话内模式存内存不落盘
- 降级兜底：SKILL.md 读失败 → 250 字核心规则 fallback（fail-open）

## 配套机制

- **适配器测试矩阵**：16 个测试文件，**每个宿主一个**（含 Hermes），防适配器漂移
- **规则同步检查脚本**：AGENTS.md compact 版 vs skills/ 完整版自动对齐校验
- **命令层**：commands/*.toml ×6 → OpenCode/Gemini/Codex 各自格式
- **MCP 通道**：独立 MCP server，第三条注入通道
- **platform-native.md**：HTML/CSS/JS/Swift/Node/Python/DB 七层「你以为要装库、平台其实自带」对照表（lodash.groupby → Object.groupBy、uuid → crypto.randomUUID）——**规则 + 知识捆绑分发**，知识让规则可执行

## 对多 Agent 框架的借鉴清单（8 条）

1. 核心行为单一源 + 薄适配器（不做内容复制）
2. 能力分级分发：plugin → skill → instruction 按宿主降级
3. AGENTS.md 锚点策略：新宿主接入成本 ≈ 0
4. 指令构建器模式：规则源带模式标注，运行时过滤动态生成
5. 适配器测试矩阵：每宿主一测试
6. 生成物同步脚本：规则改动后自动重跑生成物
7. 模式命令设计：强度可调（lite/full/ultra/off）而非 on/off 二值
8. Hermes 钩子即插即用：pre_llm_call + pre_gateway_dispatch + register_skill 组合 = 行为注入完整模板

## 泼冷水

- benchmark 是自报（12 任务中位数，promptfoo 自测，非 peer-reviewed）；YouTube「94% less code」是流量话术
- 规则注入是提示词不是约束：小模型/复杂代码库会误砍边界处理
- 适配器矩阵是持续税：每新宿主 = 适配器 + 测试 + 同步脚本
- instruction-tier 宿主拿到的是静态文本，无模式切换无命令——宣传口径需打折
- 交易/资金代码不建议开 ultra：删代码的收益远小于正确性的成本

## 方法论贡献

「行为单一源 + 能力分级分发 + 事实标准载体锚点」是 agent 行为分发的标准答案，可复用于任何想跨宿主的 agent 产品（qintopia-agent-os 架构评审 checklist）。

## 下一步

- qintopia-agent-os 对照 8 条清单做架构评审
- 试用 /ponytail-review 于求职项目 diff，评估实际减负
