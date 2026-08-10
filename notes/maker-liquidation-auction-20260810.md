# Maker LIQ2.0 拍卖类套利调研（2026-08-10）

> Bruce 14 类对照表唯一 ❓ 空白候选（毛 2-15%、净 0.5-5%），与清算共用数据管道。
> 本文档 = 机制拆解 + 2026-08-10 链上实测 + 数据源清单 + 参与路径评估。
> 主类：拍卖（12）｜关联：清算（11）

## TL;DR（先说结论）

1. **系统还活着**：Maker→Sky 迁移后（2024-08 rebrand，USDS 替代 DAI），清算仍走 Dog→Clipper 荷兰式拍卖，架构未变。
2. **但机会极低频**：实测 ETH-A clipper 最近一次 Kick 在 **2026-06-05**，之后 65 天**零活动**；当前全系统 17 个 ilk 的活跃拍卖数全部为 0。
3. **⚠️ 文档坑**：旧文档（docs.makerdao.com）的事件签名已过时。2026 年链上实际是**新版 7 参数签名** `Kick(uint256 id, uint256 top, uint256 tab, uint256 lot, address usr, address kpr, uint256 coin)`（无 ilk bytes32），用旧签名过滤日志会得到 0 条。
4. **门槛低但竞争是「在场」问题**：参与只需要 gas（flash swap callee 模式），难点是监控覆盖率和清算触发及时性——与 Aave 清算同构，但拍卖是持续窗口（最长 tail），不是抢单，对个人更友好。

## 一、机制拆解（LIQ2.0 = 荷兰式拍卖 + 即时结算）

### 角色与合约

| 合约 | 作用 | 2026 实测地址（ETH-A） |
|---|---|---|
| `Dog` | 清算入口：`bark()` 检查抵押不足 → 没收抵押品 → 记坏账 → 调 `Clipper.kick()` | `0x135954d155898D42C90D2a57824C690e0c7BEf1B` |
| `Clipper` | 拍卖合约：`kick()` 开拍 / `take()` 购买 / `redo()` 重置 / `yank()` 撤销 | `0xc67963a226eddd77B91aD8c421630A1b0AdFF270` |
| `Abacus` | 价格曲线：当前价 = f(初始价 top, 已过时间) | `0x7d9f92DAa9254Bbd1f479DBE5058f74C2381A898` |
| `Vow` | 坏账/盈余记账，拍卖所得 DAI 去向 | — |

### 拍卖生命周期

1. **触发**：Vault 抵押率跌破清算线 → keeper 调 `Dog.bark(ilk, urn, kpr)` → `Clipper.kick(tab, lot, usr, kpr)` 开拍。
   - `tab` = 需筹集的 DAI（债务 + 稳定费 + 清算罚金 chop）
   - `lot` = 抵押品数量；`top` = 初始价 = OSM 价 × `buf`（实测 ETH-A buf=1.10，即 OSM 价 +10%）
2. **降价**：价格按曲线随时间下降（实测 ETH-A 用 StairstepExponentialDecrease，tau/tail=7200s）。
3. **购买**：任何人调 `take(id, amt, max, who, data)`。
   - `amt` = 想买多少（≤ lot）；`max` = 愿意付的最高单价（限价单语义）
   - 实际成交价 = min(当前拍卖价, max)；`owe = slice × price`，若 owe > tab 则缩量到刚好覆盖 tab
   - **关键设计**：`data` 非空时，`who` 合约会被回调（clipperCallee 模式）——即**无 DAI 也能拍**：keeper 用 DEX 把拍到的抵押品换成 DAI 付账，同一笔 tx 内完成（flash swap），只需 gas。
4. **重置**：价格跌超 `cusp`（实测 0.45，即跌到 top 的 45%）或超 `tail`（7200s）仍未拍完 → 需 `redo()` 重开（新 top = 当前 OSM 价 × buf），redo 也有激励。
5. **结束**：`tab` 筹满（多余抵押品退回 vault）或 `lot` 卖完，拍卖清除。

