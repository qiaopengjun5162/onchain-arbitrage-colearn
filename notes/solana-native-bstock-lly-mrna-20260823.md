# Solana 原生币股 LLY/MRNA 价差核验（2026-08-23）

> 触发：Solana 官方周报（`solana-weekly-20260823.md`）中 $LLY/$MRNA 上线 → 待办「币股监控考虑加 LLY/MRNA」→ 本次实际核验并部署监控。
> 关联：`notes/tokenized-stock-arbitrage.md`（四条路线）、`notes/solana-weekly-20260823.md`
> 产出：`scripts/solana_stock_convergence_watchdog.py` + cron `1da3deea43ef`（周一至五 21:00-22:55 每 15 分钟）

## 标的与结构

| 项 | LLY | MRNA |
|---|---|---|
| 底层 | Eli Lilly (NYSE: LLY) | Moderna (Nasdaq: MRNA) |
| 发行 | Backpack Securities（via Sunrise） | 同左 |
| Mint | `LLYuwZ33keFihgwoxXsBawy31AiRFLFSva32TYq5TvD` | `MRNAzXzhNcaEXJPibHEn8cd4vyekCDiivTyEwswLUCT` |
| 赎回 | 1:1 兑换真实股票（Backpack Exchange 通道） | 同左 |
| 上市日 | 2026-08-20 公告 | 同左 |

结构亮点：与 Gate xStocks/BNB bStock 的「合成价格追踪」不同，Backpack 版 = **真持有底层股票 + 1:1 可赎回**（有真实证券支撑），是币股里偏「真 RWA」的一档。

## 快照（2026-08-23 周六 21:13 北京，美股闭市）

- 美股收盘（8/21 周五）：LLY **$1,255.40** | MRNA **$145.13**
- 链上（DeFiLlama 聚合 / GeckoTerminal 主池）：
  - LLY：$1,252.04（主池 LLY/USDC $1,252.67，流动性 $154.7K，24h 量 $22.9K）
  - MRNA：$148.18（主池 MRNA/USDC $148.35，流动性 $151.4K，24h 量 $8.3K）
- 偏离：LLY **-0.3%（折价 26bps）** | MRNA **+2.1%（溢价 210bps）**

## 判定：不进场，两个硬伤

1. **深度玩具仓**（COINX 教训第 2 条重演）：全生态流动性 LLY ~$300K / MRNA ~$170K，24h 量 <$23K，距用户门槛（24h 量 ≥$1M）差 30-100 倍。$500 即明显滑点，$1K 滑穿。
2. **当前价差 = 闭市漂移非错价**：周六无美股锚，MRNA +210bps = 市场对周一开盘的预期（MRNA 本周 $174→$133 暴跌 -23% 后反弹，mRNA 题材热，市场赌续涨），不是可收敛的错价。

**收敛机制验证（健康）**：MRNA 主池日线 vs 美股收盘——
- 8/19：链上 $165.4 vs 美股 $174.4（-5.2%）
- 8/20：链上 $130.3 vs $133.3（-2.3%）
- 8/21：链上 $145.5 vs $145.1（+0.3%）
链上跟随美股波动，无持续错价。

## 数据源路径（踩坑记录）

- ❌ jup.ag 全系（quote-api/price.jup.ag/api.jup.ag）：Clash 代理 TLS 握手失败（SSL_ERROR_SYSCALL），直连也空 → 弃用
- ✅ DeFiLlama `coins.llama.fi/prices/current/solana:<mint>`：聚合价 + confidence 0.99，无需 key，走代理稳定
- ✅ GeckoTerminal `api.geckoterminal.com/api/v2/networks/solana/tokens/<mint>/pools`：池子价/流动性/24h 量，无需 key
- ✅ yfinance（hermes venv + 代理环境变量）：美股实时/收盘

## 部署

- `scripts/solana_stock_convergence_watchdog.py`：watchdog 模式，开盘（北京 21:30）35 分钟后偏离 ≥150bps 推送；周末/非窗口/开盘前/无信号静默
- cron `1da3deea43ef`：`*/15 21-22 * * 1-5`，no_agent（stdout 非空才推）
- wrapper：`~/.hermes/scripts/run_solana_stock_conv.sh`（指定 hermes venv python 因有 yfinance）

## 下一步

- [ ] 周一（8/24）21:30-22:00 观察首个开盘收敛信号（若链上仍偏离 ≥150bps 且流动性到位 = 真错价窗口）
- [ ] 深度是死穴：若后续 Sunrise/Backpack 给主池加流动性（>$1M），才值得手工扫单
- [ ] 币股线新增同类标的（NBIS/TTWO/SKHY 已上市）可复用同一脚本框架
