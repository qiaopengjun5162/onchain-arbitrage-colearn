# 以太坊主网套利交易分析报告

**交易哈希**: `0x82a206c9dff00bf7b205987bdcd9384c06c6d9962aa929c84ab45dd0330c4e72`
**区块**: 25,710,561（`0x188dfe1`）· **时间**: 2026-08-13 16:54:11 UTC · 块内第 279/342 笔
**分析日期**: 2026-08（基于链上原始数据完整重建：`debug_traceTransaction` callTracer 全轨迹 + receipt 日志逐条解码 + 交易前后链上状态查询 + Blockscout 合约识别）

---

## 1. 一句话结论

机器人用**免费 Morpho 闪电贷**顶格存入 MetaMorpho 金库放大自己的份额占比、以 **13% 的净成本**向一个利用率 100% 的 Morpho 市场"买出"借款额度，然后在 Uniswap V4 池里以 **64% NAV（0.686 USDC）** 的价格买入 sNUSD、在 Morpho 按 **91.5% × NAV（1.0638 USDC）** 借出 USDC，当场把折价套现，并把债务丢给交易内新建的一次性合约。

---

## 2. 交易总览

| 项目 | 值 |
|---|---|
| 发起者 EOA | `0x343de4fe545e0bde879a96500700800720f7af32` |
| 执行合约（机器人） | `0xfbc74f4a2b603715c8b4368be062157ea536142d`（未开源；在 Kyber calldata 中自称 **"MyAwesomeApp"**） |
| 入口函数 | `0x02393416`（含市场 id 等参数） |
| Gas used | 1,739,038 |
| Gas price | ≈ 0.1304 gwei（baseFee 0.1247 + priority 0.0057） |
| 手续费 | ≈ 0.000227 ETH（约 $0.5） |
| **已实现利润** | **166.666013 USDC** → EOA |
| 未实现部分 | 一次性合约 `0xebf7...` 上的 Morpho 头寸净值 **+93.7 USDC**（NAV 口径） |

---

## 3. 涉及的协议与合约

| 角色 | 合约 | 说明 |
|---|---|---|
| Morpho Blue | `0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb` | 借贷层 + 免费闪电贷来源 |
| 核心市场 | id `0xae60b71b407e0517ead445b7113a7ffa07ea4a9379d526ade541a3e9ec777cb4` | **USDC 贷 / sNUSD 抵押**，LLTV **91.5%**，IRM = AdaptiveCurveIrm（`0x870ac11d...`），费率 0 |
| 市场预言机 | `0x28e82e7f25dbcd487af27c80de4f62553260feca`（MorphoChainlinkOracleV2） | 喂价 = sNUSD NAV（≈ `sNUSD.convertToAssets`，Chainlink 口径） |
| sNUSD | `0x08efcc2f3e61185d0ea7f8830b3fec9bfa2ee313` | Neutrl 的质押型代币（Staked NUSD），ERC-4626 金库 |
| NUSD | `0xe556aba6fe6036275ec1f87eda296be72c811bce` | Neutrl USD，sNUSD 的底层资产 |
| MetaMorpho 金库 | `0xf29ce940178c8794802fb48a6c1b2edddac96431` | 第三方策展 USDC 金库，向 9 个 Morpho 市场放贷（含本市场；其余抵押品为 Pendle PT、WBTC、stETH 等） |
| Kyber MetaAggregationRouterV2 | `0x6131b5fae19ea4f9d964eac0408e4408b66337b5` | 聚合路由，经自有 V4 模块（`0xadf0233ab0...`）进入 Uniswap V4 |
| Uniswap V4 PoolManager | `0x000000000004444c5dc75cB358380D2e3dE08A90` | 两个 sNUSD/USDC V4 池 |
| 一次性助手合约 | `0xebf74c12319fc28251ce7f7aac5e8c877509705e` | 交易内 CREATE；接收抵押品与债务 |
| V4 池 1 | id `0xbc4146ed2af95067570f528c1445d8530f1aca9c` | 960.38 sNUSD @ 653.13 USDC |
| V4 池 2 | id `0xe6a803f91369422e736ea73ca80c5f5820a7ecee` | 74.21 sNUSD @ 56.79 USDC |

