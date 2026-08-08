# Titan DART Swap API Access

来源：

- https://titan-exchange.gitbook.io/titan/developer-doc/dart-swap-api/get-api-access
- Markdown: https://titan-exchange.gitbook.io/titan/developer-doc/dart-swap-api/get-api-access.md

## 定位

Titan DART Swap API 是 Solana 路由/Swap API 研究资料之一，适合用来观察：

- swap API 接入方式
- 公共 endpoint 限速
- partner API key 模式
- REST/JSON 请求结构
- transaction building

## 关键点

公共 endpoint：

- Base URL: `https://api.titan.exchange/dart`
- 不需要 API key
- 每个 IP 每秒 1 次请求
- REST only
- JSON response
- DART provider only

Partner access：

- 通过 `Authorization: Bearer YOUR_API_KEY`
- 或 `X-API-Key: YOUR_API_KEY`
- 需要填写申请表获取 partner API key

## 和套利研究的关系

这类 API 不一定直接用于高频执行，但很适合早期研究：

- 获取 quote
- 比较 route
- 观察不同规模交易的报价变化
- 记录 API 限速和接入成本
- 分析公共 endpoint 和 partner access 的能力差异

公共 1 rps 更适合低频观察、数据结构学习和手动验证，不适合实时抢机会。

## 数据字段方向

后续看 Overview / How to Use 时重点提取：

- input mint
- output mint
- amount
- slippage
- route
- fee
- expected output
- transaction payload
- provider
- error code
- rate limit behavior

## 安全边界

- 不在笔记中保存 API key。
- 不把交易构造结果当作执行建议。
- 不用主钱包直接测试第三方 API 生成的交易。
- 先做 quote 和 transaction inspection，再考虑 devnet 或小额测试。

## 下一步

1. 阅读 Titan DART Overview。
2. 阅读 How to Use，提取请求/响应字段。
3. 和 Jupiter Quote API 做字段和限速对比。
