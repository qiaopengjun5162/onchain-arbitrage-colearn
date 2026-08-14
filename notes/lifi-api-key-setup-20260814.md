# LI.FI API Key 配置清单（2026-08-14）

> 来源：Bruce Xu 工具文「注册与开通」部分 + Paxon 已注册（Integration 已完成）
> 定位：执行现实学配套操作清单——把 120 轮报价实验的匿名额度升级为正式配额

## 状态

- LI.FI Partner Portal 注册：✅ 已完成（Paxon，2026-08-14 确认）
- API Key 配置：待完成（本清单）

## 配置步骤

```
① 确认 Key 状态：Portal → Integration 详情
   - Key 只显示一次；若当时没保存：看 Portal 是否支持重新查看，
     不支持则新建 Integration 拿新 Key
② 测试：curl -H "x-lifi-api-key: <KEY>" https://li.quest/v1/keys/test
   → 返回 ok 即有效
③ 安全存放（不进 git/不进聊天）：~/.config/lifi/lifi_key
④ 脚本接入：环境变量 LIFI_API_KEY 读取；header:
   headers["x-lifi-api-key"] = os.environ["LIFI_API_KEY"]
⑤ 验证：对比匿名 vs 带 Key 的 quote 请求（复用 120 轮实验脚本）
```

## 安全铁律

- Key = 账号凭据，**只存本地配置文件**，聊天/仓库/GitHub 只出现变量名 `LIFI_API_KEY`
- KB 是公开 repo——任何 key 进 repo 即泄漏
- 服务端携带，不暴露浏览器前端（Bruce 原文强调）

## 后续

- `day6_lifi_quote_compare.py` 等脚本升级为带 Key 版本（Hermes 执行）
- 带 Key 后跑一轮对比验证配额/限流差异
- 登记表单（tally.so/r/PdQ4q1，截止 08-31）用真实 Integration 名 + 草稿场景提交，走提额

## 关联

- `notes/execution-reality-infra-latency-20260814.md`（登记福利 + 25bps integrator 归零实测）
- `notes/l0006-integrator-retest-20260812.md`（integrator=jumper.exchange 归零平台费）
- `scripts/day6_lifi_quote_compare.py`（120 轮报价实验）
