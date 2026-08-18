# 资金费率监控平台清单 × Auto-Prediction AI 语义套利 Harness（2026-08-18）

> 来源：群友/用户分享 X 链接 2 条（2026-08-18），Hermes 事实验证后归档
> 归档日期：2026-08-18
> 关联：`icl-incremental-notes-digest-20260817.md`（057 资金费筛选判据）、`funding-rate-signal-engineering-20260808.md`、`pm-rebalancing-scanner`（PM 研究线）

## 一、5 家资金费率套利监控平台（@WY_mask，2026-08-17）

链接：https://x.com/WY_mask/status/2089474853317603339

| # | 平台 | 宣称 | 存活验证 | 备注 |
|---|---|---|---|---|
| 1 | Loris Tools (loris.tools) | 专门做资金费率套利扫描器，实时覆盖广、可筛选 | ✅ 200，HTML 含 API//docs/Funding Arbitrage Scanner | 有 API 入口，值得进一步探测 |
| 2 | CoinGlass | 常用、中文友好、基础免费 | ✅ 200 | 业界标准站，已熟知 |
| 3 | Sharpe (sharpe.ai/funding-rates) | 免注册、33 家交易所、年化 APR 归一化、币×所热力图、单币跨所对比 | ✅ 200，HTML 含 API/api-keys/Free/Pro/Heatmap | 归一化口径是它的卖点（与 057「短窗口骗人」呼应） |
| 4 | PerpFinder | 实时监控+套利价差+热力图+持仓量 | ✅ 200，HTML 含 API Docs/Free/Funding Heatmap，明确标注 rates 归一化到 1 小时 | 显示 OI = 直接支持 062 OI 过滤判据 |
| 5 | CoinBeacon | 排行榜（最高/最低）、归一化 8h、警报 | ✅ 200 | 归一化 8h 口径与主流 CEX 结算一致 |

**验证结论**：5 家全部存活（curl 实测 200）。这是「工具清单类」分享，无收益 claim，不涉及 gross/net 核验。价值 = 比自建监控更快的交叉验证源 + 归一化口径差异教学（PerpFinder 1h / CoinBeacon 8h / Sharpe APR——**口径不统一时对比即错误**，与 057 短窗口陷阱同族）。

**对我们研究线的意义**：
- funding 信号层（`funding-rate-signal-engineering`）可把 Sharpe/PerpFinder 当**独立第二数据源**交叉验证自建脚本（避免单一来源系统性偏差）
- PerpFinder 同屏显示 OI = 062「OI 过滤」判据的现成工具化
- 无新策略增量；是工具补强不是新线索

## 二、Auto-Prediction：AI-native 语义套利研究 Harness（@0xcherry 车厘子，2026-08-17）

链接：https://x.com/0xcherry/status/2089351523117715906
GitHub：https://github.com/TraderAlice/Auto-Prediction

### 事实验证（2026-08-18 Hermes 实测）
- ✅ 仓库真实：created 2026-08-17，8 stars / 2 forks，TypeScript，730 文件，pre-alpha
- ✅ README 完整（Concepts/Architecture/Operations/CLI 文档齐全）
- ✅ 安全边界明确：「Live orders, transaction signing, token approvals, credentials for production trading, and movement of funds are disabled and out of scope」——**禁实盘**，纯研究 harness
- ✅ 非货币字段全用 bigint 定点（money/prices/fees/payouts 不用 JS number）；未知精度/stale book/不完整 payout partition 一律 fail closed
- ⚠️ license 字段 None（GitHub API 未检出 license）——引用/复用时注意
- ⚠️ 无收益 claim（README 明示 pre-alpha），符合「开源可审计」过滤器第一道

### 核心思路（可偷的干货）
把预测市场报价当作「**某个交易场所定义的结算合约的交易估值**」，而非世界真实概率。Agent 在事件空间里做启发式搜索找关系：
- 两个措辞不同但结算同一世界事件的合约
- 一个事件蕴含/抑制/部分排除另一个
- 若干合约在特定前提下构成 partition
- 同一世界被不同场所用不同规则/窗口/oracle 观察

管线：匿名场所证据 → content-addressed 市场语料 → Agent 探索与本体实验 → 持久化假设与反例 → 独立语义审查 → 确定性 payoff 编译 → bigint 市场模拟 → 精确验证 → **shadow-only 观察**（永远不接实盘）。

### 对照我们 PM 研究线
- **「语义套利」= 我们 `pm-probabilistic-forest-arb-paper` 的 LLM 找依赖市场对 + Polymarket rebalancing 扫描器（YES/NO 镜像）的上游抽象**：我们做的是「同义不同词合约价差」的具体子集，它做的是完整的事件空间关系图谱——方向一致，它是框架级、我们是落地级
- 它的「settlement contract ≠ world probability」本体论切分 = 我们 PM 结算规则风险（天气市场 TWAP 结算教训）的理论化
- 不打算直接用（pre-alpha + 无 license + 我们已有自己的 PM 栈），但 docs/CONCEPTS.md + PLANS.md 值得读一遍当方法论参照

## 归档
- links.md 已各追加 1 行（2026-08-18）
