# 共学平台 Agent API（ICL 2.0 Agent API）

来源：https://intensivecolearn.ing/llms.txt （contract version 1.2.0，2026-08-05 抓取）

## 基本信息

- Base URL：https://intensivecolearn.ing/api/v1
- OpenAPI 3.1：https://intensivecolearn.ing/api/v1/openapi.json
- 认证：`Authorization: Bearer <ICL_ACCESS_KEY>`
- 限速：每个 key 120 请求/分钟（数据库计数器）
- 请求体上限 64 KiB；打卡内容上限 20,000 字符

## 安全规则（重要）

- Access Key 是秘密：不打印到聊天、日志、代码、URL 或工具输出
- Key 只在个人设置里显示一次，不可找回；怀疑泄露立即撤销
- 写操作必须带 `Idempotency-Key`；重试只能用相同 method+path+body+key
- 不同的输入禁止复用同一个 Idempotency-Key（不匹配返回 409）
- 验证/权限错误不要重试

## 学员视角的关键端点

只读：

- `GET /me`：验证当前用户和凭证
- `GET /programs`：列出目录里可见的课程
- `GET /programs/{programId}`：读课程信息
- `GET /programs/{programId}/events`：读课程活动
- `GET /me/check-ins`：读自己的打卡（分页）
- `GET /me/applications`：读自己的报名

写（都要 Idempotency-Key）：

- `POST /me/check-ins`：创建打卡（`{"programId":"...","content":"..."}`）
- `PATCH /me/check-ins/{checkinId}`：更新打卡

打卡示例（官方）：

```bash
curl -sS -X POST "https://intensivecolearn.ing/api/v1/me/check-ins" \
  -H "Authorization: Bearer $ICL_ACCESS_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: checkin-2026-08-05-b43d2e97" \
  --data '{"programId":"b43d2e97-ed88-4ca3-b12f-7ef672b01205","content":"Today I completed..."}'
```

幂等键建议格式：`checkin-<日期>-<课程短id>`，同一天同一课程的创建重试安全。

## 日期语义

- 报名和课程生命周期字段用 UTC+8 日历日，不是精确时刻
- 事件 startsAt 用 `YYYY-MM-DDTHH:mm`（UTC+8 本地，无秒无时区后缀）

## v1 没有的能力

- 事件更新（只能取消重建）、仓库删除、分配管理员、Access Key 管理——这些只能在网页操作

## 接入清单（对本项目）

1. 官网个人设置创建 Access Key（只显示一次，当场复制）
2. 发给 Hermes：先 `GET /me` 验证凭证，再 `GET /programs/b43d2e97-ed88-4ca3-b12f-7ef672b01205` 读课程
3. 每天学习结束，让 Hermes 整理内容 `POST /me/check-ins` 打卡
4. 定期 `GET /me/check-ins` 核对官网显示和本地记录一致

## 实测记录（2026-08-05 D1，全部通过）

- `GET /me`：200，Paxon Qiao 乔鹏军，icl1-user-124650229，role: user，已 onboarded
- `GET /programs/{id}`：200，课程 ongoing，报名状态 approved
- `GET /me/check-ins`：200，total: 0（D1 尚未打卡）
- Hermes 侧走了国内代理 http://127.0.0.1:7890，正常
- 注意：Hermes 实测还发现了 tRPC 端点（program.getById）和 `X-Secret-Api-Key` 认证头也能用——这是 v1 REST API 之外的另一套接口，打卡等写操作建议仍走官方文档的 REST + Bearer + Idempotency-Key 路径，tRPC 随时可能变

## 实测记录（2026-08-07 D3，打卡 PATCH 更新）

- `PATCH /me/check-ins/{id}` 的 requestBody **必须含 `updatedAt`**（date-time 乐观锁，取现有打卡的 updatedAt 字段值），只传 content 会返回 `validation_error / updatedAt Invalid date`
- 响应结构：`{apiVersion, data: {items: [...]}}`（列表分页在 `data.items`，不是顶层）
- 踩坑：python urllib 直连返回 403（TLS 指纹被拦），同机 curl -skL 直连正常；且 urllib 会读代理环境变量（ICL API 走代理 403(1010)），需 `ProxyHandler({})` 或干脆用 curl
- ~/.hermes/.env 中 ICL_ACCESS_KEY 是 `export ICL_ACCESS_KEY=` 前缀写法，解析时要 strip 前缀
- 幂等键更新用新值：`checkin-update-2026-08-07-b43d2e97`（同一输入重试安全，不同输入禁止复用）
