# Notion Solana 资料页

来源：

- https://attractive-spade-1e3.notion.site/Solana-fca856aad4e5441f80f28cc4e015ca98

## 当前状态

已记录为 Solana 研究资料。

页面通过 Notion 动态渲染，命令行抓取只返回 Notion 壳，没有直接拿到正文。后续需要人工打开阅读，或从 Notion 导出 Markdown 后再整理进知识库。

## 整理方式

拿到正文后，按下面结构拆分：

- 基础概念
- 开发工具
- DEX / 路由
- MEV / Jito
- 数据索引 / RPC
- 项目案例
- 可转成脚本或 watcher 的任务
- 适合发布的学习笔记

## Hermes 处理提示

把导出的 Markdown 或复制的正文交给：

- `hermes/prompts/source-to-note.md`
- `hermes/prompts/obsidian-sync.md`
- `hermes/prompts/solana-research.md`

要求 Hermes 不要机械摘要，而是提取：

- 资料链接
- 可验证假设
- 可执行任务
- 需要官方文档核验的判断
- 可以沉淀到 Obsidian 的概念页
