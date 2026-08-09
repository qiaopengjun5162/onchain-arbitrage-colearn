# Hermes runtime_footer 配置：回复尾部显示模型/session（2026-08-09）

> 来源：https://x.com/brucexu_eth/status/2086271718306496594（brucexu.eth，2026-08-09）
> 状态：Hermes 配置技巧（官方文档已支持），对本机 Hermes 直接可用

## 用途

每条回复消息尾部自动附加：
- **当前 session 用的模型**
- **reasoning effort**（推理强度）
- **session 状态**（新开 vs 之前的）

对多模型配置 + 长 session 特别有用：一眼看到当前在用什么模型跑，任务开始前可手动切换或开新 session。

## 配置（回复区 Iilaclove 验证）

```yaml
display:
  platforms:
    telegram:
      runtime_footer:
        enabled: true
        fields:
          - model
          - reasoning_effort
          - session_status
```

官方文档：https://hermes-agent.nousresearch.com/docs（Configuration → display）

## 备注

- Bruce 原帖以为是手动 Prompt 加的，实际官方 config 已支持（`runtime_footer`）
- rayoo_eth：配合 Auxiliary models 使用效果好
- 对本项目：多模型跑脚本/分析时能确认「谁在干活」——尤其 cron 任务与手动任务混跑时

## 状态

- [x] 本机 Hermes 已配置（2026-08-09）：`~/.hermes/config.yaml` runtime_footer enabled: true，fields 改为 model/reasoning_effort/session_status（原 context_pct/cwd）——重启 gateway 后生效
