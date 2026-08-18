# D14 第二周总结：AMM 数学 → 模拟器 → Jito pipeline（2026-08-18）

> 主线：第 2 周（D8-D14）收尾总结，对照 21 天产出总表自查
> 关联：`personal-learning-plan-v2.md`（D14 行）、`week2-breadth-review-20260816.md`（D12 广度回顾）、`from-research-to-production-roadmap-20260814.md`（五阶段管线）
> 自查结论：**监控脚本 ✓ / 模拟器 ✓ / Jito pipeline 半完成（mainnet 闭环跑通，套利逻辑已接、待实盘纪律）**

## 一、本周产出盘点（对照 21 天产出总表）

| 总表项 | 状态 | 证据 |
|---|---|---|
| 监控脚本 | ✅ 完成 | `scripts/multi_chain_spread_monitor.py`（DOS 搬砖）、`no_arb_corridor_radar.py`（无套利带 v2）、`backrun_thin_pool_scanner.py`（容量边界）、`whale_dump_radar.py`、`maker_clipper_sentinel.py` + `auction_sentinel.py`、`jito_bundle_monitor.py`、`evidence_harvester.py`（36 哨兵 cron） |
| AMM 数学（D8-D9） | ✅ 完成 | `notes/amm-math-v2-preview-20260811.md`（x*y=k 精确复现误差 0、费率反推 0.30%）、`scripts/amm_v2_verify.py`、`scripts/amm_clmm_visualize.py`（CLMM tick/区间可视化） |
| 利润模拟器（D10） | ✅ 完成 | `scripts/arb_profit_simulator.py`（V2 带费 swap 精确解、4 类路径、净利 bps 判定） |
| Jito bundle（D11-D13） | 🟡 半完成 | mainnet 首笔落地（`jito-bundle-mainnet-first-land-20260815.md`，8 轮排查→0.005 SOL tip confirmed）+ swap bundle 落地（`jito-swap-bundle-first-land-20260816.md`）+ `jito_arb_pipeline.py`（发现→判定→Jupiter quote→bundle 全链路，chainId 过滤修复后 9 路径全负=正确输出） |
| 广度五方向（D8-D12） | ✅ 完成 | `week2-breadth-review-20260816.md`：排序层=放弃 / perp funding=观察窗 / 聚合器=工具 / LP 动态调区间=唯一实测（动态>死守>持有，仅下跌月赢） |
| 增量笔记消化（D13-D14） | ✅ 完成 | 90 篇 + 91 篇两批 digest（`icl-incremental-notes-digest-20260816/17.md`），本批五强：RWA 基差 / 资金费短窗口 / Monad gasLimit / 测量自我污染 / 原子性≠执行权 |
| 实盘发布（D11-D12） | ✅ 完成 | 公众号 D1-D12 + X thread D1-D12 双平台收官（含 D11 首笔实弹交易复盘、D12 bundle 管线自动定价） |

## 二、周认知主线（本周验证了什么 / 否定了什么）

1. **验证：常驻结构性价差被磨平，肉在事件窗口/机制错位**（D12 广度横切结论 + D14 增量 digest 双重确认）
   - 模拟器跑通后的真实结果：主流池路径 9 条全负、无套利带 60bps 走廊内全配对正常态
   - 事件型证据：TUT 核爆一小时 13.5% 价差、充提状态套利（Deposit Disabled→内部溢价 5%）、周末杠杆 ETF 偏离（SNXX +165-181bps 常态）
2. **验证：成本模型是生死线，且要按链定制**——Monad gasLimit 不退回（052）、Backpack taker 100ms 减速带（057）、Quoter 幻觉率 99.5%（007+037 双证）、25bps 平台费是 gas 的 81 倍（022）
3. **否定/修正：测量自指污染**——「速度溢价 51bps」= 自己填的滑点被 toAmountMin 读回（滑点指纹 11/31/51bps），修正后 ≈1.0-1.1bps；**「一致到小数点后一位」恰恰证明没在测市场**
4. **新认知：原子性≠执行权**——bundle 保证顺序和全有或全无，不保证抢到；竞价让渡 95% 后 0.8 ETH 剩 0.04；expected_net = P(纳入)×landed_net − 基建成本
5. **升级：币股线 → RWA 基差套利**——Tokenized Stock × HL HIP-3 框架（log(P/X)=log(P/O)+log(O/X)、周末价格发现权争夺、机会存在置信度 90%）取代单纯「闭市漂移」视角；与证据台账 RWA/币股候选（10/30d、dev_bps_median 65.5bps、98% 超 30bps）互证

## 三、Jito pipeline 半完成的缺口（D15-D19 调整依据）

已完成：mainnet 首笔 bundle（encoding + tip 下限两坑解决）、swap bundle 落地、管线 dry-run 跑通（发现→判定→自动接 Jupiter quote→bundle，chainId 过滤修复）
未完成（列入 D15-D19）：
- [ ] **真实正利润路径触发**：目前 0 信号是正确输出（主流池磨平），需把扫描范围扩到事件窗口/新池（接 evidence-tracker 候选）
- [ ] **--execute 实盘纪律**：需人工确认 + 最小资金护栏 + 失败分类日志（revert/bid too low/conflict/late 分类，032 模型）
- [ ] **funding 监控补两列**：短窗口 vs 长窗口对比（057）+ 名单换手率 ≤50%
- [ ] **成本模型模板加 gas 语义检查**（052 Monad 教训，D15 pipeline 整合前必须）
- [ ] **RWA 基差数据抓取**（币股线升级分支：xStock DEX 报价 + HL funding 免 key，跑 2 周基线）

## 四、D15-D19 节奏调整

| Day | 原计划 | 调整 |
|---|---|---|
| D15 | Pipeline 整合 1 | 不变，但加「gas 语义检查」前置步骤 |
| D16 | Pipeline 整合 2 + 延迟日志 | 加失败分类日志（032 的 5 类负样本） |
| D17 | 历史机会回测 | 不变（Dune dex.trades + prices.hour 底座已就绪，084） |
| D18 | 回测报告 | 不变 |
| D19 | 4 方向对比表 v1 | 币股方向升级为「RWA 基差套利」（083 框架），非单纯时钟差 |

## 五、打卡闭环

- daily/2026-08-18.md（D14 主线 digest + 追加归档）
- ICL 打卡 2026-08-18 已提交（POST 201 验证通过）；**08-16 缺卡**（API 不支持补昨天的卡，只能算 leave day 或网站手动补，待用户定）