### Keeper 激励（谁付你钱）

- `tip` = 固定激励（实测 ETH-A **250 USDS**/次）
- `chip` = 比例激励 = tab × chip（实测 ETH-A chip=0.001 → 0.1%）
- 盈利大头实际来自**折价买抵押品**：chop（罚金）>0 时，拍卖价 ≤ 市价 × chop，拍下来转手即赚
- 注意：`bark`（触发清算）和 `take`（购买）是两种 keeper 动作，都有激励

### 与 Aave/Compound 清算的本质差异

| 维度 | Maker LIQ2.0 | Aave/Compound |
|---|---|---|
| 机制 | 荷兰式拍卖（价格随时间降） | 固定折扣抢单（FCFS） |
| 竞争 | 窗口期持续出价（最长 2h） | 秒级抢 `liquidate()` |
| 资本 | 零 DAI 可参与（flash callee） | 需自有稳定币 |
| 利润来源 | 折价 + tip/chip | 固定 bonus |
| 个人可行性 | 中（监控 + 价格判断） | 低（速度竞赛） |

## 二、2026-08-10 链上实测（证据）

RPC: ethereum.publicnode.com（代理 7890），cast + eth_call / blockscout API。

### 全 ilk 参数快照（Dog.ilks）

| ilk | clip | chop | hole(USDS) | active |
|---|---|---|---|---|
| ETH-A | 0xc67963a2... | 1.1300 | 40,000,000 | **0** |
| ETH-B | 0x71eb8943... | 1.1300 | 15,000,000 | 0 |
| ETH-C | 0xc2b12567... | 1.1300 | 35,000,000 | 0 |
| WBTC-A | 0x0227b54A... | 1.0000 | 10,000,000 | 0 |
| WSTETH-A | 0x49A33A28... | 1.1300 | 30,000,000 | 0 |
| RETH-A | 0x27CA5E52... | 1.0000 | 2,000,000 | 0 |
| USDC-A | 0x046b1A57... | 1.0000 | 20,000,000 | 0 |
| LINK-A | 0x832Dd5f1... | 1.0000 | 3,000,000 | 0 |
| UNI-A / AAVE-A / YFI-A / CRVV1ETHSTETH-A / GNO-A | ... | 1.0000 | 1-5M | 0 |
| RWA 系（RWA007-016） | 0x0（未配 clip） | — | — | — |

**结论**：全系统 17 个 ilk 全部 `dirt=0, count=0` → **当前无任何活跃拍卖**。RWA ilk 无 clip（走特殊清算路径，非 LIQ2.0）。

### ETH-A Clip 参数（2026-08-10 实测）

```
buf  = 1.10   (初始价 = OSM × 1.10)
tail = 7200s  (2 小时未拍完需 redo)
cusp = 0.45   (价格跌到 top 45% 需 redo)
chip = 0.001  (比例激励 = tab × 0.1%)
tip  = 250 USDS (固定激励)
calc = 0x7d9f92DAa9254Bbd1f479DBE5058f74C2381A898 (StairstepExponentialDecrease)
```

### 历史频率（ETH-A clip，blockscout 全量日志）

- 累计：**631 Kick + 861 Take**
- 最近活动：blk 25253425（Kick）→ blk 25253486（Take），**2026-06-05**，之后至今（08-10，约 65 天）**零活动**
- 上一波：2026-02 前后（blk 24.35-24.39M 区间）
- 2025 年：多波次（blk 22.2-23.9M）

**含义**：ETH-A 拍卖是**低频事件流**（几个月一波），不是持续机会。要做的是「在场」+「事件驱动」，不是高频扫描。

### ⚠️ 事件签名（实测，勿用旧文档）

```
新版 Kick: 0x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8
           Kick(uint256 id, uint256 top, uint256 tab, uint256 lot, address usr, address kpr, uint256 coin)
新版 Take: 0x05e309fd6ce72f2ab888a20056bb4210df08daed86f21f95053deb19964d86b1
           Take(uint256,uint256,uint256,uint256,uint256,uint256,address)
旧文档 Kick(bytes32 ilk, uint256 id, ...) → 链上已不用，勿用
```

