# Morpho 闪贷灌金库 + sNUSD oracle/DEX 价差套利实战案例（2026-08-13）

> 来源：Paxon 群内分享（Etherscan tx 分析请求）
> 链：Ethereum 主网
> 交易：`0x82a206c9dff00bf7b205987bdcd9384c06c6d9962aa929c84ab45dd0330c4e72`（block 25747425）

## 一句话结论

bot 用 **Morpho Blue 免息闪电贷 $27.7M** 灌进 Lulo USDC 金库触发分配器自动部署，顺手在无人问津的 Uniswap V4 池子里以 **35% 折价（$0.686）** 扫走 1,034.6 sNUSD，抵押进 Morpho 市场按 oracle 公允价（$1.0638）**满额 91.5% LTV 借出 $1,006.94**——一鱼两吃的**一次性 oracle/DEX 价差套利**，单笔净赚 ≈ **$297**（gas 仅 $0.87）。

## 交易画像（blockscout v2 API + 公共 RPC 实测）

- **时间**：2026-08-13 16:54:11 UTC（北京 08-14 00:54）
- **发起**：`0x343De4Fe545E0BdE879A96500700800720f7af32`（EOA bot）
- **目标**：`0xFBC74F4A2b603715c8b4368Be062157EA536142d`（**Lulo USDC 金库 wrapper**，铸造 luloUSDC 份额，自定义函数 `0x02393416` 未解码）
- **内部创建**：`0xeBf74C12319FC28251Ce7f7AaC5e8c877509705E`（**CalldataChunk**，本 tx 专属头寸载体，Morpho setAuthorization 授权给 wrapper）
- **status**: ok；gas 1,740,574；费 **0.000227 ETH（130 gwei，≈$0.87）**

## 参与方

| 地址 | 角色 | 备注 |
|---|---|---|
| 0x343De4Fe… | 调用者 EOA | bot |
| 0xFBC74F4A… | Lulo USDC 金库 wrapper | 自定义闪贷-灌金库函数，收 $166.67 利润 |
| 0xf29ce940… | 底层 MetaMorphoV1_1 金库 | 份额=luloUSDC；分配器在此 |
| 0xBBBBBbbB…EEFFCb | **Morpho Blue** | 闪电贷来源（0 费）+ 3 个市场 |
| 0xeBf74C12… | CalldataChunk | 新建合约，持有 sNUSD 抵押 + 借款头寸 |
| 0x6131B5fa… | Paraswap MetaAggregationRouterV2 | sNUSD 买入路由 |
| 0x8F10B468… | V4 PoolManager 执行 | 2 个近空 V4 池 |

## 路径还原（token 流，USDC 6 位小数 / sNUSD 18 位）

```
① Morpho Blue 闪贷 USDC        +$27,722,557.78（还款额=借款额 → 0 费用）
② 存入 MetaMorpho 金库          -$27,720,847.84 → 分配器部署到 3 市场：
   m1 PT-reUSD-25JUN2026  $9,958,751.78 ｜ m2 sNUSD/USDC $8,340,464.53 ｜ m3 siUSD $9,421,631.53
   （三市场均 loan=USDC、LLTV 91.5%、MorphoChainlinkOracleV2）
③ Paraswap → 2 个 V4 高费池（fee 19.9% / 4.95%，近空池）：
   -$709.93 USDC → +1,034.6 sNUSD（实价 $0.6862/枚）
④ SupplyCollateral 1,034.6 sNUSD（onBehalf=CalldataChunk）→ m2
   + SupplyCollateral $1,000 USDC（onBehalf=金库，自留头寸）
   → Borrow $1,006.94 USDC（onBehalf=CalldataChunk, receiver=wrapper）
   = 卡在 91.5% 满额 LTV：1034.6 × 1.0638 × 0.915 = 1,007.07 ≥ 1,006.94
⑤ 撤出金库全部（含 m3 历史遗留 $876.59 一并回收）→ 还清闪贷（分毫不差）
⑥ 余额 $166.67 打回 bot EOA
```

