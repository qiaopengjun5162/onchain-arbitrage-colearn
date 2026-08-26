# Morpho 套利机会发现与监测方案 digest（2026-08-14）

> 来源：用户提供 PDF `sources/morpho-arbitrage-discovery-monitoring-2026-08-14.pdf`（9 页中文报告，基于 0x82a206c9 案例）
> 定位：阶段 2（脚本/信号）设计蓝图——「同构猎物雷达」的实现路径解锁

## 核心不等式（检测公式）

```
套利窗口：oracle_price × LTV > spot_price
本例：1.064 × 0.915 = 0.973 > 0.686（窗口 +55%）

deviation  = |oracle_price − spot_price| / oracle_price
borrowable = oracle_price × ltv
gross      ≈ (borrowable − spot_price) × qty − swap_fees − borrow_fee
```

## 机会根因四要素（市场配置缺陷，非代码漏洞）

1. **固定快照预言机**：ChainlinkOracleV2 无实时喂价，2026-01-19 创建市场时写入后冻结
2. **抵押品去锚**：sNUSD 相对 $1 锚偏离 -31%（DEX 成交 $0.686）
3. **高 LTV 91.5%**：oracle×LTV = 0.973 仍高于市场价
4. **非官方市场**（listed=false）：调用者直接创建，无风控护栏
+ 闪贷放大：27.7M 零成本杠杆

## 三条发现路径（雷达的三种触发逻辑）

| 路径 | 逻辑 | 时效 |
|---|---|---|
| ① 系统性价差扫描 | 轮询 oracle.price() vs DEX 实时价/TWAP，偏差 >2-5% 进候选 | 机会成熟期 |
| ② 市场参数筛选（**埋雷期**） | 监听 MarketCreated：固定/NAV 预言机 + 高 LTV + 非官方 + 易去锚抵押品 → 提前标记，等价格崩塌自动成熟 | 最早 |
| ③ 稳定币去锚监控 | NUSD/sNUSD 偏离 $1 锚 -31% 触发 + 该资产在 Morpho 有预言机未更新市场 → 升级为候选 | 触发期 |

## L0-L3 分层监测（个人起步 L0+L1）

- **L0 手动看板**：Dune/Morpho 市场页/DefiLlama 去锚页（免费，分钟级）
- **L1 定时轮询脚本**：Python + Morpho API + RPC + Telegram/飞书 webhook（秒-分钟级，低门槛）← **我们的目标层**
- **L2 事件流实时**：Forta 代理/Substreams/The Graph（秒级，高门槛）
- **L3 预防加固**：验证预言机/LLTV 护栏/下线非官方市场（治理侧）

告警分级：偏差 >2% 记录 / >5% 即时通知 / >10% 立即通知+人工复核
误报控制：30 分钟 TWAP 过滤插针；剔除扣费后负收益；RPC 多节点轮换；告警去重+冷却

## 行为指纹（识别同类 bot）

nonce 108 机器人 EOA → Morpho Bundler + KyberSwap + Uniswap V4 → "MyAwesomeApp" client id → 闪贷+抵押+借款组合（Forta 已有类似代理）

## ✅ 关键验证：Morpho 官方 GraphQL API 可用（雷达数据源解锁）

- endpoint：`https://blue-api.morpho.org/graphql`（POST，Content-Type: application/json）
- 实测查询成功（2026-08-14 晚）：`markets(first, orderBy: SupplyAssetsUsd, orderDirection: Desc) { items { marketId listed lltv oracle{address} loanAsset collateralAsset state{utilization supplyAssetsUsd} } }`
- **首屏即扫到高危特征市场**：PAXG→USDC（lltv 91.5%，listed=false，util=1.0）、sdeUSD→USDC（91.5%，listed=false，util=1.0）、K→USDC（62.5%，listed=false，util=1.0）、BONDUSD→USR（94.5%，listed=false，util=1.0）——4 个利用率 100% 的非官方市场
- **绕开了 eth_getLogs 403**：全市场清单不再需要事件扫描（publicnode 禁 eth_getLogs），GraphQL 直接给 marketId 列表

## 雷达 v1 实现方案（更新版，替代昨晚受阻设计）

```
① GraphQL 拉全市场清单（listed/lltv/oracle/collateral/loan/utilization）→ 每 10-30min
② 过滤高危特征：listed=false + lltv≥90% + 抵押品为衍生/质押/4626 类 + utilization≥95%
③ 对候选市场：eth_call oracle.price()（publicnode）+ DEX spot 价（V4/V3 池 slot0 或价格 API）
④ deviation = |oracle−spot|/oracle > 5% → 落盘 data/prey_radar.jsonl + 告警
⑤ 告警分级 2%/5%/10% + 冷却期（报告模板）
```

## 风险提示（报告原文保留）

- 被动监测是秒级，专业搜索者是毫秒级 mempool 竞争——监测价值=知道机会存在+提前布局，不是每次抢先
- 自动执行高风险（MEV 三明治/清算/合规），研究期只做被动监测

## 关联

- `notes/morpho-flashloan-vault-snusd-arb-case-20260813.md`（案例笔记）
- `notes/from-research-to-production-roadmap-20260814.md`（五阶段管线：本 digest = 阶段 2 蓝图）
- `scripts/`（雷达脚本待建：prey_radar.py）

## 追加：窗口复盘（第二份 PDF，sources/morpho-snusd-arbitrage-window-report-2026-08-14.pdf）

### 生命周期实证（8/13 12:02 → 8/14 03:51，约 16 小时）
- 首笔借款 12:02:11（偏离仅 -2%，抢跑）→ 13:48 新池 P5 以 $0.7209 初始化（最早可确认破 5% 线）→ **14:02-15:02 爆发 159 笔（78%），1 小时借空** → 15:02-17:02 价格回稳 $0.88-0.96 → 8/14 00:02-04:00 二次下探 $0.26-0.34 → 03:51 最后一笔
- 全窗口：203 笔 / 33 地址 / 毛借出 90.7 万 USDC

### 当前状态（8/14 复核）：名义存在、实际冻结
- 预言机 $1.06387 未更新；市场价 $0.203（-81%！）；理论利差 4.8 倍
- **利用率 100%，可借余额 0** → 新套利者无法进场（除非有人存入/归还）
- 预言机一旦更新 → 0.915 仓位资不抵债 → 清算连环（后来者彻底失去前提）

### 雷达参数校准（实证）
- 5% 偏离线 = oracle×0.95（报告独立验证与我们阈值一致）；**抢跑者在 -2% 进场 → 信息级告警阈值降到 2%**
- **新池初始化价 = 可执行触发点**（深跌池批量出现=买入路径成立）→ 雷达第三信号
- 利用率 100% = 执行冻结信号（第二信号实证：159 笔借空后通道关闭）
- 方法论可复用：Swap 事件 sqrtPriceX96 解码 + Borrow 事件逐块扫描 + 时间戳对齐；公共 RPC 10k 块/请求上限限制（12:02-13:48 无法完整枚举→"可确认观测+行为推断"口径）
