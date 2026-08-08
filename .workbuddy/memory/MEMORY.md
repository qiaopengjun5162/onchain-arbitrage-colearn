# 链上套利共学 - 长期项目笔记

## Obsidian 知识库同步
- 真实 vault：`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/ObsidianVault/链上套利共学/`
- 项目内镜像：`obsidian/`（与 vault 内容一致，由脚本同步）
- 同步脚本：`scripts/sync_obsidian_batch.py`（manifest 驱动，增量同步 `notes/` → vault + 镜像；自动补 frontmatter + 把内部 `notes/<slug>.md` 引用重写为 vault 双链 `[[中文名]]`）。新增笔记只需在 MANIFEST 加一行再跑脚本。
- 双链规范：vault 内笔记用 `[[中文标题]]` 互链；`[[实盘达成率]]` 为故意占位（研究/模拟阶段未实盘），保持断链符合设计。
- 断链自检：扫 vault 所有 `[[x]]`，核对是否存在同名 `.md`，唯一允许的断链是 `实盘达成率`。

## 角色分工（AGENTS.md）
- 桌面端（我）：想清楚 / 整理 / 沉淀 / 同步 Obsidian。
- Telegram Hermes：执行 / 即时资料查询 / 打卡 / 任务拆解。
- 两边都可能改同批文件，写前先看现状、追加不覆盖。

## 项目铁律
- 研究 / 模拟 / 实盘严格区分；模拟盘收益不可写成真实收益。
- 私钥 / 助记词 / API Secret / 交易所 Token / 钱包截图不入库。
- 发布、交易、分享操作细节前必须由人复核。

## 主线状态
- 主线 D3 devnet swap（Solana + Jupiter 跑一次真实 swap）始终未推，待用户决定。
- 概念页 `[[我的 Edge]]` / `[[套利成本模型]]` 仍为空骨架，待真实数据填充。
