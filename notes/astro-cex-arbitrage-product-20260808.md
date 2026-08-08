# Astro（astro-btc）— CEX 套利策略产品调研

> 来源：https://astro-btc.xyz/ + https://github.com/astro-btc/Astro（Paxon 分享 2026-08-08）
> 领域：CEX 资金费率套利 / 现货-合约价差套利 / 汇率网格 | 类型：闭源商业产品（安装脚本 + SDK 接口）
> 关联：`notes/funding-fee-arbitrage-1token.md`（资金费套利基础方法论）

## 产品定位

Astro 是一套**交易所套利策略自动化系统**：用户购买/部署服务后，通过浏览器管理后台配置交易对（pair），系统自动在多家 CEX 之间执行套利。支持 Binance、Bybit、Bitget、OKX、Gate、Kucoin、Aster、Backpack、Hyperliquid、Htx、Lighter 共 11 家。

- 产品使用群：https://t.me/astro_discuss
- 行情工具：https://pulse.astro-btc.xyz/ + https://astro-btc.github.io/Astro-Perps/?coin=ETH
- 实时资讯/上新/费率调整：https://t.me/astro_realtime_news
- 完整产品文档：https://www.notion.so/Astro-2900e967938c80419830e5baf64f00f5

## 策略模式（pair.type）

| 类型 | 含义 | 说明 |
|---|---|---|
| SF | 现货-合约（现期） | 同一交易所或跨所，现货吃资金费率/价差 |
| FF | 合约-合约（期期） | 不同永续之间价差 |
| SR | 现货-现货（现汇） | 跨所现货价差，STEP 文档示例 ETH/BTC 汇率 |
| FR | 合约-现货（期汇） | 反向组合 |
| FS | 混合 | 支持 spotMarginType 参数（spot/cross/isolated） |

核心参数：`openPosition`/`closePosition`（开平仓阈值）、`maxTradeUSDT`（≥10）、`leverage`、`buyEx`/`sellEx`（买卖交易所）、`minNotional`（≥6）/`maxNotional`、`stopLoss`、`stepOpen`/`stepClose`（梯度开平仓）、`rateMultiply`（倍率）、`priceAlert`。

## 汇率网格（Docs/GRID.md）— 设计亮点

ETH/BTC 汇率网格例子：
- 用户只需设 4 个参数：最小汇率（网格下限）、最大汇率（网格上限）、最大仓位价值、格子数量
- 系统算出：每格汇率差、每格利润率（2×格差/(上限+下限)）、每格资金占用（总仓位/格子数）
- **关键风控提示（原文）**：每格资金占用一定要大于单笔最小下单额 2 倍以上（Binance BTC 最小单 110U），否则来回开单会迅速磨光本金
- 交易逻辑：当前格子 N，只做两件事——N+1 满仓则清仓、N-1 空仓则买入；单边行情同时买卖是换仓不是 BUG
- 建议最小单 10-20U：网格交易不抢单，有足够时间吃满一个格子，滑点更低

## 架构（从 INSTALL.md / SDK-API.md 推断）

```
浏览器管理后台（HTTPS, 默认端口 8443）
  └── astro-server（.env: PORT / ALLOWED_DOMAIN / ADMIN_PREFIX / ADMIN_SECURITY_CODE / ADMIN_2FA_SECRET）
        └── astro-core（执行核心，add pair 会触发其重启，需等 3 秒）
              └── 交易所 API（Binance 统一账户 / Bybit 全仓 / OKX 合约模式 / Gate 统一+跨币种…）
```

- 部署：Ubuntu x86-64，最少 2GB 内存；**禁止中国境内服务器**；**不要用美国服务器**（Bybit 拒绝美国 IP 调 API）；境外网络可本地部署但 API 需绑定 IP
- 后端 API 为 `POST /xxx/api/config/sdk-update-pair`（xxx=ADMIN_PREFIX），本机 127.0.0.1:12345

## SDK 接口（sdk-demo.js / SDK-API.md）

- 鉴权：`x-timestamp`（毫秒，±30s 窗口）+ `x-nonce`（12-64 位，防重放）+ `x-sign`（HMAC-SHA256，key=API Key）
- canonical message：`${timestamp}\n${nonce}\nPOST\n${apiPath}\n${rawBody}`（服务端用原始 body 验签，客户端必须签原始 JSON 字符串）
- 限频：20 次/10s，按 IP，超限 429
- Pair 管理：list/add/update/delete；Message：warning/notice（走飞书报警，前缀 `[uiw]-`/`[uin]-`）
- API Key 通过管理后台「开发者代码」`set api-key ***` 设置（12-32 位随机，被盗可开单，需谨慎保管）

## 安全清单（SECURITY.md 官方必读）

服务器：不暴露 IP / 禁 SSH 密码登录 / 防火墙只开 22 + 8443
交易所 API：**必须绑定 IP 白名单** + **绝不开提现权限**（两条反复强调）

## 风险与评估（研究视角）

- 闭源产品，核心策略实现（astro-core）不可审计；信任边界 = 运营方服务器 + API Key 权限
- 商业模式是卖策略服务 + 部署后自持 API key，用户仍需自己承担交易所 API 绑定 IP 等安全责任
- 网格/梯度参数设计（格子资金 vs 最小下单额）是有价值的工程经验，不依赖闭源实现即可复用
- 资金费率套利基础风险清单见 `funding-fee-arbitrage-1token.md`（方向、交割、费率波动、本金占用）

## 待跟进

- [ ] Notion 产品文档全量阅读（https://www.notion.so/Astro-2900e967938c80419830e5baf64f00f5）
- [ ] 评估是否需要实盘试用（需境外服务器 + 交易所 API，属实盘决策，需人工确认）
- [ ] 网格参数设计公式可沉淀到套利武器库（每格资金占用 ≥ 2× 最小下单额）
