# Jito bundle 监控上线：MEV 活跃度实证（2026-08-09）

> 脚本：`scripts/jito_bundle_monitor.py`（只读）+ cron（每小时 watchdog）
> 数据源：`bundles.jito.wtf/api/v1/bundles/recent`（公开，走代理可用）

## 首跑实测（2026-08-09 10:00 UTC）

| 指标 | 值 |
|---|---|
| 待处理 bundle | 100（全部带 tip） |
| 含交易数 | 120 |
| P50 tip | 9,961 lamports（~0.00001 SOL） |
| **P99 tip** | **2,020,000 lamports（0.002 SOL）** |
| 均值/标准差 | 74,100 / 285,769（高离散） |

## 🎯 核心发现：与 priority fee 通道的对照

- **Priority fee 通道：0 竞价**（同刻 150 区块全 0）——普通交易通道无人竞争
- **Jito bundle 通道：P99 tip 0.002 SOL，100% bundle 带 tip**——MEV 持续活跃

**实证结论：Solana 上的套利/抢跑竞争几乎全部走 Jito bundle 通道，不走普通 priority fee 通道。** 即使周末凌晨，bundle 通道持续有 MEV 活动。这直接实证了 note046 三论点「Solana 毫秒级链窗口，拼 Jito bundle + 节点位置」——**bundle 是套利的默认通道，priority fee 只是散户/常规交易的成本**。

## 意义

1. **执行层竞争全景**：普通通道（priority fee）≈ 0 + bundle 通道（tip）> 0 = 「套利者用 Jito，散户用普通交易」的分层
2. **对套利执行的意义**：如果做 Solana 套利，**必须走 Jito bundle**（否则即使发现机会也抢不过 bundle）；tip 是成本，P99 tip 是极端行情成本
3. **数据积累**：`data/jito_bundle_history.csv` 每小时一条，攒 ≥20 条后可看分位趋势（与 priority_fee_history 对照）

## 下一步

- [ ] tip 与 priority fee 双通道对照看趋势（两个 CSV 合并分析）
- [ ] bundle landed 率（recent 只有待处理；需要 block engine 的 bundle status API）
- [ ] Drift perp 数据（链上 funding，与 CEX funding 对照）——HTTP API 探测失败，走链上读取
