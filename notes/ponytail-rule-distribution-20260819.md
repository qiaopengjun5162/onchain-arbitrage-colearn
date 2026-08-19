# Ponytail 规则分发机制拆解（AI Agent 框架参考）

> 来源：https://ponytail.dev/ + https://github.com/DietrichGebert/ponytail（2026-08-19 用户提供）
> 归档日期：2026-08-19（Hermes 记录）
> 数据核验：GitHub API 实测 stars=105,599 / forks=5,835 / MIT / 创建 2026-06-12 / v4.9.0；克隆仓库 159 文件全量拆解

## 一句话定位

ponytail 是一套让 AI 编码 agent「写最少的代码」的规则集，但**它真正值得研究的不是规则本身，而是「一套规则分发到 20+ 个 agent 宿主」的分发架构**——这是 2026 年 AI agent 生态的通用分发范式，对 qintopia-agent-os 多 Agent 框架有直接借鉴价值。

## 核心架构：单一规则源 + 薄适配器 + 三级分发

```
核心行为（单一来源，只写一份）
├── skills/ 6×SKILL.md        ← 完整版规则（ponytail 主规则 120 行）
├── AGENTS.md                 ← compact 版（32 行，instruction-tier 通用载体）
└── docs/platform-native.md   ← 知识配套（HTML/CSS/JS/Swift/Node/Python/DB 七层「平台原生替代」查表）
        │
        ▼ 指令构建器（运行时按模式过滤，动态生成注入文本）
hooks/ponytail-instructions.js（Claude/pi 共用 JS 版）
__init__.py build_injected_context()（Hermes 用 Python 版，218 行）
        │
        ▼ 宿主适配器（全是 <10 行的薄壳）
Plugin-tier（12 个）        Skill-tier（2 个）      Instruction-tier（10+ 个）
Claude Code / Codex /       Swival / OpenClaw       Cursor / Windsurf / Cline /
Grok / OpenCode / pi /                              Antigravity / Zed / Jules /
Hermes / Qoder / Copilot CLI                        Amp / Junie / CodeWhale / Kiro / Copilot(回退)
```

### 三级分发层级（分发矩阵的核心）

| 层级 | 能力 | 载体 | 宿主 |
|---|---|---|---|
| **Plugin** | 会话激活 + 每轮注入 + 模式持久化 + 斜杠命令 + subagent 注入 | plugin.json + hooks + commands/ | Claude Code、Codex、Grok、OpenCode、pi、Hermes、Qoder、Copilot CLI |
| **Skill** | 技能安装（6 个 SKILL.md 直装） | skills/ | Swival、OpenClaw |
| **Instruction** | 静态规则文件，无命令无动态 | .mdc / .md / AGENTS.md | Cursor、Windsurf、Cline、Zed、Jules、Amp、Junie、CodeWhale、Antigravity |

设计原则：**核心行为只写一份，宿主适配器全部指向既有文件**。宿主支持钩子就用钩子，支持技能就装技能，只有指令文件就用 AGENTS.md——按宿主能力降级，不按宿主复制规则。适配器薄到多数 plugin.json 只有一个 `{"name": "ponytail"}` 字段。

### AGENTS.md = 2026 年 agent 生态的事实标准载体

分发矩阵的锚点不是任何一家厂商的插件格式，而是 **AGENTS.md**：Jules/Amp/Zed/Junie/CodeWhale/Antigravity/Copilot 等 10+ 个宿主原生读取它（仓库根目录或全局 `~/.config/...`）。新 agent 发布时零配置接入的分发通道。instruction-tier 的「规则文本」全部以 AGENTS.md 的 32 行 compact 版为准，用 `scripts/check-rule-copies.js` 自动检查与 skills/ 完整版对齐。

## Hermes 适配拆解（plugin.yaml + __init__.py，与 qintopia 最相关）

Hermes 属于 plugin-tier，是六个完整适配里机制最清晰的，218 行 Python 一个文件全搞定：

1. **声明式清单** `plugin.yaml`：`provides_hooks: [pre_llm_call, pre_gateway_dispatch]` + `provides_commands ×6` + `provides_skills ×6`
2. **pre_llm_call 钩子**：每轮 LLM 调用前注入 `build_injected_context()` —— 读 skills/ponytail/SKILL.md，按当前模式（lite/full/ultra）用正则过滤 intensity 表行 + 示例行，只注入对应模式的规则文本（同一份 SKILL.md 服务 4 种模式，不维护 4 份）
3. **pre_gateway_dispatch 钩子**：`rewrite_gateway_command()` —— 拦截 `/ponytail-review` 等斜杠命令，先做权限检查（gateway._check_slash_access），再重写成普通 agent prompt（「Load and follow the Hermes plugin skill ponytail:review...」）
4. **register_command**：`/ponytail [lite|full|ultra|off]` 模式切换（内存 _current_mode）+ 5 个技能命令（ctx.inject_message 排队注入）
5. **register_skill**：6 个 SKILL.md 注册为 `ponytail:<skill>` 命名空间技能
6. **配置链**：env `PONYTAIL_DEFAULT_MODE` > `~/.config/ponytail/config.json` > 默认 full；会话内模式只存内存不落盘（轻量设计）
7. **降级兜底**：SKILL.md 读取失败 → `_fallback_instructions()` 一段 250 字核心规则文本（fail-open，不 fail-closed）

