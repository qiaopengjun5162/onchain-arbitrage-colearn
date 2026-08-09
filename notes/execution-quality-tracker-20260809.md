# Execution Quality Tracker 框架上线（2026-08-09）

> 脚本：`scripts/execution_quality_tracker.py`（四步框架）
> 对应 notes/solana/README.md 研究线四阶段「execution quality tracker」——roadmap 核心问题「Paper Trading 里哪些收益会在实盘中消失？」

## 框架（四步）

1. **quote**：Jupiter 报价 → 模拟期望价（`sim_price`）
2. **build**：solana-rs swap 构造 v0 交易 → dry-run 签名成功 = 可执行性
3. **execute**：`--send` 真实广播 → 链上成交价（待接入 getTransaction 解析）
4. **compare**：达成率 = exec_price / sim_price → 落 CSV（`data/execution_quality.csv`）

## 首跑实测（2026-08-09 10:13 UTC）

- 模拟报价：0.01 SOL → 0.7648 USDC（均价 76.4793，路由 BisonFi）
- 交易构造：✅ dry-run 签名成功（560 bytes v0 交易，可执行）
- 达成率结构就绪（实盘后回填）

## 意义

- **达成率是模拟→实盘的桥梁**：<1 = 滑点/竞争损耗；结合 failed_tx_monitor（60-73% 失败率）→ 真实期望收益 = 模拟 × 达成率 × 成功率
- roadmap 问题「哪些收益会在实盘中消失」的量化工具：每笔实盘记录达成率，积累分布后看 P50/P99 达成率（沿用拒 Mean 方法论）

## 待办

- [ ] --send 真实广播 + getTransaction 成交价解析（需真实钱包 SOL）
- [ ] 达成率历史分布（P50/P99.9，≥20 条生效）
