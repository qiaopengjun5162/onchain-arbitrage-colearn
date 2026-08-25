# 350ms slot 对 Jito 管线的影响评估（2026-08-25）— Solana 线 backlog 补做

> 背景：Solana 官方周报（08-23）宣布 slot time 降到 350ms（首次削减）；08-21 BAM 笔记已核验「功能标志 Epoch 1019 激活、Epoch 1020 生效」→ 主网已在 350ms 时序
> 触发：`notes/solana-weekly-20260823.md` 可执行项 `[ ] 350ms slot 对 Jito 管线的影响评估 → D20 主网迁移清单`（D20 被同块排序挤掉，本日补做）

## 一、实测确认（2026-08-25）

- `api.mainnet-beta.solana.com` getEpochInfo：**epoch=1022**，absoluteSlot=441,611,419
- 3 秒实测推进 10 slots ≈ **390ms/slot**（含 RPC 请求往返延迟，实际时序应在 350-400ms 区间）→ **350ms 时序已生效**（相对 400ms 时代 -12.5%）

## 二、变更链条（400ms → 350ms → 更快的下一步）

- 400ms（历史基准）→ **350ms**（当前，Agave 4.2 系列）→ 官方路线图指向 **200ms 时隙**（Agave 4.2 公告提及「迈向 200ms」）
- 配套变更：**BAM 拍卖 50ms → 35ms**（Epoch 1020 生效，已核验）；**Jito Block Engine 拍卖仍 50ms**（未变）

## 三、对 Jito 管线的影响（逐项）

| 管线组件 | 影响 | 判定 |
|---|---|---|
| `jito_bundle_pipeline.py`（Block Engine，tip 自动定价 99 分位） | Block Engine 拍卖 50ms 不变 → 提交流程**无需改动**；但每个 slot 时间预算 400→350ms，bundle 必须更快到达（延迟预算 -12.5%） | ⚠️ 微调不重构 |
| `jito_bundle_monitor.py`（bundle 落地监控） | 监控频率无需变；slot 变快 → 每秒事件更多，去重窗口要按 slot 数而非时间 | ⚠️ 去重逻辑检查 |
| `priority_fee_monitor.py` | 350ms 下 tip 竞价更紧凑，P99 tip 可能上移；当前数据 p50/p99=0（近期无套利流量，非时序影响） | 👀 持续观察 |
| `execution_quality.csv`（达成率/fill_rate） | 0.2404 fill_rate（10:00 快照）——350ms 时代达成率是核心 KPI，继续跟踪 | 👀 持续跟踪 |
| 雷达 v4 `no_arb_corridor_radar.py`（slot 快照绑定） | **已适配**：slot_a/slot_b/slot_now + blockhash8 绑定，同源腿 slot 差 >10 强制 suspect——350ms 下 slot 差阈值需重标（10 slots ≈ 3.5-4s，更敏感） | ⚠️ 阈值重标 |
| 同块套利 | 窗口 400→350ms = 每 slot 排序竞争时间 -12.5% → 更卷；排序权资本游戏结论不变 | ❌ 无新机会 |

## 四、延迟预算分解（350ms 下的时间线）

一个套利交易从发现到进块的预算（实测/文献值）：
- RPC 轮询/事件到达：100-200ms（公共 RPC）→ Flashblocks 类/私有 RPC 可到 50ms
- 模拟/报价：50-100ms
- bundle 构建 + 提交：50-100ms
- **合计 200-400ms ≥ 350ms slot** → 公共 RPC 路径在 350ms 时代基本无法稳定同块；私有 RPC + 预构建是前提（与 008 笔记「400ms 窗口内广播否则 slot 被跳过」一致，现在预算更紧）

## 五、对策（主网迁移清单的一部分）

1. **延迟预算重标**：350ms slot 下，目标 = 事件发现到提交 <250ms（预留 100ms 进块余量）；公共 RPC 轮询不够，需 WS 订阅 + 预构建
2. **tip 定价**：保持 P99×1.5 动态策略（D12 经验），但 99 分位窗口缩短到近 1-2 小时滚动（350ms 下竞争结构变化更快）
3. **雷达 slot 阈值**：`>10 slots` 的 suspect 线改为 `>8 slots`（10×0.35s vs 10×0.4s 的物理意义对齐）
4. **BAM 观察**：35ms 拍卖已生效；若未来 bundle 走 BAM（非 Block Engine），提交窗口 35ms——那是完全不同的执行形态（SEV-SNP 硬件、块内 N slot 均分 CU），暂不接入，保持观察
5. **数据源升级路径**：Helius WS（已有 key）→ 私有 RPC 预构建 → Flashblocks（Base 侧思路同样适用 Solana 的 200ms 未来时序）

## 六、结论

- 350ms 已生效（实测 ~390ms/slot），对现有管线**无破坏性影响**（Block Engine 50ms 拍卖未变）
- 真正的影响是**延迟预算 -12.5%**：公共 RPC 轮询路径在同块竞争里基本出局，私有 RPC + WS 订阅 + 预构建是 350ms（及未来 200ms）时代的入场券
- 与 D19 结论一致：个人 edge 不在同块速度竞争，350ms 只是进一步确认「速度型 MEV 是基础设施玩家的游戏」