## 手续费结构（Paxon 惯例：不看赚多少，看成本）

| 项 | 金额 | 说明 |
|---|---|---|
| 闪电贷费 | **$0** | Morpho Blue flashLoan 0 费，还款=借款精确相等 |
| V4 池 fee | ~$0.13 | 19.9%+4.95% × 交易额极小（$0.65/$0.057），绝对成本可忽略 |
| 借款利息 | $1,006.94 @ **~105% APR** | m2 当时利用率打满，AdaptiveCurveIrm avgBorrowRate=105.1%（rateAtTarget 26.3%）；仓位不快速平掉利息会吃掉权益 |
| Gas | **$0.87** | 1.74M gas @ 130 gwei |
| **净利** | **≈ +$297** | = 借出 1,006.94 − 买入 709.93 − gas 0.87；另有 ~$93.7 权益留在 CalldataChunk 头寸 |

## 核心 alpha：oracle 与 DEX 的 55% 价差

- **oracle 报价**：m2 市场 oracle = MorphoChainlinkOracleV2（**vault 模式**：BASE_FEED 全 0，BASE_VAULT=sNUSD 自身，读其兑换率）→ `price()` = 1.0638e24 / SCALE 1e6 = **$1.0638/sNUSD**（与 blockscout 汇率 $1.054 同量级=公允价）
- **DEX 实价**：$0.6862（两个近空 V4 高费池，初始价离谱且无人搬平）
- **玩法**：折价买入 → 按公允价抵押 → 满额借出 = 每枚 sNUSD 白赚 $0.377
- **本质**：低流动性错价捡漏（池子里躺着 $700 的 sNUSD 标错价没人管），不是可持续常驻策略——池子被搬平即失效

## 为什么能成立（机制要点）

1. **闪贷 0 费 + 原子执行**：Morpho Blue flashLoan 免息，整笔一个区块内闭环，失败即回滚
2. **金库分配器当杠杆支点**：闪贷注入 → MetaMorpho allocator 自动把 $27.7M 铺进 3 个市场（这正是「今年早些时候出现过」的思路：用别人的分配机制完成资本部署）
3. **新建 CalldataChunk 隔离头寸**：每笔 tx 新建一个头寸载体合约，抵押+借款挂在它名下，后续可单独平仓/被清算，不污染主合约
4. **借到顶格 LTV**：1,006.94 / 1,007.07 = 99.99% 上限，一分不浪费

## 风险与可复现性

- **错价池不可再生**：同款 $0.686 的 sNUSD 池被搬平后无肉可吃；扫 V4 近空池要盯「高 fee + 低流动性 + 价格偏离公允价」三元组
- **借款利率是计时炸弹**：105% APR 下仓位必须当周内平（还款+赎回 sNUSD 或等清算）
- **oracle 模式可被仿制**：vault 模式 oracle（读自身兑换率）给了「DEX 价 vs 协议价」套利的新一类目标——凡是新上线的稳定币/生息代币 + vault 模式 oracle + 近空池，都是同构猎物
- **可复制骨架**：闪贷灌金库触发 allocator → 借错价抵押品 → 满额借出 → 还闪贷，这一套可以套用到任何「oracle 公允 > DEX 实价」的资产上

## 取证方法论沉淀（本次新动作）

