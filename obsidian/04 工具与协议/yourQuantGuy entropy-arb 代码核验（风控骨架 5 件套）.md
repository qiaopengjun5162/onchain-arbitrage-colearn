---
title: yourQuantGuy entropy-arb 代码核验（风控骨架 5 件套）
date: 2026-08-28
type: note
tags:
  - onchain-arbitrage
  - tool
---

# yourQuantGuy entropy-arb 代码核验（2026-08-28）

> 触发：群分享 https://x.com/yourQuantGuy/status/2092743173730628061（08-26 22:37 UTC，228 likes/23.3k views）
> 系列：08-26 预热帖（batch2 ⑥，已归档 `group-share-x-links-batch2-20260826.md`）承诺的「明天开源」正式落地
> 方法：GitHub API 核验 + 源码逐文件审读（engine.py 35KB 核心）
> 结论：**学习价值高（风控骨架可抄），不装不跑**（同币跨 DEX perp 价差在我们框架内无新意 + README 带返佣）

## 一、Repo 事实（GitHub API，2026-08-28）

- `your-quantguy/entropy-arb`：desc「Open-source two-venue perp arbitrage bot for entropy exchange」
- **MIT license** ✅（不是名不副实开源）｜ 80★ / 45 forks（创建 2 天）｜ Python，63KB，24 文件含 5 个测试文件
- 结构：`main.py` + `entropy_arb/{engine,book,feeds,config,recorder,dashboard,venue_hl,venue_lighter}.py` + `tools/analyze.py` + tests/
- 推文 4 个优化方向自述：多所大乱斗 / 动态价差阈值 / 滑点动态管理 / 低延迟

## 二、机制（README + engine.py 审读）

- 结构：**一条腿永远 Entropy**（Hyperliquid 上的 io builder dex），对冲腿 = Lighter 主网 / Lighter Robinhood 链 / trade.xyz（HL l2Book）——即「同币跨 HIP-3 类 DEX perp 价差」
- 信号：`premium_bps = (Entropy price / hedge price − 1) × 10000`，围绕 config 里手工标定的 `midline_bps` 上下带：
  - `premium ≥ midline+upper(+费用)` → SELL entropy / BUY hedge
  - `premium ≤ midline−lower(+费用)` → BUY entropy / SELL hedge
  - 全部走 **taker 实盘订单簿**（HL/Lighter 官方 WS），非页面价差
- **风控骨架（比推文自述的「最基础」扎实，逐项列出）**：
  1. per-direction **persistence arming**（连续确认才触发，防单 tick 假信号）
  2. per-venue **inventory ladder + position caps**（每腿库存阶梯 + 仓位上限，防单向堆仓）
  3. per-venue order budgets + **reactive rate-limit exclusion**（订单预算 + 触发式限流剔除）
  4. **net-delta hedging**（净敞口对冲）+ `_reconcile_positions` 周期链上对账
  5. **venue-outage pausing with probing**（交易所故障暂停 + 探测恢复）
- **数据驱动参数标定闭环**：`--record-only` 无需密钥即可双簿记录 → 1 分钟 CSV → `tools/analyze.py` 算出 midline/upper/lower 三数 → 填 config —— 与我们的 funding_viz「历史费率/基差 → 参数」同思路，但做成了标准闭环
- 密钥：`.env.example` 明确「切勿提交 .env」；HL 用 **agent 钱包**（最小权限）+ 主账户地址分离——安全姿势与库内铁律一致

## 三、与库内对照

| 点 | 库内互证 | 判定 |
|---|---|---|
| 同币跨 DEX perp 价差 | 08-26 batch3 ⑦ Chosmos110 Entropy↔Lighter SNDK 工具核验：同机制无新意 | ✅ 互证 |
| 阈值=手工标定+数据驱动 | 我们的 scanner+dual_mode（费率差/基差/稳定性） | 🟡 他们的 analyzer 闭环可借鉴 |
| persistence arming | 我们哨兵有稳定性门槛但无「连续 N tick 确认」 | 🟢 可抄进执行设计 |
| inventory ladder/venue pause | 我们无执行层（只读监控） | 🟢 实盘阶段直接抄 |
| 返佣引流 | README 三条 referral（Entropy tier4 100% 返佣 / Lighter RH / trade.xyz） | ⚠️ 引流成分存在，不点 |
| 开源质量 | MIT + tests/ + 双语文档 | ✅ 同类里罕见地规范 |

## 四、判定与可执行项

1. **不装不跑**：同币跨 DEX perp 价差在 21 天全地图里已定性（DEX 流动性/深度差 + 跨结算风险），且作者自己说「不要指望跑起来就能盈利」；要跑需真金 + 三所密钥，风险收益不成比例
2. **学习价值高**：engine.py 的风控骨架是我们目前只读监控集群缺的**执行层设计模板**——已提炼 5 个可复用件（persistence arming / inventory ladder / order budget+限流剔除 / 故障暂停+探测 / 链上对账），存证本文档，费率线或清算线进入实盘设计时直接引用
3. **生态观察**：Entropy（HL io builder）是币股 RWA 候补方向成员（Lighter 同生态 08-25/08-26 已观察）；HL 的 io builder dex 机制本身值得单独研究（新原语）
4. 返佣链接一律不点，走官方路径（库内规矩）

## 红旗

- README 三连 referral = 项目开源 + 返佣引流并存（预热帖已识别），但代码质量与文档规范性在同类里罕见地高，**内容可信度与引流意图分开判**
- 80★/2天 有 X 流量助推成分，不代表盈利验证
