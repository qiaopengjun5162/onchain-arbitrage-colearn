# AI Agent 工作流工具观察：Obsidian 创作中枢 Ailu + 微信 CLI 情报库

> 来源：X @alin_zone 推荐逸尘 Ailu（[推文](https://x.com/alin_zone/status/2090331225856872569) / [原文](https://x.com/gengdaJ/status/2088831092379775198)）+ Rion Wu 微信 CLI 开源预告（[推文](https://x.com/rionaifantasy/status/2090491734153429317)）
> 日期：2026-08-21 | 类型：工具/工作流观察 | 状态：verified（Ailu 已开源可核验；微信 CLI 未开源待验）

## 假设

AI Agent 工作流工具正从「单点插件」走向「创作/情报全链路中枢」；值得拆解其架构，对照 Hermes 自身工作流找可借鉴点。同时警惕：带 KOL referral 链接的推广（AnySearch）需与功能宣传分开评估。

## 结论

1. **Ailu（逸尘，已开源 AGPL）**：嵌在 Obsidian 里的 Agent 工作台，写作→记忆→预览→发布全链路。仓库 `github.com/mcncarl/ailu` + `github.com/mcncarl/wechat-relay`（公众号中转）+ `github.com/mcncarl/agent-memory-vault`（共生记忆系统）。
2. **微信 CLI 情报库（Rion Wu，预告开源）**：微信聊天记录 → 行动总览/HTML 日报/重点联系人回复建议/跨群商单索引。
3. **AnySearch 是带 referral 的推广**（`utm_campaign=kol_08a`），功能未核验，仅记录方法论。

## Ailu 架构拆解（值得借鉴的点）

### 1. Agent 工作台
- 集成 Codex + Claude Code，**接入 CC Switch 统一配置**（终端和 Ailu 一套配置，切换模型零成本）
- 参考 Wesight/OpenCode：多对话并行 + 归档（ADHD 多线程创作场景）
- 精选 20+ 创作相关 Skill（不无脑挪用上百个）
- 选中文字直接在对话内提问 = 交互式学习（比全局窗口复制粘贴强）

### 2. 记忆系统（agent-memory-vault）
- Codex/CC/Ailu 共用一套记忆库，**只读创作相关记忆**
- 关键设计：**手动「沉淀到记忆」按钮**，不自动写入对话记忆 → 降低无效记忆输入
- 与 Hermes 记忆哲学一致：高信号记忆 > 全量记录

### 3. 发布链路（最大踩坑价值）
- **公众号上传**：微信 API 要求 accesstoken 来源 IP 在白名单 → 动态 IP 不行 → 必须固定出口 IP 服务器。方案：`Ailu → 子域名 → Cloudflare Tunnel → 腾讯云东京服务器（固定IP出口）→ 微信官方API`。服务器放境外避开 ICP 备案（境内服务器长期稳定需备案）
- 中转安全：域名 + HTTPS + Authorization Token（中转 Token 独立于公众号凭据）
- **X 长文上传**：5:2 封面图比例、25 张正文图上限（硬性规则，纯经验费）；Cookie 从 Chrome `~/Library/Application Support/Google/Chrome/Default/Cookies` 取
- 飞书：CLI 扫码授权，最小权限原则（不多要权限）

## 微信 CLI 情报库（Rion Wu）

- 功能：24h 聊天记录总结+行动总览、重要群聊信息、HTML 交互日报、重点联系人日报+回复建议、跨群链接索引（商单识别）、时间范围可调
- 方法论增量：**Project Research Skill** = 定义问题 → 搜索证据（AnySearch）→ 比较外部公开方案 → 形成执行计划。反例：直接改 Prompt 是修错地方，重做入口才是正解（「日报两万字 → 拆成今日总览/主题搜索/联系人/回复建议/商单雷达五入口」）
- ⚠️ 未开源（预告），AnySearch 功能未核验，referral 推广成分待过滤

## 与共学线关联

- **AI 补技术短板本身就是 edge**（与 Bruce 导师层验证工具选型互证）：Ailu 用 Agent 完成公众号上传自动化，正是「执行摩擦再降一档」的例证
- 公众号发布链路：我们已有 moonpub CLI 推草稿箱方案；Ailu 的差异化 = 本地预览排版（八套模板）+ Agent 生成封面直接插入。wechat-relay 的 Cloudflare Tunnel + 固定 IP 架构对 Agent×Payments 的 webhook 回调有复用价值
- 记忆系统「手动沉淀」设计与 Hermes 记忆/技能体系同构
- 群聊情报自动化对共学 digest 工作流有参考（但微信 CLI 未开源，先观察）

## 风险 / 保留意见

- Ailu 是 **AGPL 协议**：参考架构可以，直接并入商业化项目（qintopia 等）有许可证风险
- 腾讯云东京服务器方案非零成本（服务器月租 + 域名）
- AnySearch 为 KOL 推广（referral 链接），功能宣称未经独立核验，仅方法论可取

## 下一步

- [ ] 如需 X 长文发布能力：参考 5:2 封面 / 25 图限制踩坑清单，评估 moonpub 之外是否要补 X 发布（现已有 xurl skill）
- [ ] 微信 CLI 开源后核验：是否真开源、权限边界、数据本地化
