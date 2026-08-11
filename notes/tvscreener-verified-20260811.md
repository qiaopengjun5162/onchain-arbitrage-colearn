# tvscreener 验证：币股时钟差数据源打通（2026-08-11）

> 触发：X 推文 @tiany221 安利 tvscreener（TradingView Screener 的 Python 库）。群内选项 B：验证能否作币股时钟差/多资产筛选数据源。
> 结论：**可用，且有意外的正资产——tokenized 币股和实股两条腿能在一个库拿全。**

## 一、验证结果

| 项目 | 结果 |
|---|---|
| 安装 | `uv pip install --python <hermes venv> tvscreener`（venv 无 pip，uv 秒装） |
| 网络 | **直连可用**（无需 Clash 代理；TradingView scanner API 未墙） |
| 股票 screener | ✅ 美股实时：NVDA $217.55（−2.86%）、AAPL $308.26、TSLA $330.88、TSM $418.47，Price/Change/Change%/1h% 全有 |
| 加密 screener | ✅ BTC/ETH 等 150 行 + **交易所 tokenized 股对**（BITGET:RSPYUSDT、RQQQUSDT、RMUUSDT） |
| Coin screener | ⚠️ DEX 币（CRYPTO:YFIUSD 等），schema 不同，与 tokenized 股无关 |
| 字段 | 13000+ 声称；实测 search()/presets 可用（price/change/volume/market_cap 等） |
| 免费额度 | 150 行/次默认（按市值/活跃排序），无认证，~2-4s/次，stream() 可轮询 |

## 二、币股时钟差的数据闭环（核心价值）

- **实股腿**：StockScreener → NASDAQ:NVDA 等，Change% = 对前收盘涨跌（美股闭市时冻结）——正好是「闭市漂移」研究的实股锚点
- **币股腿**：CryptoScreener → BITGET:RSPYUSDT 等 tokenized 对（RSPY=SPY token、RQQQ=QQQ token），币股 24h 交易，闭市时继续动
- 同一个库、同一套 API，两条腿价格一次拉齐 → `scripts/tokenized-stock-arbitrage` 类监控可以只依赖这一个数据源
- 注意：gate.io 的 bNVDA 风格 token 是否在 TradingView 收录需进一步查（本次见到的是 Bitget 的 RSPY/RQQQ/RMU 系列）；TV 覆盖 ≠ 全交易所覆盖

## 三、限制与坑

- **按 ticker 过滤**：无 set_symbols 方法；isin 不支持多值（报 "Expected one value"）；Symbol 带交易所前缀（NASDAQ:NVDA）→ 用本地 `df[df.Symbol.str.endswith(tuple([...]))]` 过滤
- ACTIVE_SYMBOL 是 bool 字段（分组内是否活跃代码），不是代码字段——按代码过滤别用它
- 默认 150 行按市值排，长尾标的需要换排序/翻页（set_range 存在，未深测）
- 全字段返回时列很多（几百列），用 select() 只挑要的列

## 四、对研究线的意义

- 补上 `notes/us-stock-free-data-sources-20260808.md` 的缺口：免费美股/币股双腿数据源 +1
- 候选落地：币股时钟差监控脚本（实股 Change% 冻结 vs 币股 24h 动 → 溢价扩散检测），接现有哨兵架构
- 多资产筛选：13000 字段支持「市值>X 且 涨跌幅>Y 且 成交量>Z」的选股器式扫描，可服务信息差来源系统（research-backlog #8）

## 关联

- 推文：https://x.com/tiany221/status/2086656283420319771；仓库：github.com/deepentropy/tvscreener
- 笔记：`notes/tokenized-stock-arbitrage.md`（币股时钟差）、`notes/us-stock-free-data-sources-20260808.md`
- 安装位置：hermes venv（`~/.hermes/hermes-agent/venv`）
