# L0006 integrator 参数复测：25bps「地板」实为默认参数渠道费（2026-08-12）

> 触发：群友 064（Web3Rason）发现 `integrator=jumper.exchange` 让 LI.FI 平台费归零（997.5→1000.0 USDC）
> 复测：`scripts/l0006_integrator_retest.py`，Base USDC → Arbitrum USDC，integrator × 金额 全矩阵，2026-08-12 02:53 UTC 实测
> 状态：✅ 已复现并扩展（16 组报价全部成功）

## 结果表（到账 USDC）

| integrator | 100 | 1,000 | 10,000 | 100,000 |
|---|---|---|---|---|
| **无（默认）** | 99.75 | 997.50 | 9,975.00 | 99,750.00 |
| **jumper.exchange** | **100.00** | **1,000.00** | **10,000.00** | **100,000.00** |
| socket | 99.75 | 997.50 | 9,975.00 | 99,750.00 |
| lifi | 99.75 | 997.50 | 9,975.00 | 99,750.00 |

- 无 integrator / socket / lifi：feeCosts = `LIFI Fixed Fee` 0.2510% 恒定（100U 收 0.251$，100k 收 250.99$）——**比例费、无规模折扣，与 L0006 原结论一致**
- **jumper.exchange：feeCosts = 0，全金额档 25bps 归零**（gas 也略降 0.0065$→0.0041$，路径处理差异）

## 结论

1. **L0006「25bps 恒定地板」修正为「默认参数渠道费」**：LI.FI 自家前端（jumper.exchange 是其官方产品）不付平台费，第三方渠道付 0.25%。对套利者：**quote 一律带 `integrator=jumper.exchange`，地板从 25bps → 0**
2. 只有这个特定 integrator 免；socket/lifi 均照收——**integrator 参数必须写入所有成本模型与脚本**（064 原话：成本纪录没写 integrator 就不可比，验证成立）
3. 无规模折扣结论保留，但性质变了：25bps 是渠道成本而非协议硬下限
4. break-even 门槛整体下移 25bps：跨链 USDC 从「>0.5% 往返才有理论空间」→「>0.25% 往返」量级（桥费仍是最小项之外的主导，见下）

## 对已有结论的连锁修正

- **DOS 搬砖（dos-bridge-arb-20260811）**：当时净 7.6bps 是含默认平台费的口径 → 带 jumper.exchange 重测预计回到 ~32bps 量级，**仍 NO-GO**（BSC→ETH 桥费 $0.69 才是杀手），但门槛显著变松
- **「时长假象」（L0006）**：报价不含时间维度的结论不受影响（executionDuration 7s 恒定）
- **052 库存再平衡 / 053 等待定价**：再平衡成本与等待漂移是独立项，不受影响；但 LI.FI 各腿 quote 均应带 integrator 重算
- **群友 086/058「0.25% 服务费硬下限」**：为默认渠道口径，非硬下限

## 待办

- [ ] 各跨链脚本统一加 `integrator=jumper.exchange`（day6_lifi_quote_compare.py、multi_chain_spread_monitor.py 的 LI.FI 部分）
- [ ] DOS 报价带 integrator 重测，更新 dos-bridge-arb 笔记净价差数字
- [ ] （可选）验证 jumper.exchange 在 quote/advanced-routes/execute 三端行为一致（本次只测 quote）

## ⚠️ 勘误（2026-08-12 下午）：DOS 重测假设被证伪——integrator 对 DOS 无影响

- **假设**（本笔记初版）：DOS 净 7.6bps 含默认平台费，带 jumper.exchange 应回升到 ~32bps
- **实测证伪**：①LI.FI `/v1/quote` 对 BSC→ETH 全部 404（USDT/DOS/任意币，含 sanity 对照）——**LI.FI 根本没有 BSC→ETH 主网路由**，Base→Arb 同参数正常（997.5/1000.0 复现）②查原笔记：DOS 走 **LayerZero V2 原生 OFT 桥**（BSC OFT ↔ ETH OFTAdapter，桥费 BSC→ETH $0.69 = LayerZero 消息费 + BNB gas），**与 LI.FI 平台费是两个独立系统**
- **修正结论**：DOS 的 7.6bps 本来就是「无 LI.FI 平台费」口径；integrator 参数不适用 → 净价差维持 ~7.6bps，**NO-GO 判定不变**
- **新发现（更有价值）**：跨链成本模型必须按「实际桥」核算——LI.FI 覆盖 ≠ 全链（BSC→ETH 盲区）；聚合器报价查不到 ≠ 路径不存在（DOS 走原生桥活得很好）
- 教训：先写假设再验证（AGENTS.md 规则），假设被数据打脸是正常产出
