---
title: prey radar v2 高频偏离轮询原型
date: 2026-08-26
type: note
tags:
  - onchain-arbitrage
  - tool
---

# prey radar v2：高频偏离轮询原型（2026-08-26 结营后清算事件线第一步）

> 脚本：`scripts/morpho_prey_radar_v2.py` ｜ 数据：`data/prey_radar_v2.jsonl`（降采样）+ `prey_radar_v2_state.json`
> 触发：D21 总结「下一步主攻方向 #1 清算事件线」→ 08-25 daily 信号链修正（不监听预言机交易，改高频轮询偏离）
> 关联：`[[猎物雷达 v1（预言机偏离哨兵）]]`（v1 全市场 30min 扫描）、`notes/solana/350ms-slot-jito-impact-20260825.md`、`[[Morpho HF 清算触发扫描器]]`

## 一、为什么做（v1 的瓶颈实测）

v1 是 30min cron 全市场扫描（200 市场串行 eth_call + DeFiLlama）。实测跑一次 **>180s 超时**（200 市场 × ~3.6s/市场串行 ≈ 720s）——30min 粒度对清算窗口毫无意义（预言机更新到清算是秒~分钟级）。高频化必须先解决单轮耗时。

## 二、怎么做（四个关键实测发现）

1. **JSON-RPC 批量 eth_call 可用**（publicnode，实测 2.2s/批）——1 次请求拿全部 watchlist 的 oracle price()。⚠️ 之前误判「不支持批量」是因为拿代币地址调 price() 会 revert（返回 result=None），不是批量问题
2. **DeFiLlama 批量多币种可用但 >10 币单请求返回空**（实测 9 币 1.9s 正常，13 币空）→ 分块 ≤8/请求
3. **⚠️ checksum 地址坑**：DeFiLlama key 全小写，GraphQL 是 checksum 地址——不统一小写全 cache miss（WETH 因天然全小写侥幸命中，一度误导排查）
4. 缩放档自动探测沿用 v1（候选 [18,20,24,30,33,34,36,37,42,45]，对现货 <10% 吻合），WETH 比值预言机兜底

**架构**：watchlist（GraphQL top-N 活跃市场，默认 12）→ 每 tick = 1 次批量 RPC（全部 oracle）+ 1 次批量 DeFiLlama（全部现货，SPOT_TTL 5s 缓存）→ 有效节奏 ≈ RPC 往返 ≈ **2-3s**（公共 RPC 极限；Flashblocks WS 到位后才 <200ms）

**信号链**：`dev_bps = (oracle_usd − spot) / oracle_usd × 1e4`，**正值 = oracle 高估 = 危险方向**（下修 → 抵押品贬值 → 清算窗口）。偏离突变（单 tick Δ≥20bps）= 现货动了预言机没跟 = 预言机即将更新。oracle raw 变化 = 预言机刚更新（联动 HF scanner 接手）。

**日志降采样**：oracle 更新 / |Δdev|≥1bps / level 变化 / 60s 心跳才落盘——1s×12 市场全量 540 条/45s → 实测 **22 条**（降 96%）。

## 三、结果（2026-08-26 实测）

**单次快照**（12 市场，9.7s 含启动 GraphQL）：

| 抵押品 | 借出 | 偏离bps | oracle$ | spot$ | 级别 |
|---|---|---|---|---|---|
| cbDOGE | USDC | +24.2 | 0.09 | 0.09 | ok |
| wstETH | WETH | +14.4 | 3,058.22 | 3,053.81 | ok |
| cbETH | WETH | +13.8 | 2,800.81 | 2,796.94 | ok |
| cbETH | USDC | +4.4 | 2,798.16 | 2,796.94 | ok |
| USDe | USDC | +2.8 | 1.00 | 1.00 | ok |
| SOL | USDC | +2.0 | 96.92 | 96.90 | ok |
| cbBTC | USDC | −2.1 | 78,906.32 | 78,922.55 | ok |
| WETH | USDC | −7.8 | 2,459.42 | 2,461.34 | ok |
| cbXRP | USDC | −38.9 | 1.43 | 1.44 | ok |
| mGLO | USDC | −638.3 | 0.94 | 1.00 | ok（v1 同款，oracle 落后偏安全） |
| cbBTC | EURC | — | — | 78,922.55 | scale?（EUR 报价预言机，见限制） |

