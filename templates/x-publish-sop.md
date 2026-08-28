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
| D3 | x.com/qiaopengjun/status/2086403022721290416 | 6 | 08-09 发布 |
| D4 | x.com/qiaopengjun/status/2086744237509578896 | 6 | 08-10 发布 |
| D5 | x.com/qiaopengjun/status/2087032122293039513 | 7（5/6 拆条 + 公众号条） | 08-11 发布 |
| D6 | x.com/qiaopengjun/status/2087353099086410106 | 9（3/5/6 超长拆条） | 08-12 发布 |
| D7 | x.com/qiaopengjun/status/2087813689181352024 | 7（6 条正文 + 公众号链接条） | 08-13 发布 |
| D8 | x.com/qiaopengjun/status/2088204222231887896 | 6（公众号链接+标签在 6/6，零拆条） | 08-14 发布 |
| D9 | x.com/qiaopengjun/status/2088795789107794383 | 7（6 正文 + 公众号链接条带标签） | 08-16 发布 |
| D10 | x.com/qiaopengjun/status/2088975731204517896 | 8（6 正文 + 标签条带 TG 链接 + 公众号链接条） | 08-16 发布 |
| D11 | x.com/qiaopengjun/status/2089341248033501244 | 9（2/8 拆两条 + 5 正文 + 标签条带 TG + 公众号条） | 08-17 发布 |
| D12 | x.com/qiaopengjun/status/2089645125786022018 | 9（8 正文 + 末条合并 TG/公众号链接/4 hashtag） | 08-18 发布 |
| D13 | x.com/qiaopengjun/status/2090354571478786201 | 9（8 正文 + 末条合并 TG/公众号链接/4 hashtag；4/9 LI.FI 被 X 自动链接化为 t.co） | 08-20 发布 |
| D14 | x.com/qiaopengjun/status/2090742711175549337 | 9（末条合并公众号链接+TG+4 hashtag，链接自动 t.co） | 08-21 发布 |
| D15 | x.com/qiaopengjun/status/2090989012345643051 | 9（末条合并公众号链接+TG+4 hashtag；当日草稿未落盘，08-23 按 RSC 验证补建记录文件） | 08-22 发布 |
| D16 | x.com/qiaopengjun/status/2091158131988664454 | 10（草稿 9 条，用户发布时拆 5/9 成两条；末条 TG+公众号+4 hashtag，用户去掉 TG+2 hashtag 留 #Solana #Web3） | 08-22 发布 |
| D17 | x.com/qiaopengjun/status/2091445980784968115 | 10（与草稿 1-10 完全一致无拆分；末条公众号链接+TG+4 hashtag 全保留） | 08-23 发布 |
| D18 | x.com/qiaopengjun/status/2091702202952040464 | 12（与草稿 1-12 完全一致；末条链接 t.co 化） | 08-24 发布 |
| D19 | x.com/qiaopengjun/status/2092152136906027497 | 12（1-11 逐字一致；末条按草稿核对） | 08-25 发布 |
| D20 | x.com/qiaopengjun/status/2092572064037429616 | 12（起始帖逐字一致，回复链待补验） | 08-26 发布 |
| D21 | x.com/qiaopengjun/status/2093191669080526854 | 14（RSC 全链核验逐条一致，全部 status ids 已归档） | 08-28 发布 |

## 常见坑

- `credits depleted 402`：X API 需要充值 credits（最低 $5），充值前所有读写都发不了 → 手动发
- xurl 不走代理超时：必须 `HTTPS_PROXY=127.0.0.1:7890`
- 验证 thread 用 web_extract（xurl read 同样耗尽）
- 不要用 `xurl --verbose`（会泄露 token）；`~/.xurl` 含凭据，绝不进 LLM context