---

## 4. 执行流程（8 步，全部原子化在闪电贷回调内）

```
 EOA 0x343de4fe...
   │  execute()
   ▼
 机器人合约 0xfbc74f4a...（"MyAwesomeApp"）
   │
   ▼
[1] Morpho 闪电贷      +27,722,557.77 USDC   (手续费 0)
   │
   ▼
[2] 顶格存入 MetaMorpho 金库
    -27,720,847.84 USDC  ──────► 拿到金库 86.97% 份额
   │
   ▼
[3] 捐赠给市场 ae60    -1,000 USDC  (onBehalf=金库)
    ──────► 市场利用率从 100% 解封，出现借款空间
   │
   ▼
[4] Kyber → Uniswap V4 两个池
    -709.93 USDC  ──────►  +1,034.60 sNUSD  (@0.686/枚)
   │
   ▼
[5] 抵押 sNUSD + 借款   +1,006.94 USDC
    = NAV(1.0638) × 91.5%；债务记在一次性合约 0xebf7 名下
   │
   ▼
[6] 赎回金库            +27,721,717.49 USDC  (含捐赠回血 869.65)
   │
   ▼
[7] 归还闪电贷          -27,722,557.77 USDC
   │
   ▼
[8] 利润                +166.67 USDC  ──────► EOA
```

### 逐步细节

1. **Morpho 闪电贷 27,722,557.77 USDC**（`flashLoan(MarketParams, assets, data)`，市场费率 0，免费）。
2. **顶格存入 MetaMorpho 金库 27,720,847.84 USDC**：`maxDeposit` 返回 27,720,847,999,064（金库存款上限），机器人几乎打满。金库把资金分配到 3 个 Morpho 市场（ae60 得 8,340,464.53）。机器人获得 26,222,631,809,040,610,733,804,588 份额 = **金库总份额的 86.97%**（金库原规模仅约 415 万 USDC，被这笔存款稀释）。
3. **捐赠 1,000 USDC**：直接 `supply` 进市场 ae60，`onBehalf` 填金库地址 → 金库 totalAssets +1000，份额单价上涨约 3.13 bps；同时市场供给 +1000，**打破 100% 利用率**。
4. **Kyber 聚合买入 sNUSD**：709.926805 USDC → 1,034.5969855 sNUSD，经两个 Uniswap V4 池：
   - 池 1：960.3826 sNUSD @ 653.132660 USDC → **0.6801 USDC/枚**
   - 池 2：74.21438 sNUSD @ 56.794145 USDC → **0.7653 USDC/枚**
   - calldata 中 ClientData 字段：`{"Source":"MyAwesomeApp","AmountInUSD":"710.602939","AmountOutUSD":"0",...}` —— Kyber 定价接口把 sNUSD 当成 $0，机器人正是利用这个"市场不知情"。
5. **部署一次性合约 `0xebf7...`**（构造函数调用 Morpho `setAuthorization(机器人, true)`），然后：
   - `supplyCollateral`：1,034.5969855 sNUSD，`onBehalf = 0xebf7`
   - `borrow`：1,006.940350 USDC，`onBehalf = 0xebf7`，`receiver = 机器人合约`
6. **赎回金库 27,721,717.49 USDC**：比存入多 +869.65（= 捐赠 1,000 × 86.97% 份额占比）。
7. **归还闪电贷 27,722,557.77 USDC**。
8. **利润 166.666013 USDC 转给 EOA**（机器人合约 `Swept` 事件 166,666,013）。

---

## 5. 获利原理：两个价格世界

```
                    ┌── 池价 0.686 USDC/枚（池子极浅被砸出的折价）──→ 买入成本
      sNUSD ────────┤
                    └── 预言机价 1.0638 USDC/枚（= NAV，Morpho 按此放贷）──→ 抵押可借 91.5%
                       每枚借出 0.9734 − 成本 0.686 = 0.287 价差
```

