# Priority fee / CU 监控上线（2026-08-09）

> 脚本：`scripts/priority_fee_monitor.py`（只读）+ cron `Priority fee监控(priority_fee)`（0698c1dd90a0，每小时 watchdog）
> 对应 notes/solana/README.md 研究线二阶段「数据：priority fee / 失败交易」

## 实现

- **数据源**：Helius RPC `getRecentPrioritizationFees`（无参 = 最近 20 区块，实测返回 150 条）
- **指标**：P50 / P99 / 均值 / 标准差（lamports）+ 每区块竞价上限（slot max）+ 历史 P99 分位
- **方法论**：沿用 infra_selfcheck——拒 Mean 看 P50/P99.9+std；历史分位 ≥0.8 = 竞价高位（与 funding basis 同规则）
- **watchdog**：P99 ≥ 0.01 lamports/CU（≈14K lamports）黄警，≥0.05 红警；静默模式只有异常才输出
- **落盘**：`data/priority_fee_history.csv`（每小时一条，攒 ≥20 条后分位生效）

## 首跑实测（2026-08-09 09:55 UTC）

- **150 区块 / 150 笔 fee 全部为 0 lamports**——周末凌晨，链上无套利竞争，所有交易都是普通 fee
- 这本身就是有效基线：**正常市场 Solana 执行成本（竞价）= 0**，Priority fee 是事件驱动成本
- 区块竞价 max = 1 lamports（个别交易给了 1 lamport 意思一下）

## 结论与意义

1. **Priority fee 是「事件驱动的执行成本」**：平时 0，套利/抢跑潮时飙升——与 CEX 手续费不同，它是**竞争强度仪表盘**
2. **对套利的意义**：
   - 平时做套利交易成本极低（fee 可忽略），门槛只在路径发现/模拟精度（呼应 note046 三论点）
   - 抢跑潮（高 P99 + 高标准差）时要避开直接竞价，或走 Jito bundle（小费而非 priority fee）
3. **与 Jito 衔接**：priority fee 高 = 区块空间竞价激烈，此时 Jito bundle 是替代通道（bundle 用小费，不参与 priority fee 竞价）——下一阶段做 Jito 研究时用此数据对照

## 下一步（Solana 线）

- [ ] Jito bundle / 小费研究（priority fee 高时 bundle 对比）
- [ ] 失败交易监控（getSignaturesForAddress 找 failed）
- [ ] Drift perp 数据（链上 funding/清算，与 CEX funding 对照）
- [ ] execution quality tracker（模拟 vs 实盘达成率）
