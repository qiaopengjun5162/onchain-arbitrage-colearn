---
用途: 每日发布流水线总 SOP（共学打卡 → 公众号文章 → X thread → 归档验证）
触发: 用户说"把第X天的笔记/推文发公众号/X"、"继续发布"
---

# 每日发布流水线 SOP（2026-08-09 整合定稿）

> 子文档：`templates/wechat-publish-sop.md`（公众号细节）+ `templates/x-publish-sop.md`（X 细节）
> 技能：`moonpub-wechat-publish`（Hermes skill，含完整 ship 命令）
> 本文 = 总入口 + 跨平台编排 + 今日踩坑沉淀

## 流水线总览（每天约 10 分钟）

```
daily/<日期>.md 打卡
   │
   ├─① 公众号：改写文章 → social/wechat/<slug>.md
   │        → moonpub ship（cover+render+push+后台配置+手机预览）
   │        → 用户手机确认 → 微信后台人工发布 → mark-published
   │
   └─② X thread：改写 6 条 → social/x/<日期>-d{N}-thread.md
            → 先试 xurl 自动发（402 则手动）
            → 用户手动发 → 发起始链接给 Hermes → web_extract 验证 6 条
            → 归档发布记录
   │
   └─③ 知识库提交：git commit（文章全套 + daily 追加 + SOP 历史表）
   │
   └─④ Obsidian 同步：核心笔记写入 obsidian/ 暂存区 → 复制进 iCloud vault → 双链检查（2026-08-13 起）
```

## ⚠️ 开工前必查（2026-08-09 新增，防重复发布）

**ship 前先查 `.moonpub/status.jsonl` 该 slug 是否已 published**：

```bash
grep -c '"slug":"<slug>","status":"published"' .moonpub/status.jsonl
# >0 = 已发布 → 不要 ship！否则会推新草稿造成重复文章
# 已发布的文章若要换样式：先 delete-draft 旧草稿，别让草稿箱里躺着重复版本
```

2026-08-09 实测教训：D2 昨天已发布，今天为换浅色主题重 ship 推了新草稿（100011385）→ 用户指出"昨天已经发了"→ 立即 `moonpub delete-draft 100011385` 删除，状态改回 published。

## 公众号编排

1. **写文章** → `social/wechat/<slug>.md`
   - 素材：`notes/` + `daily/` 当天全部产出（**检查完整度**：Rust 双实现、广度点都别漏）
   - frontmatter：title / wechat_title / digest / author / wechat_author
   - 标题风格：`共学 D{天}：{有钩子的主题}`（例：`共学 D3：0.01 SOL 的第一笔真实 swap`）
   - **文末必带**「关于本次共学」介绍块（`templates/colearn-intro-block.md`，D8 起）——活动导流，文案数字发布前核对
2. **主题（正文配色）**：`moonpub.toml [wechat] theme` 控制
   - **当前定稿：`geek`（浅色 #f6f8fa GitHub 风）**——用户 8/9 反馈黑底长文累眼后统一
   - 可选浅色：`geek`(GitHub绿) / `blueprint`(浅蓝) / `paper`(米白宋体) / `notebook`(浅蓝白)
   - 封面风格 `--style geek-black`（终端风 BUILD NOTES）与正文主题独立，两者可混搭
3. **ship**（execute_code + subprocess，env 从 ~/.zshrc 读 WECHAT_APPID/SECRET）：
   ```python
   [moonpub, "--articles", ROOT, "ship", f"social/wechat/{slug}.md", "--style", "geek-black"]
   ```
4. **发布前预览**：Chrome headless 截图发给用户（render 后 html）
5. **发布后**：`moonpub mark-published` + daily 记录

## X thread 编排

- 草稿格式：`**1/6**` 标题行 + 100-150 字/条、一条一观点、末条带标签 `#链上套利 #Solana #Crypto`（按主题加）
- 先试自动：`xurl --app my-app post "<第1条>"`（env 带 HTTPS_PROXY=127.0.0.1:7890）——**当前仍 402 credits depleted，转手动**
- 手动流程：发第 1 条 → 回复式发 2-6 条 → 用户给起始链接 → web_extract 验证 6 条完整 → 归档
- 验证注意：X 会吞部分标点（→ ≈ 逗号显示成空格），内容完整即可

