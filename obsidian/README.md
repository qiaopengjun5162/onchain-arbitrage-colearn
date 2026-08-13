# Obsidian 对接方案

## 定位

当前项目是共学工作台，Obsidian 是长期知识库。

工作台里可以保留原始打卡、临时草稿、脚本想法和每日推进；Obsidian 里只沉淀经过整理的知识单元，方便长期检索、双链和复用。

## 推荐目录

如果接入现有 Obsidian vault，可以创建：

```text
链上套利共学/
  00 MOC 链上套利共学.md
  01 每日打卡/
  02 市场地图/
  03 策略假设/
  04 工具与协议/
  05 失败复盘/
  06 可发布草稿/
  99 资料来源/
```

## 笔记类型

- MOC：总入口，链接所有核心页。
- 每日打卡：从 `daily/` 精简同步。
- 市场地图：DEX、perp、RWA/币股、预测市场、MEV。
- 策略假设：从 `templates/strategy-hypothesis.md` 整理。
- 工具与协议：LI.FI、The Graph、Hermes、taoli.tools、1inch、DeFi PoC Lab。
- 失败复盘：模拟盘和实盘差距、价格不收敛、滑点、失败交易。
- 可发布草稿：从 `social/` 精修。

## Frontmatter

推荐每篇沉淀笔记保留：

```yaml
---
title:
date:
type: daily | market | strategy | tool | source | review | draft
status: idea | researching | verified | rejected | published
tags:
  - onchain-arbitrage
  - colearn
source:
related:
---
```

## 双链规则

优先链接到这些概念页：

- [[链上套利]]
- [[套利成本模型]]
- [[我的 Edge]]
- [[Paper Trading]]
- [[实盘达成率]]
- [[链上 Perp]]
- [[RWA 币股]]
- [[预测市场 LP]]
- [[MEV]]
- [[Hermes Agent]]
- [[LI.FI]]
- [[The Graph]]

## 同步原则

- 原始材料先放项目目录，整理后再进 Obsidian。
- 每日打卡只同步“可复用的发现”，不是机械复制全文。
- 一个策略只有写清假设、成本、风险和放弃条件，才进入策略目录。
- 公开发布前，从 Obsidian 或 `social/` 生成干净草稿。

## 实际同步机制（2026-08-13 起，见 templates/daily-publish-pipeline.md）

- **本目录 `obsidian/` = 暂存区**（git 管理、可回溯），**iCloud vault = 长期库**（Obsidian 打开即见）。
- vault 路径：`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/ObsidianVault/链上套利共学/`
- 流程：写暂存区 → 双链检查 → 复制进 vault → 更新 MOC → comm 验证 → git commit。
- ⚠️ 历史教训（08-13）：只写暂存区不复制进 vault = 同步失败。两目录结构必须一致。