- 交易时 `sNUSD.convertToAssets(1e18)` = **1,063,795,351,104,006,057**（≈1.0638 USDC/枚），预言机 `price()` 输出 1.0637953511e21（= convertToAssets × 1000，适配 Morpho 价格刻度）。
- 两个 V4 池总计只锁了约 **4,045.9 枚 sNUSD**（≈ $2,700 流动性），机器人一笔就抽走 25.6%，池价被砸到 NAV 的 64%。
- Morpho 允许按 NAV 的 91.5% 借款：
  - 抵押物 NAV 价值 = 1,034.597 × 1.063795 = **1,100.60 USDC**
  - 最高可借 = 1,100.60 × 91.5% = 1,007.05 USDC（实际借 1,006.94，LTV = 91.49%，贴着上限）
  - **毛利润 = 借出 1,006.94 − 买入成本 709.93 = +297.01 USDC**

**折价为什么存在**：sNUSD 是质押型代币，解押有流程/队列，不能即时按 NAV 赎回；池子流动性极薄，任何抛售都会砸出深折价；而 NAV 预言机不动，Morpho 继续按 1.0638 放贷。机器人专收这种"结构性错价"。

---

## 6. 三个关键工程细节

### 6.1 为什么搞 27.7M 存款 + 1,000 捐赠？——市场利用率 100%，借不了钱

交易前一区块（`0x188dfe0`）的市场状态：

```
totalSupplyAssets = 1,659,566.249220
totalBorrowAssets = 1,659,566.249220   ← 完全相等，利用率 100.0000%
```

Morpho 规定借款总额 ≤ 存款总额，此时谁也借不出钱。机器人捐赠 1,000（+ 金库存取间净多出的 6.94）恰好凑出 **1,006.94 的借款空间**，借完后利用率回到 100%（`borrow = 1,006.940350` 与供给增量分毫不差）。

### 6.2 捐赠为什么能几乎无损拿回？——金库份额当"放大器"

捐赠挂在金库名下（`onBehalf = 金库`），金库份额单价上涨 3.13 bps。机器人先闪电贷顶格存入、持有 86.97% 份额，赎回时拿回 1,000 × 86.97% = **869.65**，实际捐赠成本仅 **130.35**（13% 漏给金库其他持有人——他们相当于 87 折买入了 1,000 USDC 的生息存款）。

若没有这步，捐赠成本是整整 1,000，利润直接转负。

### 6.3 债务怎么处理？——甩给一次性合约

借款 `onBehalf = 0xebf7`（新建合约，抵押品也在其名下），借出的 USDC 却转给机器人。交易结束后 `0xebf7` 持有：

```
+ 1,034.60 sNUSD 抵押
− 1,006.94 USDC 债务
净值 +93.7 USDC（NAV 口径）
```

机器人已被授权管理该头寸，之后可随时还款取回 sNUSD 按 NAV 赎回兑现，或让头寸长期滚动。

---

## 7. P&L 账本（单位 USDC）

```
  + 1,006.94   借出（债务丢给 0xebf7）
  −   709.93   买入 sNUSD
  −   130.35   捐赠漏损（1,000 − 869.65）
  ═══════════
  =   166.67   已实现利润 → EOA  ✓（与日志 Swept 166,666,013 完全一致）
  −    ~0.5    gas（0.000227 ETH）
  ───────────
  另：+93.7    0xebf7 头寸净值（未实现，NAV 口径）

  资金守恒校验：flash +27,722,557.767661 − 存款 27,720,847.840856 − 捐赠 1,000
  − 买币 709.926805 + 借款 1,006.940350 + 赎回 27,721,717.493324
  − 还款 27,722,557.767661 − 划转 166.666013 = 0 ✓
```

---

## 8. 此类机会如何捕获