## 三、数据源清单（监控要用的）

| 数据 | 来源 | 说明 |
|---|---|---|
| 活跃拍卖列表 | `Clipper.list()` / `count()` eth_call | 每 ilk 一个 clip，轮询即可 |
| 拍卖详情 | `Clipper.sales(id)` → pos/tab/lot/usr/tic/top | 价格曲线可从 calc 合约算 |
| 新拍卖事件 | eth_getLogs topic0=新 Kick 签名 | **实时性核心**：Kick 即信号 |
| 历史数据 | blockscout v2 `/addresses/{clip}/logs` | 免费无 archive 限制，可翻页 |
| 参数变化 | 治理事件 / docs.sky.money | buf/tail/cusp/chop 会变，监控需定期核 |
| 价格基准 | OSM 合约（比市价延迟 1-2h） | 计算折价率用，注意 lag |

## 四、参与路径评估（假设，未实盘）

### 假设：拍卖类适合个人

**支持**：
- 资本要求极低（flash callee 只需 gas）
- 不是速度竞赛（最长 2h 窗口，价格判断比手速重要）
- 低频 → 监控成本低（一个 cron 轮询 list() + logs 即可）
- 与已有清算哨兵共数据管道（liquidation_monitor.py 可扩展）

**风险/否定面（先讲风险）**：
- 低频 = 收入不稳定，可能几个月空转
- 折价率受竞争影响：拍的人多 → 成交价贴近市价，利润只剩 tip/chip
- ETH-A chop=1.13 意味着最多 13% 折价空间，但 OSM 价滞后 1-2h：**大跌时 OSM 价高于市价 → 名义折价是假象**（Black Thursday 教训：0 DAI 成交）
- 退出流动性：拍到的抵押品（ETH/WBTC）转手有滑点，算 net 要扣
- 系统性风险：清算可能被治理绕过（Dog 可被治理 bypass）、circuit breaker 4 档

### 净收益公式（对齐 132 门槛公式）

```
净利 = 折价收益(市价−成交价)×lot + tip + chip×tab − gas − 转手滑点 − 资金机会成本
门槛: expectedSurplus > gas + 失败摊派 + 机会成本 × 1.2 缓冲
```

### 与 Bruce 区间对照

Bruce 说毛 2-15%、净 0.5-5%——**在清算事件发生时才存在**。频率乘上去，年化取决于事件次数。

## 五、下一步（可执行）

1. [ ] **拍卖哨兵 v1**：cron 轮询 17 个 clip 的 `count()`，>0 即告警 + 拉 `sales()` 明细（复用 liquidation_monitor.py 结构）
2. [ ] Kick 事件实时监听（webhook 或高频轮询），事件驱动进群
3. [ ] 折价率计算器：市价（CEX/DEX）vs 拍卖当前价，算理论净利
4. [ ] 参数快照脚本：定期记录 buf/tail/cusp/chop/chip/tip，治理变更可追溯
5. [ ] 对照表补行：14 类总表「拍卖」从 ❓ → ⚠️（机制已验证，频率待观察）

## 关联

- Bruce 对照表：`notes/bruce-first-principles-arbitrage-20260810.md`（拍卖=空白候选）
- 清算论文：`notes/defi-liquidation-mev-papers-digest-20260810.md`（70% 无跳变 → 固定折扣）
- 门槛公式：`notes/execution-quality-tracker-20260809.md`
- 官方文档：https://docs.makerdao.com/smart-contract-modules/dog-and-clipper-detailed-documentation.md
- Keeper 参考实现：github.com/sky-ecosystem/auction-demo-keeper（已归档）/ auction-keeper（flip/flop/flap）
- 旧版黑天鹅：Black Thursday 0 DAI 清算（2020-03-12）
