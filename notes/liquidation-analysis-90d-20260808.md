# DeFi 清算全量分析（Dune 等价实现，90 天）

> 任务：D4 遗留「Dune 清算数据分析」——Dune 仪表盘（dune.com/gcm/ethereum-block-building）被 Cloudflare 403 拦截
> 方案：DeFi Sphere 公开 API（sphere.data.blockanalitica.com/liquidations/）等价实现全量历史分析
> 产出：`scripts/dune_liquidation_analysis.py` + `data/liquidation_analysis_30d.json` + `data/liquidation_analysis_90d.json`
> 日期：2026-08-08

## 数据总览（90 天，5 网络）

| 指标 | 值 |
|---|---|
| 总清算数 | 17,071 笔 |
| 抵押品总额 | $385,965,737 |
| 清算奖励总额 | $17,715,015（≈4.6% 的抵押品） |
| 大额清算（≥$50K 抵押） | 828 笔 |
| 高奖励清算（≥$5K 奖励） | 451 笔 |

## 按网络（90 天）

- **base: 10,514（62%）**——清算活动主战场
- ethereum: 4,352（25%）
- arbitrum: 2,202（13%）
- optimism: 3；polygon: 0（数据源覆盖有限）

## 按协议（90 天 Top）

- **morpho: 10,153（59%）**——压倒性第一（长尾市场/独立池）
- aave_v3: 3,209 + aave_v3_core: 2,604（合计 34%）
- compound_v3: 600；sparklend: 352；curve_llamalend: 106

## 关键发现

1. **Morpho 是清算主战场**：90 天 10,153 笔 = 59% 份额——清算套利监控应优先覆盖 Morpho（当前 DeFi Sphere 清算哨兵未区分协议，可加过滤）
2. **Base 链清算密度最高**：62% 清算在 Base（低成本 L2 借贷活跃）——清算监控哨兵当前只跑 ethereum/arbitrum/base/optimism/polygon，Base 已覆盖 ✅
3. **奖励率 ≈ 4.6%**：奖励/抵押品 4.6%——高于常见 5-10% 清算折扣下界，套利毛利空间真实存在但薄
4. **单笔最大**：morpho 7/15 奖励 $74,183（单笔 > $70K 套利机会）
5. **被清算钱包集中度**：top 10 钱包占 121+97+69+... ≈ 490 笔（2.9%）——大部分清算分散，但也有连环爆仓者（如 0xfb70... 被清 121 次）

## 与清算哨兵的对接

- 现有 `liquidation_monitor.py`：实时监控（24h 窗口、$50K 抵押阈值）
- 本分析：**全量历史视角**（90 天分布、协议/网络结构）
- 互补结论：**哨兵应加协议过滤（morpho 优先）** + 历史基线（今天 X 笔 vs 90 天日均 190 笔）

## 踩坑记录

1. API 路径必须带尾部斜杠 `/liquidations/`（不带 404）
2. 响应结构是 `{"data": {"results": [...]}}`，需解包
3. `collateral_seized_usd` / `liquidation_bonus_usd` 是**字符串**不是数字，需 float 转换
4. API **无清算人字段**（只有 wallet_address=借款人）——「谁在清算」需从 tx 数据另查
5. fd 泄漏问题：本会话大量网络调用后 execute_code 报 Errno 24，需等系统回收

## 待做

- [ ] 哨兵加 morpho 协议优先过滤 + 历史日均基线
- [ ] 清算人侧分析：从大额清算 tx 反查清算人地址（补 API 缺口）
- [ ] Base 链清算密集度的原因探究（morpho 长尾池在 Base 活跃？）
