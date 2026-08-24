# Morpho HF 清算触发扫描器（2026-08-24）——010 手册第 2 步落地

> 脚本：`scripts/morpho_liquidation_hf.py` ｜ 数据：`data/morpho_hf.jsonl` + `_state.json`
> cron `4c26244b6d9e`：每 30 分钟 watchdog（HF≤1.2 & 抵押品≥$1M & 触发跌幅≤2%，24h 去重）
> 与 `morpho_prey_radar.py`（预言机偏离）组成清算哨兵双件套

## 做了什么

- GraphQL `marketPositions`（where: marketUniqueKey_in + healthFactor_lte + marketListed）→ 持仓级 HF + **`priceVariationToLiquidationPrice`（清算触发跌幅，API 原生提供）** + 抵押品/借款规模
- 字段坑：MarketPositionState 是 `collateralUsd`/`borrowAssetsUsd`（不是 collateralValueUsd）；Market 是 `marketId`（不是 uniqueKey）
- 输出触发阶梯：每个临近清算仓的「价格跌 X% → 触发」+ 按市场汇总临近清算总规模

## 核心发现（2026-08-24 快照）

**USDe→USDC 市场 $286M 抵押品贴着清算线（16 仓，HF≤1.5）**：

| 触发跌幅 | 触发规模 | 备注 |
|---|---|---|
| -0.49% | $14.85M | 0xae0a739c |
| -0.63% | $22.04M | 0x8986F939 |
| -1.01% | $2.01M | |
| -1.24% | $23.30M | 0xB4fb31E7 |
| -1.46% | $10.14M | |
| -1.57% | $9.28M | |
| -1.83% | **$125.42M** | **鲸鱼仓 0x7bee8D37** |
| -1.99% | $49.31M | |
| **累计 -2%** | **≈$260M 连环** | |

- **USDe（稳定币 ≈$1）92% LTV 满杠杆借贷**：跌 0.5% 就开始清算，跌 2% 触发 $260M 连环——稳定币脱锚风险被杠杆放大成清算核弹
- mGLO→USDC：$19.84M 临近（触发跌幅 2.94%/3.44%）——与 prey radar 的 mGLO SIGNAL（oracle 偏离 638bps）联动：oracle 修正方向决定这批仓位的生死
- 其余市场（cbBTC/WETH/cbXRP 等）无大额临近清算——健康

## 与 prey radar 的配合（清算哨兵完整形态）

1. **prey_radar**（预言机层）：oracle vs 现货错价 → 埋雷检测（HERMES 冻结论价机 / mGLO 偏离）
2. **HF 扫描器**（持仓层）：知道「价格跌 X% → 清算 Y 规模」→ 触发阶梯
3. 完整触发条件 = 预言机更新向错价方向 + 价格穿越触发线 → 清算连环（010 手册 sNUSD 16h 生命周期同构）

## 可执行项

- [x] **USDe 脱锚监控联动（已落地 efb9285）**：USDe/USD 现货价跌破 $0.995 即输出清算触发阶梯预警（DeFiLlama USDe 价，地址 0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34；模拟脱锚验证通过，与 30min cron 合一）
- [x] **鲸鱼仓 0x7bee8D37 专项观察（已落地 8494789）**：`--whale-trend N` 读 morpho_hf.jsonl 输出 collateral≥$10M 仓位的 HF 时间序列（0x7bee8D37 $125M 仓在列，04:45→05:00 实测 HF 稳定 1.019）
- [ ] Flashblocks 200ms 决胜层（010 第 3 步）：触发前 30s 内进场路径设计（暂不执行，只研究）
