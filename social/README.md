# 自媒体草稿

这里放后续可改写成以下内容的草稿：

- X posts
- 长文
- 共学打卡
- Newsletter
- 公开学习笔记

发布前删除：

- 私人交易细节
- 精确账户规模
- 密钥或凭据
- 可被滥用的脚本
- 未验证判断
- 任何暗示稳赚的表达

## 发布流水线（2026-08-05 起）

> **总 SOP：`templates/daily-publish-pipeline.md`**（打卡 → 公众号 → X → 归档全流程 + 防重复发布检查）
> 子 SOP：`templates/wechat-publish-sop.md`（公众号）+ `templates/x-publish-sop.md`（X）

### 目录

- `social/x/`：X 推文草稿
- `social/wechat/`：公众号文章草稿（moonpub 输入格式）

### 公众号（moonpub 全自动）

1. Hermes 把当天 daily/ 笔记改写成公众号文章，存到 `social/wechat/<date>-<slug>.md`
2. 调用 moonpub CLI：`moonpub render` + `moonpub ship` 推到公众号草稿箱
3. 凭证走环境变量 `WECHAT_APPID` / `WECHAT_SECRET`，不入聊天不入库
4. 手机预览，用户确认后才正式发布

moonpub 项目：/Users/qiaopengjun/Code/Rust/moonpub（Markdown -> 渲染 -> 草稿箱 -> 确认发布）

### X（半自动）

- 没有 X Premium，用免费档 API（约 500 条/月）或只出草稿手动发
- Hermes 出 thread 草稿存 `social/x/`，用户确认后发布

### 内容红线（两个平台通用）

- 共学学员笔记是内部私享，不外传；只发自己的学习记录和公开资料整理
- 群里其他同学的观点要改写来源或获得授权
- 发布前必须人审（AGENTS.md 规则）
