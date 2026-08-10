# Day 6 (L0006) 报价对比实验：Base→Arbitrum USDC 三档 × 三桥

> 来源：官方路线图 L0006（1k/10k/100k USDT 跨链报价对比，找意外好路径）
> 脚本：`scripts/day6_lifi_quote_compare.py`（只读，li.quest/v1/quote）
> 数据：`data/day6_lifi_quote_compare.csv`（2026-08-10 03:02 UTC）
> 状态：✅ 实测完成，含一手新发现

## 实验设计

- 路线：Base 原生 USDC → Arbitrum 原生 USDC（与笔记063/058 同路线，有群友基线）
- 金额：1,000 / 10,000 / 100,000 USDC（官方 L0006 三档）
- 桥变体：best（默认最优） / allowBridges=across（快桥） / allowBridges=polymer
- 验证点：笔记058（无规模折扣）/ 笔记063（速度溢价）/ 笔记116（容量假象）

## 原始数据（9 次报价）

| 金额 | 变体 | 到手 USDC | 损耗 | 费用 USD | Gas | 执行时长 | 桥 |
|---|---|---|---|---|---|---|---|
| 1k | best | 997.5000 | 25.0bps | 2.51 | 0.0069 | 7s | eco |
| 1k | across | 997.3948 | 26.1bps | 2.62 | 0.0051 | 1s | across |
| 1k | polymer | 997.2706 | 27.3bps | 2.74 | 0.0085 | 10s | polymer |
| 10k | best | 9975.0000 | 25.0bps | 25.10 | 0.0069 | 7s | eco |
| 10k | across | 9973.9970 | 26.0bps | 26.11 | 0.0051 | 1s | across |
| 10k | polymer | 9972.7057 | 27.3bps | 27.41 | 0.0085 | 10s | polymer |
| 100k | best | 99750.0000 | 25.0bps | 251.05 | 0.0069 | 7s | eco |
| 100k | across | 99740.0195 | 26.0bps | 261.07 | 0.0051 | **900s** | across |
| 100k | polymer | 99727.0575 | 27.3bps | 274.09 | 0.0085 | 10s | polymer |

## 三个验证结果

1. **笔记058 ✅ 亲手复现**：best 三档损耗恒 25.0bps（0.25% LI.FI 固定费），无 min fee、无规模折扣——与群友 64 条实测一致。Gas 恒定 $0.0069（固定成本）。
2. **笔记063 ✅ 亲手复现**：eco(7s) vs across(1s) 快 6 秒少拿 $0.1052@1k / $1.003@10k ≈ **1.0-1.1bps 恒定速度溢价**——与群友「快 6 秒 ≈ $0.103/1000U」同量级。
3. **笔记116 ⚠️ 补充新形态——「时长假象」**：across 在 100k 档执行时长从 1s 暴涨到 **900s（15 分钟）**，而报价金额几乎不变（99740.02 vs 10k 档 9973.997 的比例一致）。这不是 116 的「排名崩塌+报价暴跌」形态，而是**报价不变、执行时长暴涨 900 倍**——对机会寿命 <15 分钟的套利，这笔「最优报价」实际不可执行。

## 结论

1. **跨链稳定币 USDC→USDC 的成本结构极其干净**：0.25% 固定费地板 + Gas 固定 + 桥费按比例，三档完全线性——「越大越划算」不成立，但也无容量陷阱（本路线）。
2. **速度是正交维度，默认报价完全忽略它**：eco(7s)、across(1s)、polymer(10s) 三桥损耗差仅 1.3-2.3bps，但对短寿命机会，1s vs 900s 是生死之差。
3. **API 坑记录**：LI.FI quote 的 `prefer`/`bridges`/`slippage>1` 参数无效或报错；有效参数是 **`allowBridges` / `denyBridges`**（slippage 必须 ≤1）。费用字段 amount 是 raw 字符串，须按 token decimals + priceUSD 折算。
4. **对研究线**：跨链候选评估必须同时记录 `executionDuration`（时长假象）——与 Jupiter 侧 v2 加 slot 新鲜度维度是同一原则的两端实现。

## 打卡素材（Day 6）

「L0006 报价对比实验：Base→Arb USDC 三档×三桥 9 次报价。058/063 亲手复现（无规模折扣 25bps 恒定；快 6s 少拿 ~1bps）。新发现：across 桥 100k 档执行时长 1s→900s 暴涨 900 倍而报价不变——'时长假象'，报价必须带 executionDuration 维度才能判断可执行性。」

## 关联

- `notes/colearn-incremental-137-digest-20260810.md`（058/063/116 出处）
- `notes/lifi-crosschain-120-rounds-report.md`（自己 120 轮实测）/ `notes/lifi-cost-observation-methodology.md`（群友 142 次观测）
- `scripts/jupiter_route_monitor.py` v2（同原则的 Solana 侧实现：slot 新鲜度维度）