1. **监控对象**：Morpho Blue 中"抵押品 = 衍生/质押/4626 份额代币、预言机 = NAV 类"的市场（特征：`MorphoChainlinkOracleV2` 或封装 `convertToAssets` 的预言机）。
2. **核心信号**：`DEX 成交价 < LLTV × 预言机价格`。本案 0.686 < 0.915 × 1.0638 = 0.9734。
3. **第二信号（易被忽略）**：市场利用率。`market(id)` 显示 supply ≈ borrow（100% 利用率）时，必须先制造供给头寸（捐赠/入金）才借得出来——这是本 tx 花费 130 USDC 解决的门槛。
4. **容量测算**：利润上限由**池子深度**决定而非价差。应计算 `可买数量 × (LLTV×NAV − 成交价)`；本例两池共 ~4,045 枚 sNUSD，单次利润上限仅 ~$260。
5. **执行链路**：聚合器（Kyber/1inch/0x）+ 直接对 PoolManager 的 V4 路由；上线前用 Tenderly 模拟全套动作并核对 `maxDeposit / maxWithdraw / borrow` 上限与市场状态。
6. **风险清单**：
   - sNUSD 能否真的按 NAV 赎回（解押队列/暂停风险）；
   - NUSD 本身脱锚风险；
   - 预言机是否真实跟踪 NAV、是否可被操纵；
   - 竞争：该机器人已在反复运行（16:31、16:33、16:54 一天多次，次日凌晨继续），价差窗口短；
   - 公共 mempool 下存在被 frontrun（抢买抬价）风险，需考虑私有 relay。

---

## 9. 能否模仿？

**技术上可行**（合法、公开的"借贷平台 NAV 折价套利"策略家族），但需认清：

- **单笔利润薄**：已实现 $167 + 未实现 ~$94，且被池深硬性封顶；节点/监控/模拟等基础设施成本会侵蚀利润。
- **需要自写合约**：顶格存款、onBehalf 捐赠、借款、闪电贷归还、头寸管理必须原子化（本 tx 机器人合约未开源，需自行实现）。
- **在位竞争**：已有高频跑者；需考虑私有 relay 防 frontrun。
- **真正的风险在退出端**：借出的钱是自己的债务头寸（哪怕挂在一次性合约名下）；若 sNUSD 无法按 NAV 赎回或 NUSD 脱锚，头寸按市场价资不抵债（抵押品市价 709.9 vs 债务 1,006.9），会被清算或损失。
- **可复制的正确姿势**：先做**无头寸版本**——在折价出现且能按 NAV 赎回的品种上，"池里买 → 抵押 → 借款"，借款额度 < 市场剩余可借量，并持续监控 LTV 与预言机变化。

---

## 10. 附：分析数据来源与中间产物

- 交易/RCPT：publicnode、dRPC 公共 RPC（`eth_getTransactionByHash`、`eth_getTransactionReceipt`）
- 调用轨迹：dRPC `debug_traceTransaction`（callTracer，238 KB）
- 日志解码：receipt 全部 72 条日志逐条解码（Transfer/Supply/Borrow/Withdraw/Swap/FlashLoan 等）
- 链上状态：`eth_call` 查询交易前（`0x188dfe0`）与交易后（`0x188dfe1`）市场状态与头寸
- 合约识别：Blockscout API（MetaMorphoV1_1 / sNUSD / NUSD / AdaptiveCurveIrm / MorphoChainlinkOracleV2 / PoolManager）
- 事件签名：4byte.directory + 本地 keccak 校验
- 项目背景：Neutrl 官方文档、Messari 报告、DefiLlama/DexPaprika 等公开资料

本地中间文件（工作目录 `/home/zhangy/temp/`）：

- `calltrace.json` — 完整 callTracer 调用树
- `receipt.json` — 交易收据
- `trace.json` / `sel_names.json` / `topic_names.json` — 轨迹与签名解析
- `0x82a206c9_flowchart.txt` — ASCII 流程图
- `0x82a206c9_flowchart.mmd` — Mermaid 流程图

> 备注：原始 Tenderly 导出文件 `/tmp/0x82a206c9....json` 在本分析环境中不可见（沙箱 `/tmp` 为空），本报告完全基于链上公开数据重建，信息量等价；如将该文件复制进工作目录可做逐层对照核验。