- blockscout v2 三件套照旧：token-transfers 画主干 / logs 认池子 / addresses 画像
- **新增：Morpho Blue `idToMarketParams(bytes32)`**（selector `0x2c3c9157`）eth_call 直读市场四要素（loan/collateral/oracle/irm/lltv）——注意新版 Morpho `market(bytes32)`（`0x5c60e39a`）返回的是 6×uint128 头寸数据，不是市场参数，别用错
- **新增：MorphoChainlinkOracleV2 的 vault 模式识别**——BASE_FEED=0 + BASE_VAULT≠0 = 价格来自 vault 兑换率而非 Chainlink feed
- **坑**：USDC 6 位小数/sNUSD 18 位小数混算极易错位（本文案初算时把 $709.93 看成 $0.71，整条账错了一个数量级）；先统一小数位再对账
- 公共 RPC：llamarpc/1rpc 被网络拦 → **ethereum-rpc.publicnode.com 直连可用**（eth_call + eth_getTransactionReceipt 全通）

## 深度解析修正（2026-08-14 晚：debug_traceTransaction 全轨迹重建对照）

> 来源：外部深度解析报告（sources/0x82a206c9-arbitrage-analysis-report-20260813.md，dRPC callTracer 238KB 全轨迹 + 前后状态查询）。**修正了本笔记早上的三处理解**：

### 修正 1：那笔 $1,000 是「捐赠解封」，不是自留头寸
交易前市场**利用率 100%**（supply = borrow = 1,659,566.25），Morpho 规定借款 ≤ 存款，**此时谁也借不出钱**。bot 直接 supply 1,000 USDC（onBehalf=金库）打破 100% 利用率，制造出 1,006.94 的借款空间（1,000 捐赠 + 存取净差 6.94），借完利用率回到 100%。

### 修正 2：金库 27.7M 存款的真正作用是「份额放大器」
顶格存入（占金库总份额 **86.97%**，金库原规模仅 ~415 万被稀释）→ 捐赠挂在金库名下使份额单价 +3.13bps → 赎回时按 86.97% 拿回 869.65。**捐赠实际成本 = 1,000 − 869.65 = 130.35（13% 漏给金库其他持有人）**。没有这个放大器，捐赠成本是全额 1,000，利润直接转负。

### 修正 3：净利是 $166.67，不是 $297
```
+ 1,006.94  借出
−   709.93  买入 sNUSD
−   130.35  捐赠漏损（1,000 − 869.65）
=   166.67  已实现利润 → EOA ✓（Swept 事件 166,666,013 分毫不差）
另：+93.7   一次性合约 0xebf7 头寸净值（未实现，NAV 口径）
```
$297 是毛利（借款−买入），漏了捐赠成本。

### 新增认知
- **机会本质** = 「NAV 预言机市场 + 深折价衍生品 + 100% 利用率」三重结构；核心信号：`DEX 成交价 < LLTV × 预言机价`（本案 0.686 < 0.915×1.0638 = 0.9734）
- **容量硬顶**：两 V4 池仅锁 ~4,045 枚 sNUSD（~$2,700），bot 一笔抽走 25.6%，单次利润上限 ~$260
- **bot 画像**：Kyber calldata 自称 "MyAwesomeApp"；一天多跑（16:31/16:33/16:54），次日凌晨继续——**已在位竞争，价差窗口短**
- **退出风险**：债务挂在一次性合约 0xebf7（机器人已授权），若 sNUSD 无法按 NAV 赎回或 NUSD 脱锚，头寸市价 709.9 vs 债务 1,006.9 直接资不抵债
- 两个价格世界图：池价 0.686（浅池砸出折价）vs 预言机 1.0638（NAV 不动）→ 每枚借出 0.9734 − 成本 0.686 = 0.287 价差

## 数据来源

- tx：`https://etherscan.io/tx/0x82a206c9dff00bf7b205987bdcd9384c06c6d9962aa929c84ab45dd0330c4e72`
- blockscout v2：`eth.blockscout.com/api/v2/transactions/{hash}`（token-transfers / logs / addresses）
- RPC：ethereum-rpc.publicnode.com（receipt / eth_call）
- 市场 id：m1 `0x9bc98c2f…c7cd79`（PT-reUSD-25JUN2026）、m2 `0xae60b71b…777cb4`（sNUSD）、m3 `0xbbf7ce1b…1d8c99`（siUSD）