## 配套机制

- **hooks 家族**：claude-codex-hooks.json（两宿主共用一份映射）+ copilot-hooks.json + qoder-hooks.json；ponytail-activate（会话激活）/ mode-tracker（模式追踪）/ runtime / subagent（子代理注入）/ statusline（终端状态栏）
- **命令层**：commands/*.toml ×6（ponytail/review/audit/debt/gain/help）→ OpenCode 转 .opencode/command/*.md、Gemini 自动发现、Codex 用 `@ponytail-review` 形式
- **MCP 通道**：ponytail-mcp/ 是独立 MCP server（instructions.js + index.js）——第三条注入通道，可被任意 MCP 客户端挂载
- **适配器测试矩阵**：tests/ 16 个测试文件，**每个宿主一个**（含 hermes-plugin.test.js），node --test 统一跑——适配器不漂移的保证
- **规则同步检查**：scripts/check-rule-copies.js（AGENTS.md vs skills 对齐）+ check-versions.js + build-openclaw-skills.js（生成物重跑）
- **基准体系**：benchmarks/（promptfoo config + agentic 测试 + 多日期 results/）——宣称的 54% less code / 22% fewer tokens / 20% cost / 27% faster 是 12 个 feature task 的 self-reported 中位数
- **platform-native.md 知识配套**：规则说「用平台原生」，知识库告诉它「平台原生是什么」——HTML 表单控件/CSS 能力/JS API/SwiftUI/Node/Python/DB 七层「你以为要装库、平台其实自带」对照表（如 lodash.groupby → Object.groupBy、uuid → crypto.randomUUID、点击库 → argparse）。**规则 + 知识捆绑分发**，知识让规则可执行

## 可偷的干货（对 qintopia-agent-os 的借鉴清单）

1. **核心行为单一源 + 薄适配器**：行为只在核心目录写一份，宿主适配器全是「指向既有文件」的引用，不做内容复制
2. **能力分级分发**：同一条规则按宿主能力降级（plugin → skill → instruction），不追求每个宿主能力对齐
3. **AGENTS.md 锚点策略**：分发矩阵围绕事实标准文件展开，新宿主接入成本 ≈ 0
4. **指令构建器模式**：规则源带模式标注（frontmatter + 表格行 label），运行时正则过滤动态生成注入文本，一份源服务 N 种模式
5. **适配器测试矩阵**：每个宿主一个测试文件，防适配器漂移
6. **生成物同步脚本**：规则改动后自动重跑生成物（.openclaw/skills 从 skills/ 构建）+ 一致性检查
7. **模式命令设计**：`/ponytail [lite|full|ultra|off]` 强度可调而非 on/off 二值，降低规则对正常开发的侵入性
8. **Hermes 钩子即插即用**：pre_llm_call + pre_gateway_dispatch + register_skill/command 的组合就是「行为注入 + 命令重写 + 技能命名空间」的完整模板

## 泼冷水（诚实评估）

- **105k stars 营销成分大**：官方 benchmark 是自报 + promptfoo 自测（non-peer-reviewed）；YouTube 标题「94% less code」是流量话术；官网数字（54%）可信度中等偏上（有测试矩阵支撑），但 sample=12 个任务偏小
- **规则注入是提示词不是约束**：小模型/复杂代码库会误砍——上下文没读全就「懒」，把必要的边界处理删掉。官方在 SKILL.md 里用大量篇幅防这个（「ladder runs after you understand the problem, not instead of it」），但模型不保证遵守
- **适配器矩阵是持续税**：20+ 宿主的代价是每个新 agent 发布都要加适配器 + 测试 + 同步脚本（已有 16 测试 + 3 脚本维护）。个人/小团队复刻前要评估投入
- **instruction-tier 名不副实**：官网 install 列表把「完整支持」和「只读静态文本」混在一起宣传——Cursor/Windsurf 等拿到的是不会随模式切换的静态规则
- **对交易/资金代码的实际风险**：删代码的收益远小于正确性的成本。ponytail 的 safety 条款（trust boundary 验证/资金路径不简化）写得清楚，但模型执行时可能不遵守——资金相关代码不建议开 ultra

## 对我们的意义

- **qintopia-agent-os 直接参考**：上面 8 条借鉴清单就是现成的架构评审 checklist——特别是「AGENTS.md 锚点 + 能力分级 + 指令构建器」三件套，是多 Agent 框架行为分发的标准答案
- **Hermes 插件机制实证**：ponytail 的 Hermes 适配就是我们平台插件 API（pre_llm_call/pre_gateway_dispatch/register_skill/register_command）的完整使用范例，可当插件开发教程
- **可实操**：装 ponytail lite 到 Claude Code/Hermes，当「代码评审第二双眼睛」（/ponytail-review 查 diff 过度工程）——对求职项目代码质量有实际帮助

## 待办

- [ ] qintopia-agent-os 架构评审：对照 8 条借鉴清单逐条看现有框架差距
- [ ] 试用 /ponytail-review 于求职项目某个 PR，评估实际减负效果
- [ ] 跟进 ponytail 后续版本（v4.9.0，迭代很快），重点看适配器矩阵怎么处理新宿主

## 关联

- `notes/week2-summary-20260818.md`（agent 工具链研究线）
- obsidian: `05 Bot 代码与开源项目/Ponytail 规则分发机制.md`
