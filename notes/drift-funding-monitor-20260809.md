# Drift 链上 perp funding 监控上线（2026-08-09）

> 脚本：`scripts/drift_funding_monitor.py`（driftpy 官方 SDK）+ cron（每小时 watchdog）
> 对应 notes/solana/README.md 研究线「perp: Drift」——与 CEX funding_sentinel_v2 形成链上对照

## 实现要点（含踩坑）

1. **Drift 程序 ID**：`dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH`（v2-teacher 文档确认；网上流传的地址是错的）
2. **依赖**：`uv pip install driftpy`（hermes venv 无 pip；注意会降级 solana-py 到 0.36.6）
3. **精度坑**：funding 用 `last24h_avg_funding_rate`（**1e9 精度**）不是 `last_funding_rate`（1e6，且是 130 天前的陈旧字段）——driftpy 的 AMM 里 `last_funding_rate_ts` 全市场都是 1120 万秒前
4. **market_index ≠ 列表下标**：`get_perp_market_accounts()` 返回列表开头是 MELANIA/预测市场（mkt 65/39/38），必须按 m.name 解析 + market_index 显示
5. **过滤**：跳过 Prelaunch/预测市场（BET/REPUBLICAN 等，funding 天然巨大）+ 用户 <10 的小市场

## 首跑实测（2026-08-09 10:09 UTC，41 个活跃市场）

| 市场 | funding %/24h | 解读 |
|---|---|---|
| **BTC-PERP** | **-16.14 ★** | 链上 BTC 空头极端拥挤（多头付天价费用） |
| **PAXG-PERP** | **+6.46 ★** | 黄金永续多头拥挤 |
| BNB-PERP | +0.98 | 偏多头 |
| ETH-PERP | -0.29 | 偏空头 |
| SOL-PERP | -0.055 | 正常（2396 用户，最大市场） |

## 核心价值：链上 vs CEX funding 对照

- **CEX（funding_sentinel_v2）**：BTC 等主流币永续折价现货 -3~-8bps = 市场冷静
- **Drift 链上**：BTC -16%/24h = 链上永续空头极端拥挤
- **对照结论**：同是 BTC，CEX 永续冷静但 Drift 链上剧烈——**链上 perp 是散户/投机情绪放大器，CEX 是机构定价**。极端 funding 出现 = 链上情绪拐点信号（空头拥挤到极致 → 反弹或踩踏）
- 与 basis_arb_model 联动：BTC 链上 -16% funding 意味着「永续空头付钱」，如果做「现货多 + 永续空」在 Drift 上是**收 funding 的**（对冲成本为负）

## 下一步

- [ ] BTC -16% 深挖：为什么 Drift 上 BTC 空头这么挤（对比 Hyperliquid/Jupiter perp）
- [ ] 链上 funding 历史落盘（攒分位，与 CEX basis 分位同规则）
- [ ] 清算数据接入（Drift 的 User 账户可以算清算线）
