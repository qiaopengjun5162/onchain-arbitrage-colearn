---
用途: 改稿时选择/串联「去 AI 味」写作 skill 的桥接文档（推文思路：不安装任何 skill，靠链接+选择逻辑让 AI 自己执行）
触发: 用户说"改稿 / 去AI味 / 写得像人 / 发公众号前润色"，或任何长文发布前的文字打磨
来源: https://x.com/spicycandy00/status/2086732942806847701 （2026-08-10 核验）
---

# 写作 Skill 桥接文档

## 原则

- **不安装任何 skill**：AI 读本文档后按需拉取对应仓库的 SKILL.md 作为规则注入即可。
- 三个不是替代关系，是三个方向；组合调用，人类主编定稿（AI 写作时代，你我都是主编）。
- 本机已有 hermes `humanizer` skill（英文向）可作第四对比源。

## Skill 清单（2026-08-10 核验）

| skill | 仓库 | 定位 | 强项 | 弱点 |
|---|---|---|---|---|
| human-writing | [KKKKhazix/human-writing](https://github.com/KKKKhazix/human-writing)（2.2K★） | 中文创作+改稿一体 | 长文/深度稿；材料第一；去机构腔/演说腔/营销腔/模型腔 | 偏创作，纯清理弱于 humanizer-zh |
| humanizer-zh | [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh)（15K★） | 编辑型去 AI 味 | 5 条核心规则 + 注入灵魂 | 只做清理，不管长文结构 |
| ljg-plain | [lijigang/ljg-skills](https://github.com/lijigang/ljg-skills)（6.8K★，skills/ljg-plain） | 概念解释型 | 写特定主题（概念/科普）成文质量有惊喜 | 非专做去 AI 味，会漏删 AI 句式 |

> ⚠️ 推文原链接把 humanizer-zh 错贴成 `op7418/guizang-ppt-skill`（PPT 仓库），上表已修正。

## 硬规则（从仓库 SKILL.md 原文提炼，AI 执行时必须遵守）

### human-writing（创作/改稿）
- 默认文风：见过事、查过材料、愿意把来龙去脉讲清楚的人在说话；保留中文互联网长帖的活人感与自然韵律。
- **成稿正文严禁**：冒号、破折号、「不是……而是……」及同类翻案句。
- **清除黑话**：商业黑话 + 模型惯用黑话。
- **材料第一**：非虚构长文先检查材料——计划 1200 字需先列出 ≥5 件具体材料（注明来自用户哪句话或哪份可靠来源），材料不足就研究、追问或缩短，**绝不用重复解释灌字数**。

### humanizer-zh（编辑/清理）
基于维基「AI 写作特征」指南（翻译自 blader/humanizer，参考 stop-slop），5 条核心规则：
1. 删填充短语：去除开场白和强调性拐杖词
2. 打破公式结构：避免二元对比、戏剧性分段、修辞性设置
3. 变化节奏：混合句子长度，两项优于三项，段落结尾多样化
4. 信任读者：直接陈述事实，跳过软化、辩解和手把手引导
5. 删金句：听起来像可引用金句的，重写它

+ **注入灵魂**：有观点（对事实做出反应）、承认复杂性（真实的人有复杂感受）、适当使用第一人称、允许幽默与锋芒。

### ljg-plain（概念解释）
把复杂概念讲清楚的方向；写特定主题时有意外惊喜，但去 AI 味不彻底，需要 humanizer-zh 扫尾。

## 选择逻辑（AI 按此执行）

| 稿子类型 | 主 skill | 辅助/扫尾 |
|---|---|---|
| 深度长文 / 行业解读 / 公众号硬核文 | human-writing 主写或主改 | humanizer-zh 扫尾清理 |
| 情绪流 / 故事 / 口播 / 代入感文字 | humanizer-zh 主改（断句短、呼吸感强） | — |
| 概念科普 / 名词解释 | ljg-plain 起草 | human-writing 收风格 + humanizer-zh 清理 |
| 拿不准 / 重要稿 | 三版并出（推文法） | 人工对比、融合、重写 |

## 执行协议

1. 收到改稿请求 → 判断稿子类型 → 按上表选主 skill + 辅助 skill。
2. 拉取对应仓库 SKILL.md 全文（`https://raw.githubusercontent.com/<owner>/<repo>/main/...`）作为规则注入；human-writing 在 `human-writing/SKILL.md`，Humanizer-zh 在根 `SKILL.md`，ljg-plain 在 `skills/ljg-plain/` 下。
3. 输出：主 skill 版本 + **变化说明**（改了哪几类 AI 痕迹，对应上面哪条规则）。
4. 重要稿默认给多版本并排，交人工选择。
