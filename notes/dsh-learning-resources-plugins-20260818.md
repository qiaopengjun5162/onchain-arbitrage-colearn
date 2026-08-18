# DSH 学习资源合集 + 插件清单（2026-08-18）

> 来源三条 X 帖（2026-08-17）：
> 1. [姚金刚：12 篇 DeepSeek Harness 学习资料](https://x.com/yaojingang/status/2089293234606629322)（24.6K views）
> 2. [SuSu_酥酥：20 个 DSH 插件分类清单](https://x.com/NFT_Chen/status/2089288446095323164)（8.7K views）
> 3. [Su：《DeepSeek Harness 从入门到进阶｜一切皆可插件》](https://x.com/Sukiea1008/status/2089555012565471563)（dsh 自己写自己的测评长文）
> 关联：`notes/taoli-tools-arb-angles-dsh-verify-20260815.md`（本机 dsh 实操验证，三大宣称全部属实）。

## 一、姚金刚 12 篇资料清单（按学习顺序）

| # | 资料 | 链接 | 类型 |
|---|---|---|---|
| 1 | DSH 官方仓库（源码/README/架构/版本/社区） | github.com/deepseek-ai/deepseek-harness | 权威源 |
| 2 | 官方 Web UI 教程（安装/启动/模型配置/工作区） | deepseek-harness.github.io/deepseek-harness/guide/quickstart | 教程 |
| 3 | 第一个插件教程（apply/inject/配置/生命周期/patch） | deepseek-harness.github.io/deepseek-harness/develop/basic/ | 插件入门 |
| 4 | Cordis 论文：时空可组合编程范式（底层框架理论：effect/响应式依赖/动态组合/热替换） | github.com/cordiverse/paper | 论文 |
| 5 | 分层自我改进：任务专属可演化 Agent 运行框架（DSH-V4-Flash-Preview 实验） | arxiv.org/abs/2608.08466 | 论文 |
| 6 | 「二次元头像=技术大佬」DSH 拆解公众号文 | mp.weixin.qq.com/s/5L3FMDHsKpOJ… | 公众号 |
| 7 | Simon Willison：Coding Agent 工作机制（模型/系统提示词/工具调用/状态/执行循环） | simonwillison.net/guides/agentic-engineering-patterns/how-coding-agents-work/ | 机制 |
| 8 | Anthropic 长任务 Harness 设计（Planner/Generator/Evaluator/跨会话交接） | anthropic.com/engineering/harness-design-long-running-apps | 官方实践 |
| 9 | Harness Engineering 中文系统教程（JavaGuide 收录：六层检查框架/上下文管理/约束/观测/恢复） | github.com/Snailclimb/JavaGuide/blob/main/docs/ai/agent/harness-engineering.md | 教程 |
| 10 | 从 DeepSeek 招聘反推 Harness 研究员要求（Agent Loop/Memory/Tools/Eval/多 Agent/自我改进） | reelos.ai/articles/deepseek-agent-harness-researcher/ | 招聘分析 |
| 11 | Addy Osmani：Agent Harness Engineering 全景（工具/上下文/Hooks/沙箱/记忆/验证） | addyosmani.com/blog/agent-harness-engineering/ | 博客 |
| 12 | DSH 从入门到插件化实践（架构/Profile/Bundle/插件开发/工具设计/生命周期/排错） | doc.laoyao.cn/wtknpy | 教程 |

评论区补充：deepseekharness101.com（Max_mgqiang 整理的新手参考站，按「第一次完成任务」顺序重排安装/插件/排错）。

## 二、SuSu_酥酥 20 插件分类清单

**核心必备（建议先装前 5）**
1. dsh-market — 插件市场入口，搜装升级一站搞定
2. dsh-web-ui — Web 管理 + 任务看板 + 手机远程
3. dsh-better-sidebar — 侧边栏 IDE 工作台
4. dsh-handbook — 新手手册
5. dsh-find-plugin — AI 帮你找插件

**界面交互**
6. dsh-TUI — 全屏终端（Claude Code 既视感）
7. dsh-at-file — @文件提及
8. dsh-mobile-gate — 手机局域网远程
9. dsh-mic-input — 语音输入

**能力扩展**
10. modlens — 纯文本模型看图（⚠️ 需 Gemini key，见 memory）
11. dsh-browser — 真实 Chrome 操作 + 登录状态

**监控统计**
12. TokenTracker — Token 消耗成本
13. dsh-usage-stats — GitHub 热力图使用频率
14. dsh-context — 上下文文件可视化

**多 Agent**
15. dsh_workflow — 工作流调度
16. dsh-agent-teams — 多 Agent 团队协作
17. dsh-memory-vault — 跨会话长期记忆

**娱乐外观**
18. dsh-ads — 复古广告风界面
19. whale-girl/dsh-pet — 桌面宠物
20. dsh-theme-cyberpunk2077 — 赛博朋克皮肤

⚠️ 核验：清单为第三方整理，插件名未逐个 clone 验证；装前按惯例 `git clone --depth 1` + 查 LICENSE。

## 三、Su 长文要点（dsh 自己拆自己，原汤化原食）

**产品形态**：不是成品 App——本地后台服务 + 浏览器遥控器（`dsh web` → 127.0.0.1:3080）。模型走 DeepSeek API（不是本地模型），本地的是运行环境（文件读写/权限沙箱）。

**四模式选型**（模式≠模型）：
- 极简：只写代码、越省越稳
- 标准：日常干活工具全（默认）
- PTC：嫌一步步来回太慢用
- 创造：造/改 Agent 本身
- 关系：标准是地基，PTC/创造各加一样，极简砍到两把刀

**一切皆插件（Cordis 元框架）**：模型/工具/Skill/记忆/沙箱/审批/主循环全是插件行（cordis.yml 一行一能力）。可组装/可替换/可检查可回滚。连 DeepSeek 自己的模型也只是可换的一张插件。

**创造模式三步**：抄底（复制最接近的 preset）→ 改行（加减工具/人设）→ 挂载（放 preset 目录）。

**尖锐观察（诚实评测）**：
1. 创造模式「不懂自己」——问它自己机制，回答泛泛甚至想象（模型对 Harness 自身认知未优化=产品早期信号）
2. 空白工作区却知道你旧事——不是扫盘，是带着历史上下文跑；记忆边界不透明需透明化
3. 开发者友好=新手不友好（API Key + 工作区 + 命令行三道坎）
4. 服务不自启（重启/关终端就没）、API Key 花钱、网页 Agent 手感还在打磨

**作者判断**：价值不在「现在比谁强」，在于把「Agent 该长什么样」往前推了一步——不是成品 App，是能自己组装、长期跑在本地的 Agent 运行时；未来「造 Agent」= 把不同员工 Agent 当插件各干各活。

## 意义

- 12 篇资料 = DSH 学习线完整书单（官方 → Cordis 理论 → 机制 → 工程实践 → 生态插件），接 `dsh-deepseek-harness` skill 使用
- 20 插件清单 = 生态全景速查；核心必备 5 个 + 多 Agent 3 个与我们的方向（多 Agent 协作/记忆）直接相关
- Su 长文的「一切皆插件 + 创造模式」与我们 08-15 dsh 实操验证（profile=cordis.yml 组装、session 日志即架构）互证
- 「创造模式不懂自己」= 我们 08-15 踩的坑同源：主代理 turn/end 即退出、后台子代理被杀——产品早期、主循环插件化不成熟的证据