## 归档清单（发布完成后）

- [ ] `social/wechat/<slug>.media_id` 已更新
- [ ] `.moonpub/status.jsonl` 状态 = published
- [ ] `social/x/<日期>-d{N}-thread.md` 发布记录补全（起始链接 + 各条 ID）
- [ ] `templates/x-publish-sop.md` 历史 thread 表 +1 行
- [ ] `daily/<日期>.md` 追加发布记录
- [ ] Obsidian 同步：核心笔记 → `obsidian/` 暂存区 → 复制进 iCloud vault（见下节）
- [ ] git commit

## Obsidian 同步（2026-08-13 定稿，发布后必做）

**机制**：库内 `obsidian/` 目录 = 暂存区（git 管理、可回溯）→ 复制进 iCloud vault = 长期库（Obsidian 打开即见）。两个目录结构必须一致。

- vault 路径：`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/ObsidianVault/链上套利共学/`
- 分区：`00 MOC` / `01 角色与配置` / `02 市场地图` / `03 策略假设` / `04 工具与协议` / `05 Bot 代码` / `06 失败复盘` / `07 共学群友`

**步骤**：

1. **选核心笔记**（每天 3-10 篇，不是全部）：有长期价值的方法论/已验证结论/机制认知；跳过纯过程记录
2. **写暂存区**：按模板（frontmatter：title/date/type/status/tags/source/related），中文，删执行细节（脚本路径/API 绕过/敏感数字）
3. **双链检查**：`[[链接]]` 必须能解析到 vault 现有文件名（Obsidian 按文件名解析）；断链=链接指向不存在的笔记，要么补笔记要么改链接
4. **复制进 vault**：`cp obsidian/<分区>/<笔记>.md "<vault>/<分区>/"`
5. **更新 MOC**（`00 MOC 链上套利共学.md`）：新笔记挂到对应分区节，一句话摘要
6. **验证**：`comm -23 <(find obsidian -name "*.md" | grep -v -E "^(README|moc-template|note-template|solana/)" | sort) <(find vault -name "*.md" | sed "s|vault/||" | sort)` 输出为空 = 全同步
7. **git commit**（只提交 obsidian/ 暂存区变更；vault 在 iCloud 不进 git）

**已知坑**：
- iCloud 同步有几秒~几分钟延迟，Obsidian 里稍等刷新
- 「实盘达成率」「链上 Perp」等是 MOC 占位符（研究/模拟阶段设计意图），断链检查时豁免
- 2026-08-13 发现的历史 bug：08-09 的 6 篇只写了暂存区没复制进 vault → 以后必须走完 4-6 步

## 历史 thread（截至 08-09）

| 天数 | 起始链接 | 条数 | 日期 |
|---|---|---|---|
| D1 | x.com/qiaopengjun/status/2085661488010912055 | 6 | 08-07 |
| D2 | x.com/qiaopengjun/status/2085913863829229589 | 6 | 08-08 |
| D3 | x.com/qiaopengjun/status/2086403022721290416 | 6 | 08-09 |

## 历史 media_id（截至 08-09）

| 文章 | media_id | 状态 |
|---|---|---|
| D1 交易模型 | 100011335 | 已发布 08-07 |
| D2 套利分层 | — | 已发布 08-08（草稿 100011385 已删） |
| D3 swap | 100011392 | 已发布 08-09 |

## 踩坑速查（2026-08-09 新增）

| 坑 | 现象 | 解法 |
|---|---|---|
| 二进制过期 | `--style geek-black` 静默 fallback 成 literary 封面 | ship 前 `cargo build --release`；OCR 封面确认 tag 是 BUILD NOTES |
| 黑底累眼 | 正文全黑背景 | moonpub.toml theme = "geek"（浅色）；或 frontmatter 级 `theme:` 覆盖单篇 |
| 重复推草稿 | 已发布文章再 ship 产生新草稿 | 查 status.jsonl；误推用 `delete-draft <media_id>` 删除 |
| 封面风格没生效 | style 参数对但输出不对 | 检查 cover.html 的 data-cover-style 属性 + OCR 封面 PNG |
| lifecycle guard | moonpub 带 --articles 被拦 | 必须 execute_code + subprocess.run |
| X 402 | credits depleted | 手动发布，xurl 只做草稿/验证 |
