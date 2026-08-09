# Jupiter 路由变化监控上线（2026-08-09）

> 脚本：`scripts/jupiter_route_monitor.py`（routePlan 哈希对比 + 稳定确认）+ cron（每小时 watchdog）
> 对应 notes/solana/README.md 研究线二阶段「数据：路由变化」

## 实现

- 数据：api.jup.ag/swap/v1/quote（Metis 路由引擎）routePlan 标签序列 + outAmount → md5 签名
- **稳定确认**：新路由连续 2 次快照一致才算「变化」（防秒级跳变噪音）
- 状态存 `data/jupiter_route_state.json`，变化落 `data/jupiter_route_changes.csv`
- 修正踩坑：AMOUNT 是 1e9（1 SOL lamports）不是 1e6（曾输出 0.0765 USDC 假值）

## 首跑实测（2026-08-09 10:12 UTC）

- **4 秒内路由 3 跳**：Aquifer→Deriverse → BisonFi → Quantum（输出价 76.45-76.45 USDC 几乎不变）
- **核心发现：Jupiter 秒级跳变是常态**——Metis 引擎持续重路由（同价格下换最优路径）
- 稳定确认机制有效：跳变在观察期被抑制，连续 2 次一致才报

## 对套利的意义

1. **路由跳变 ≠ 套利机会**：秒级跳变只是引擎优化，不代表价差窗口
2. **稳定路由变化 = 市场结构信号**：连续 2h 以上同路由变化 → 池子流动性迁移/新池上线/费率调整——此时检查该路径的价差
3. **联动**：路由变化日志 + basis_arb_model 的 GOAT 类信号 = 判断「路由变化是否伴随价差打开」

## 下一步

- [ ] 与 solana_dex_spread_monitor 联动：路由变化时自动跑该路径价差
- [ ] 路由历史画像：主流路径分布（SOL→USDC 通常走哪些池）+ 跳变频率基线
