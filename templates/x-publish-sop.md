---
用途: X (Twitter) thread 手动发布模板（每日共学打卡 → X thread）
触发: 用户说"把第X天发 Twitter" / "X thread"
---

# X Thread 发布 SOP（2026-08-08 定稿）

> 工具：xurl（官方 CLI，已认证 my-app/qiaopengjun）— 但 **API credits depleted（402）**，读写均需付费额度，目前只能手动发
> 代理：X API 被墙，xurl 必须走 `HTTPS_PROXY=http://127.0.0.1:7890`（Clash）

## 流程（约 5 分钟）

### 1. 写 thread 草稿 → `social/x/<日期>-d{N}-thread.md`

- 素材：当天公众号文章（`social/wechat/`）或 `notes/` 笔记
- 格式：`**1/6**` 标题行 + 正文，6 条（D1/D2 均 6 条），末条带标签 `#链上套利 #MEV #Crypto`（按主题加 #LI.FI 等）
- 风格：口语化、每条约 100-150 字、一条一个观点、有钩子
- 文件尾部保留 `## 发布记录` 占位（Thread 起始/各条/方式/状态），发布后补全

### 2. 先试自动发（万一额度恢复）

```python
env = {"HTTPS_PROXY": "http://127.0.0.1:7890", "HTTP_PROXY": "http://127.0.0.1:7890"}
# xurl --app my-app post "<第1条>"
# 报 credits depleted → 转手动
```

### 3. 手动发布（当前常态）

1. X 网页/App 发第 1 条
2. **回复**第 1 条发第 2 条（自动串 thread）
3. 依此类推 6 条，末条带标签
4. 把起始链接发 Hermes → 验证 + 更新记录

### 4. 验证 + 归档

- 验证：`web_extract https://x.com/...` 看 6 条是否串完整（xurl read 也耗尽，用网页抓取）
- 归档：`social/x/<文件>.md` 补 `## 发布记录`（Thread 起始 + 各条 ID）
- daily 追加

## 历史 thread

| 天数 | 起始链接 | 条数 | 日期 |
|---|---|---|---|
| D1 | x.com/qiaopengjun/status/2085661488010912055 | 6 | 08-07 发布 |
| D2 | x.com/qiaopengjun/status/2085913863829229589 | 6 | 08-08 发布 |

## 常见坑

- `credits depleted 402`：X API 需要充值 credits（最低 $5），充值前所有读写都发不了 → 手动发
- xurl 不走代理超时：必须 `HTTPS_PROXY=127.0.0.1:7890`
- 验证 thread 用 web_extract（xurl read 同样耗尽）
- 不要用 `xurl --verbose`（会泄露 token）；`~/.xurl` 含凭据，绝不进 LLM context
