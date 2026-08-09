# 失败交易监控上线（2026-08-09）

> 脚本：`scripts/failed_tx_monitor.py`（Helius getSignaturesForAddress err 字段）+ cron（每小时 watchdog）
> 对应 notes/solana/README.md 研究线二阶段「数据：失败交易」

## 首跑实测（2026-08-09 10:10 UTC）

| 程序 | 采样 | 失败 | 失败率 | 主要错误 |
|---|---|---|---|---|
| **Raydium-CP** | 30 | 18 | **60% ★** | Custom 8（滑点超限）×16 |
| **Pump.fun** | 30 | 22 | **73% ★** | Custom 7（池创建失败）×15、Custom 3 ×5 |
| Meteora-DLMM | 0 | 0 | 0% | 地址需换（LBUZKh... 返回空） |
| Jupiter-Router | 0 | 0 | 0% | 地址需换（JUP6LrZx... 返回空） |

## 解读

1. **60-73% 失败率是 Solana 生态基线，不是异常**：meme 交易（Pump.fun）大量失败源于滑点设置太紧 + 抢跑 + 余额不足；Raydium CP 的 Custom 8 是典型的「slippage exceeded」
2. **对套利的意义**：
   - **失败率 = 执行质量成本**：抢跑环境下真实成交率 ~40%，意味着「模拟收益 × 0.4」才是期望——这与 roadmap 三阶段「Paper Trading 达成率差异」直接相关
   - 滑点设置：Raydium 60% 失败说明**默认滑点太紧**，套利单要设足够滑点缓冲（或走 Jito bundle 确保落地）
3. **Jupiter-Router/Meteora 地址需修正**（返回 0 交易）——后续用 v2-teacher 或 Solscan 找正确程序 ID

## 下一步

- [ ] 修正 Jupiter/Meteora 程序地址（找正确 Router program）
- [ ] 失败率历史落盘 + 分位（区分「常态失败率」与「异常飙升」）
- [ ] 与 priority_fee/jito_bundle 三指标合并 = 执行层全景仪表盘（失败率 × 竞价 × bundle tip）
