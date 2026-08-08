# Helius Dashboard

来源：

- https://dashboard.helius.dev/login?redirectTo=/dashboard
- https://docs.helius.dev/

## 定位

Helius Dashboard 是 Solana 数据基础设施的账号型管理入口，适合管理和观察：

- RPC endpoint
- API key
- Webhook
- Enhanced Transactions
- DAS / NFT / Token API
- 请求量和项目配置

## 和套利研究的关系

如果要做 Solana watcher、route snapshot、交易监控或地址追踪，Helius 可以作为早期数据源之一。

适合先验证：

- RPC 请求稳定性
- WebSocket / Webhook 能否满足实时性
- Enhanced Transactions 是否能减少解析成本
- 免费/付费额度是否够做共学阶段实验

## 安全边界

- 不在项目笔记中保存 API Key。
- 不把 Dashboard 截图里的 key、项目 ID、请求细节公开。
- 脚本读取 key 时使用环境变量或本地未提交配置。

## 下一步

1. 阅读 Helius Docs，整理可用 API 列表。
2. 设计一个只读 watcher 的最小数据字段。
3. 如果创建项目，记录配置项，但不记录密钥。
