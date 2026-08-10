---
用途: 公众号文章发布模板（每日共学打卡 → 公众号草稿流水线）
触发: 用户说"把第X天的笔记发到微信公众号"
---

# 公众号文章发布 SOP（2026-08-08 定稿）

> 技能：`moonpub-wechat-publish`（Hermes skill，含完整 ship 命令与 footer 说明）
> 工具：moonpub CLI（cookie 模式，已 login 免扫码）

## 固定结尾（footer，moonpub.toml [footer] 已配好，勿改）

- 公众号简介 + 免责声明 + 关注语：寻月隐君
- 群二维码：`social/wechat/qrcode-xunyuege-20260808.jpg`（**8/15 前有效，过期换新图+改路径**）
- 点赞引导图：`social/wechat/wechatmoonpost.jpg`（"点个赞/推荐"图）
- 两图 ship 时自动上传微信 CDN

## 步骤（约 3 分钟）

1. **写文章** → `social/wechat/<slug>.md`
   - 素材：`notes/<日期>-*.md` + `daily/<日期>.md` 改写
   - frontmatter 必须有：
     ```yaml
     ---
     title: 共学 D2：套利分层——价差、MEV 与执行成本
     wechat_title: 共学 D2：套利分层——价差、MEV 与执行成本
     digest: 120字以内摘要
     author: Paxon Qiao
     wechat_author: Paxon Qiao
     ---
     ```
   - 标题风格：`共学 D{天}：{主题}`
   - 结尾不写免责声明（footer rules 已含）
2. **ship 前查违规词**（约 30 秒，粗筛非终审）：
   - 零克查词 https://lingkechaci.com（免费；主推小红书/抖音/B站，公众号词库覆盖不全，当参考）
   - 只传「标题+摘要+改写段落」；**未发布研究草稿不要整篇上传**（内容会过第三方服务器）
   - 微信审核才是终审，工具过完仍可能被拒
3. **ship 一条龙**（cookie 模式）：
   ```python
   moonpub --articles <知识库根> ship social/wechat/<slug>.md --style geek-black
   # env: WECHAT_APPID/SECRET（~/.zshrc）+ WECHAT_AUTH_METHOD=cookie + WECHAT_PREVIEW_TO=qpj4812701762
   ```
   - 自动：封面(geek-black) → 渲染 → 图片传 CDN → 推草稿 → 原创/赞赏/留言/创作来源 → 手机预览发送
   - 成功标志：`media_id: 10001xxxx` + `images: N uploaded`
4. **确认发布**：手机微信收预览 → 满意 → 微信后台/订阅号助手 app 草稿箱发布（人工）
5. **记录**：daily/<当天>.md 追加（media_id、变更）

## 历史 media_id

| 文章 | media_id | 日期 |
|---|---|---|
| D1 交易模型 | 100011335（已发布） | 08-07 |
| D2 套利分层 | 已发布 08-08（误推草稿 100011385 已删） | 08-08 |
| D3 swap | 100011392（已发布） | 08-09 |

## 常见坑

- 图片 >1MB：微信拒（`超过 1MB 限制`）→ sips 压缩：`sips -s format jpeg -s formatOptions 80 --resampleWidth 1200 in.png --out out.jpg`
- qrcode 路径相对 articles root；follow_image 相对文章所在目录
- 二维码过期（7 天）→ 换新图 + 改 moonpub.toml qrcode 行 + 重新 ship
- lifecycle guard 拦截：moonpub 带 `--articles` 必须用 execute_code + subprocess 跑
- **二进制过期**（2026-08-09）：`--style geek-black` 静默 fallback 成 literary 封面 → ship 前 `cargo build --release` + OCR 确认 BUILD NOTES
- **正文主题**：`moonpub.toml theme` 控制（当前 `geek` 浅色，用户定稿）；与 `--style`（封面）独立
- **已发布文章别重 ship**：查 `.moonpub/status.jsonl`，误推用 `delete-draft <media_id>` 删