- 11/12 解析成功，与 v1 结论一致（mGLO oracle 落后 6.4% 偏安全）
- 活跃市场全部 ok（偏离 <25bps 且多数 <15bps）——**当前无埋雷**
- cbDOGE/wstETH/cbETH 微正偏离 = oracle 略高于现货，方向危险但量级可忽略

**45s 高频实测**（--duration 45 --watch 12 --quiet）：
- 22 条降采样记录（vs 全量 540），安静期偏离漂移仅 **−1.7~+1.7bps**/tick，零误报
- 有效节奏 ~2.2-2.5s/tick（RPC 批量往返）

## 四、已知限制（原型诚实清单）

1. ~~cbBTC→EURC 类 EUR 报价预言机未解析~~ **已修复（08-26）**：loan 现货交叉转换，12/12 全解析
2. 节奏受公共 RPC 往返限制（2-3s），非真 1s——Flashblocks WS 逐桶流是执行前置
3. DeFiLlama 现货有 ~1.9s 延迟 + 5s 缓存——极端闪崩时 spot 采样滞后 ~5-7s（比 30min 好 400 倍，仍非实时）
4. 未接 HF scanner 联动（检测到偏离/更新后应自动触发持仓级 HF 计算）

## 五、下一步（清算事件线）

- [x] 挂 cron：`7954368ea467` 每 15 分钟跑 9 分钟窗口（--duration 540 --quiet），19:15 首跑 status ok 无报警（安静期契约正确）
- [ ] Flashblocks WS 端点（Chainstack 类）→ 真 <200ms 节奏 + 预言机更新逐桶流
- [x] **EUR 报价预言机交叉汇率处理（2026-08-26 晚完成）**：resolve 加 loan_usd 交叉转换（spot_loan=spot/loan_usd 探测 → oracle_usd=raw/10^s×loan_usd）；实测 cbBTC→EURC 从 scale? → -1.5bps，与 cbBTC→USDC 市场完全一致（交叉正确性验证）→ **12/12 市场全解析**
- [x] **联动 `morpho_liquidation_hf.py`（2026-08-29 完成）**：新增 `scripts/prey_hf_trigger.py`——读 v2 jsonl 尾部信号
      （JUMP/SIGNAL/ORACLE_UPDATE/BROKEN_ORACLE）→ 立即触发持仓级 HF 扫描（import morpho_liquidation_hf.scan 复用）
      → 输出「信号 + 谁 HF 最低 + 触发跌幅」；独立进程事件驱动零开销；跨进程去重 10min/信号；watchdog 契约（无信号静默）
      cron `44acb25fa67a` 每 2 分钟（比 30min HF cron 快 15 倍响应）。实测：watchdog 静默 ✅；全量 HF 快照发现
      USDe→USDC 贴线大仓（HF 1.006 起、触发跌幅 0.57%-1.93%，含 $49.32M 仓）
- [x] **v1 旧雷达退役（2026-08-29）**：`morpho_prey_radar.py` 符号 bug（偏离用绝对值 → mGLO 型「oracle 低估偏安全」误报 SIGNAL）
      + 无 EUR 交叉 → 停 cron `6c9d49f28ba7`；v2 `--include-broken` 补位（加「有资金」过滤 + marketId 去重，watch 脚本已更新）。
      实测 --include-broken：**24 个 HERMES 市场 listed=False 但 supply≈$55M×19+$11M×5+$98M 全 util=100%、
      oracle 冻结（BROKEN_ORACLE）≈$1.2B+ 借款困在 frozen 市场 = 清算连环弹药库**（24h 去重报一次）
- [ ] 攒 24h 高频数据后：统计偏离分布基线（正常漂移 vs 突变阈值校准，20bps/tick 是否合理）
