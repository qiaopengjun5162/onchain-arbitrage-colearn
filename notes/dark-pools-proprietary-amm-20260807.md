# 暗池（Proprietary AMM / Dark Pools）：定价与套利方法

> 来源：Paxon 群内分享（2026-08-07，Hermes 套利共学 Telegram）
> 归档日期：2026-08-07
> 关联：`aggregator-routing.md`（聚合器视角）、`mempool-and-ordering.md`、Solana 线（`notes/solana/`）

## 定义与特点（分享原文要点）

暗池（proprietary AMMs / dark pools）：
- **公开信息极有限**：除了链上交易数据，没有前端、公开 IDLs、源码、文档、营销或社区渠道
- 实例：**SolFi**（注：`solana-rs` 实测路由中出现过 SolFi V2、BisonFi、HumidiFi——都是暗池型）
- 只能分析交易或尝试逆向工程逻辑

**核心难点**：没法像 Raydium 这类标准 AMM——查链上账户数据 + 明确数学公式 + 传输入量离线算出输出量。

## 三种定价/询价方法（分享原文）

1. **聚合器询价**：jupiter / okx / titan
2. **模拟法**：
   - RPC 模拟法（`simulateTransaction`）——在真实链上状态模拟执行
   - 离线模拟法——逆向工程合约逻辑后本地模拟

## Hermes 补充分析

### 1. 暗池为什么存在
- 新池子上线不想被狙击/抢跑（Jared 蜜罐正是利用公开 AMM 的贪婪逻辑）；做市商想隐藏持仓
- 暗池流动性通常小（无营销 = 用户少），但**知道的人少 = 竞争少**——信息差 edge 的典型场景

### 2. 三种方法的精度与代价对比

| 方法 | 精度 | 成本/代价 |
|---|---|---|
| 聚合器询价 | 中（黑盒，间接相信聚合器的模拟；报价有 30s 时效） | 零成本，但无法确认路由内部逻辑 |
| RPC 模拟（simulateTransaction） | **高（权威：真实状态上执行全部池子逻辑）** | 需先 build 交易；模拟≠成交（实际执行时状态已变） |
| 离线模拟 | 高（可控） | 需逆向工程：Solana 程序是 BPF/ELF 字节码可反汇编，但 pool state 编码要自己摸 |

### 3. 对套利研究的含义
- 暗池价格偏离主流 = 价格发现延迟（套利窗口），但需先解决"怎么给它定价"
- **推荐的定价路径**：聚合器询价做初筛 → `simulateTransaction` 做精确模拟 → 执行前用 `toAmountMin` 保护（暗池无公式可算，模拟价是唯一参考）
- **监听交易日志**：暗池 swap 的交易日志（event/log）可分析——通过监控链上交易提取池子状态变化，相当于"用数据反推黑盒"（对应"只可以分析交易"）
- 与 round-trip closure 方法论：暗池报价必须用**同一时刻**的模拟/聚合器报价做闭环验证，不能用两个不同时间的报价拼价差（幻觉价差风险更高，因为暗池没有公开公式兜底）

### 4. 关联实测（2026-08-07，solana-rs）
- `solana-rs quote` 实测路由中出现 **SolFi V2 / BisonFi / HumidiFi / AlphaQ / Invariant / Aquifer**——多为新/暗池型
- 0.01 SOL swap 实际路由 Invariant → Aquifer；多池路由在暗池间跳转时，聚合器（Jupiter Metis）已做了内部模拟定价
- 启示：Metis 路由本身就在用模拟法给暗池定价——聚合器是暗池定价的第一层基础设施

## 下一步（待定）

- 选一个暗池（如 SolFi）做一次"聚合器报价 vs RPC 模拟 vs 实际成交"三方对照实验
- 研究 Solana 上监听指定程序交易日志提取池子状态的可行性（Helius WebSocket / Geyser）

## 离线模拟落地：solfi-sim + LiteSVM（2026-08-07 下午，Paxon 分享）

### 方法学（Paxon 原文要点）

- 暗池的数学行为是黑箱，数学函数无法直接观察，**但可用模拟观察其行为**
- **构造指令**：池子相关地址不变，用户相关地址改变
- **账户数据**：实时更新（fetch 最新状态）
- **指令数据**：逆向（逆向 swap 指令编码）
- LiteSVM 实战踩坑：**预充值**（airdrop）+ **simulate_transaction 优化方案**（dry-run 不提交状态，可快速试多种输入）

### solfi-sim（https://github.com/tryghostxyz/solfi-sim，99★，Rust）

"uses LiteSVM to run local, black-box simulations on the SolFi DEX to understand how its pricing curves work"
- 本地内存跑 4 个 WSOL/USDC 池子；附带 slot 333456106 的账户状态快照 + 重新拉取工具
- 子命令：`fetch-accounts` / `cutoffs`（打印 slot cutoff 元数据）/ `simulate`（模拟 WSOL→USDC swap）
- 实测示例：simulate --amount 10 → 池子输出 1296.914 USDC
- **README 原文印证 round-trip closure**："if you run against an RPC node, you can't guarantee that your requests will all run against the same slot. These SolFi pools appear to update every slot, and running against the fetched state in a local SVM provides better simulation guarantees"——SolFi 池子**每 slot 更新**，本地 SVM 快照 = 同区块定价的工程实现（Paxon 方法论在暗池场景的官方验证）

### LiteSVM（https://github.com/LiteSVM/litesvm，627★，Rust）

快速轻量 Solana 程序测试库（in-process VM，比 solana-program-test / solana-test-validator 快）
- `cargo add --dev litesvm`
- 能力：program 加载（`add_program_from_file` / `add_program`；主网程序用 `solana program dump` 拉）、**simulate_transaction**（dry-run 不提交）、时间旅行、airdrop（预充值）
- 程序 ID：SolFi = `SoLFiHG9TfgtdUXUjWAxi3LtvYuFyDLVhBWxdMZxyCe`（solscan 可查）

### 暗池定价的工程路径（落地建议）

```
solana program dump SoLFi...（拉 SolFi 程序）
  → LiteSVM add_program + fetch 池子账户快照（同一 slot）
  → 构造 swap 指令（池子地址不变，用户地址可变）
  → simulate_transaction 批量试输入量 → 拟合出价曲线（黑箱行为观察）
```

## solfi-sim 定价实验（2026-08-07 Hermes 实测）

solfi-sim 编译成功（solana-sdk 2.2），快照 slot 355036660（cutoff 355036859），4 个 V1 WSOL/USDC 池：

### SOL→USDC 模拟（USDC 输出）

| 池 | 0.1 SOL | 1 SOL | 10 SOL | 100 SOL | 1000 SOL |
|---|---|---|---|---|---|
| 5guD4Uz | 20.184 | 201.835 | 2018.10 | 20177.64 | 201578.06 |
| DH4xmaW | 20.186 | 201.857 | 2018.52 | 20183.79 | 201740.52 |
| AHhiY6G | 20.185 | 201.849 | 2018.47 | 20183.16 | **失败 0x12** |
| CAPhoEs | 20.186 | 201.856 | 2018.52 | 20184.39 | 201795.73 |

### 结论（V1 定价特征）

1. **恒定价格 ≈ $201.84/SOL**：0.1→1000 SOL 全程线性（每档 ≈10 倍），**无可见滑点**——V1 是"稳定价格 + 深度流动性"
2. **池间价差 < 0.01%**：4 池几乎同价，无池间套利空间（至少同 slot 快照下）
3. **硬上限**：AHhi 池 1000 SOL 触发 `custom error 0x12`（容量/滑点防御）——池子有单笔上限
4. **对比 V2**：V2 是 Slot 加速衰减定价（延迟惩罚），V1 是恒定价格 + 上限——两种完全不同的黑箱定价模型
5. 对套利的含义：V1 池价格恒定 → 价差机会来自**池间/链间价格偏离**而非池内滑点；套利规模受池上限约束

## SolFi 情报（2026-08-07 Paxon 分享，暗池文档原文）

**背景**：Ellipsis Labs 开发运营（Phoenix 订单簿团队的"自然演进"），两个版本。

### V1：`SoLFiHG9TfgtdUXUjWAxi3LtvYuFyDLVhBWxdMZxyCe`
- 大部分池子已无流动性/停运；仍活跃：cbBTC-USDC (`4o9kDwyuBhc...`)、WBTC-USDC (`6LDKXn2hqEtd...`)

### V2：`SV2EYYJyRz2YhfXwXnhNAevDEui5Q6yrfyo13WtupPF`（solfi-sim 模拟的是 V1 池）
活跃池子（Discriminator 每池不同！）：
| Market | 池子 | Discriminator | 备注 |
|---|---|---|---|
| PUMP-USDC | 2kfQuYG2FVZ... | 0xFF | 询价0x7 ✅ |
| WSOL-USDC | 65ZHSArs5Xx... | — | 计算单元要很大 ✅ |
| USDT-USDC | FkEB6uvyzuo... | 0xFC | ✅ |
| ZEC-USDC | BjBHvbqgQCR... | 0xFF | ✅ |
| MON-USDC | 2Q6S8p9iZNz... | 0xFE | ✅ |
| HYPE-USDC | 2e25gRiddjn... | 0xFD | ✅ |
| zenZEC-USDC | 7TKsqWxU9Qk... | 0xFE | ✅ |
| + 9 个近 1-4 个月无交易池（USD1/USELESS/MET/SAROS/WLFI/2Z/3×WSOL-USDC） |

### 技术分析（金矿）
1. **Slot 验证**：账户数据过旧 → 报 `0x17` 错误
2. **CU 不足坑**：WSOL-USDC 路由 + wsol ATA 流程并存时 CU 不够 → 解法：提前建 wsol 账户 / system program `create account with seed`
3. **Jupiter 白名单优惠**：直接调 SolFi V2 vs 经 Jupiter 调，询价结果不同，**Jupiter 调用结果更好**——怀疑 SolFi V2 对 Jupiter 给优惠；`sysvar instructions` 的作用之一就是获取调用合约地址（识别调用者）
4. **Slot 依赖定价机制**（核心）：完全解耦链上时间戳；**价格随 Slot 增量非线性加速衰减（平方级/指数级）**——交易延迟越高滑点惩罚越重；Slot 延迟超阈值 → `Custom(23)` 预言机过期异常

### 对研究的含义
- **V2 每池 Discriminator 不同**（0xFC-0xFF）→ 指令构造不是一套通用模板，要逐池逆向（solfi-sim 的 V1 模板不能直接套 V2）
- **Slot 定价 = 时间套利窗口**：加速衰减意味着"越早提交越划算"，但过期惩罚（Custom 23）会把延迟交易拒掉——理解衰减曲线形状是定价关键（solfi-sim 拟合的就是这个）
- **Jupiter 优惠**：套利时走 Jupiter 路由调 SolFi 可能拿到比直连更好的价格——与 `solana-rs` 实测（路由含 SolFi V2）互相印证

### 2. Obric（主动式 AMM，存活但 TVL 极小）⭐ 已调研

- 合约地址：`obriQD1zbpyLz95G5n7nJe6a4DPjpFwa5XYPoNm113y`
- 官网：obric.xyz（"SMART LIQUIDITY MATTERS — Concentrated Liquidity Without Compromise"）
- **机制**：外部预言机价格 + 集中流动性（"proactive AMM"）→ 预言机价格附近做市，极高资本效率，大额低滑点
- **链上实测（2026-08-07 RPC）**：
  - 程序存在且 executable
  - **最近 5 笔交易全部成功（err=None），间隔 ~30 秒**（slot 437788985→437789130）——**活跃使用中**，与 Lifinity（全失败）对比鲜明
- **DefiLlama：TVL 仅 $1,185**（30 天 -4.2%）——**交易活跃但 TVL 极小** = 高周转/高换手，流动性提供者少
- 对套利的含义：
  - 预言机定价 AMM 的资本效率 = 大额交易低滑点（vs 传统 AMM 的规模惩罚）
  - 但 TVL $1.2K = 容量极小，套利吞吐上限低
  - 活跃交易可能是套利者/做市商自己在对打——预言机价与市场价偏离时，套利机器人吃掉价差（PM 系 AMM 的已知套利空间）

### 3. Tessera V（Wintermute 运营的 RFQ 暗池）⭐ 已调研

- 合约地址：`TessVdML9pBGgG9yGks7o4HewRaXVAMuoVj4x83GLQH`
- **运营方：Wintermute**（知名加密做市商/量化交易公司）
- **机制**：RFQ（报价请求）暗池——不是公开 AMM，而是机构大宗交易匹配（Wintermute 报价，成交不暴露订单簿）
- **链上实测（2026-08-07 RPC）**：
  - 程序存在且 executable
  - 最近 5 笔交易**全部集中在同一 slot**（437789280，12:36）——**批量/原子执行特征**（RFQ 批次打包）
  - 4 笔成功 + 1 笔失败（`Custom 6001` 程序自定义错误）
- 对套利的含义：
  - **与 AMM 型暗池（Lifinity/Obric）本质不同**：Tessera 是报价制暗池（做市商定价），不是自动做市——没有"池子公式"可逆向，定价权在 Wintermute 手里
  - RFQ 暗池的套利空间 = Wintermute 报价与市场价的偏离（如果存在），但需要白名单/机构通道才能询价——**散户/小资金不可达**
  - 批量原子执行 → 它的交易日志反映 Wintermute 的定价行为（研究价值：观察机构报价 vs 市场价的偏离分布）

### 4. HumidiFi（XOR 混淆指令的暗池）⭐ 已调研

- 合约地址：`9H6tua7jkLhdm3w8BvgpTn5LZNU7g4ZynDmCiNN3q6Rp` | 推特：@humidifi
- **指令数据保护：XOR 混淆**——指令数据 XOR 加密，需 XOR key 才能解密实际指令——比 SolFi 的公开 discriminator 更进一步的反逆向手段（逆向难度分级：SolFi 公开格式 → HumidiFi XOR 混淆）
- **Jup 的两个 HumidiFi swap 变体 = 同一合约的两种指令**（不是两个合约）：
  ```rust
  HumidiFi     { swap_id: u64, is_base_to_quote: bool }  // 指令 87
  HumidiFiV2   { swap_id: u64, is_base_to_quote: bool }  // 指令 118
  ```
- **is_base_to_quote 反转坑（极易踩）**：
  - jup 的 `is_base_to_quote` **与 humidifi 的相反**：jup false → humidifi true；jup true → humidifi false
  - **账户组装：token A = quote token，token B = base token**（与常规 A=base 相反！）
  - 直接照搬 jup 字段 → 组装出**反向交易**指令
- **链上实测（2026-08-07 RPC）**：
  - 程序存在且 executable；最近 5 笔同 slot 批量（437789703）
  - **2 成功 3 失败**（Custom 6066/6001/**57005=0xDEAD** 彩蛋错误码）——高失败率 + 批量特征
- 参考交易：
  - https://solscan.io/tx/2ax8nbZnujHQ5K9YoiEWu2UvHyK3KWB4hTgpFeMVgeWMM3aCvzvJj8UxA3UzoNxcQ4q2LLvCXCcmjS9L8sbAH4wK（Litepaper）
  - https://solscan.io/tx/YXc8QfB1EqjwYFYovp6MfgQNjmeXQVmUqy1CsgSY12P7APC8EbV5Nk1218VX1aoqstz3LzNJYUELdKVpAqSfWHN
- 对套利的含义：
  - 指令逆向是**可做但要先解密**的（XOR key 可从已知交易推断——已知输入输出 + 公开账户结构可以暴力/统计破解 key）
  - is_base_to_quote 反转 = 组装指令时的**经典坑位**：任何用 jup 数据组 HumidiFi 指令的代码都要做字段映射，做反了就是反向交易（送钱）
  - 高失败率（含 0xDEAD）暗示部分调用被协议拒绝——协议对调用者/状态有额外校验

### 5-7. GoonFi / ZeroFi / BisonFi（批量实测 2026-08-07）

| 协议 | 合约地址 | 状态 | 链上证据 |
|---|---|---|---|
| GoonFi V1 | `goonERTdGsjnkZqWuVjs73BZ3Pb9qoCUdBUL17BnS5j` | 🟡 冷清 | 08-02 一笔成功；07-28 两笔失败（ProgramFailedToComplete）——用户已迁移 V2 |
| GoonFi V2 | `goonuddtQRrWqqn5nFyczVKaie28f3kDkHWkHtURSLE` | 🟡 活跃调用但全失败 | 08-07 12:39 三笔**全部 Custom 6008** |
| ZeroFi | `ZERor4xhbUycZ6gb9ntrhqscUcZmAbQDjEAtCf4hbZY` | 🟢 活跃 | 08-07 12:39 两成功一失败（Custom 0） |
| BisonFi | `BiSoNHVpsVZW2F7rx2eQ59yQwKxzU5NvBcmKshCSUypi` | 🟢 活跃 | 08-07 12:39 一成功两失败（6001/56） |

**批量观察**：
- GoonFi V2 / ZeroFi / BisonFi 最近交易集中在 **08-07 12:39 同一分钟**——是群分享文档作者（solanaBuild）批量测试/逆向的时间点，也说明这些协议**近期有人在做实验**（可能正是暗池文档的来源）
- 每个协议错误码独立：6008（GoonFi）/ 0（ZeroFi）/ 6001·56（BisonFi）——错误码是协议内部语义，反逆向时可用
- **BisonFi 与我们 Rust 实测关联**：`solana-rs` 100 SOL quote 路由含 BisonFi（Quantum→AlphaQ→HumidiFi→BisonFi）——BisonFi 是 Jupiter 路由的活跃成员

### 8-10. AlphaQ / WooFi / Aquifer（批量实测 2026-08-07）

| 协议 | 合约地址 | 状态 | 链上证据 |
|---|---|---|---|
| AlphaQ | `ALPHAQmeA7bjrVuccPsYPiCvsi428SNwte66Srvs4pHA` | 🟢 活跃 | 08-07 12:40 三笔全成功 |
| WooFi | `WooFif76YGRNjk1pA8wCsN67aQsD9f9iLsz4NcJ1AVb` | 🟡 冷清 | 07-28 三笔全失败（InvalidInstruction/ProgramFailedToComplete），10 天无交易 |
| Aquifer | `AQU1FRd7papthgdrwPTTq5JacJh8YtwEXaBfKU3bTz45` | 🟢 活跃 | 08-07 12:40 三笔全成功 |

**与 Rust 实测的关联**：
- **AlphaQ**：`solana-rs` 100 SOL quote 路由成员（Quantum→**AlphaQ**→HumidiFi→BisonFi）
- **Aquifer**：`solana-rs` 1 SOL quote 单池路由（73.626 USDC，$73.63）——最活跃暗池之一
- **WooFi 特殊性**：严格说是 Woo Network 的公开 DEX（非典型暗池），但 Woo 做市商（MM）控制部分流动性 → "半暗池"。10 天无交易 + 全失败 → 被 Jupiter 路由绕开或弃用

### 暗池清单总览（10 条，2026-08-07 全部链上实测）

| # | 协议 | 状态 | 定价/保护机制 |
|---|---|---|---|
| 1 | Lifinity | 💀 关闭 | 预言机 AMM；claim 到 2026-12-31 |
| 2 | Obric | 🟢 活跃微小 | 预言机集中流动性；TVL $1.2K |
| 3 | Tessera V | 🟢 批量执行 | Wintermute RFQ（报价制，无公式） |
| 4 | HumidiFi | 🟢 活跃 | **XOR 混淆指令**；双变体 87/118；base/quote 反转坑 |
| 5 | GoonFi V1 | 🟡 冷清 | 用户已迁 V2 |
| 6 | GoonFi V2 | 🟡 全失败 | Custom 6008 |
| 7 | ZeroFi | 🟢 活跃 | 零费用 DEX |
| 8 | BisonFi | 🟢 活跃 | Jupiter 路由成员 |
| 9 | AlphaQ | 🟢 活跃 | Jupiter 路由成员 |
| 10 | WooFi | 🟡 冷清 | Woo 做市商控制（半暗池） |

### 11-13. WhaleStreet / Manifest / Scorch（批量实测 2026-08-07）

| 协议 | 合约地址 | 状态 | 链上证据 |
|---|---|---|---|
| WhaleStreet | `FW6zUqn4iKRaeopwwhwsquTY6ABWLLgjxtrC3VPnaWBf` | 🟢 活跃 | 08-07 12:41 三笔全成功 |
| Manifest | `MNFSTqtC93rEfYHB6hF82sKdZpUDFWkViLByLd1k1Ms` | 🟢 活跃 | 12:41 两成功一失败（Custom 6010） |
| Scorch | `ojh19ojaKduoJZuaJADhcVGp4xt1TcdAvZmpVsCorch` | 🟢 活跃 | 12:41 两成功一失败（Custom 5457） |

**备注**：
- **Manifest** = Ellipsis Labs（Phoenix 订单簿团队）的订单簿 DEX——非典型 AMM（订单簿 + 流动性池混合）；`solana-rs` 0.01 SOL swap 测试路由成员（BisonFi→**Manifest**）
- **WhaleStreet**：名如其人——鲸鱼聚合/大宗路由类协议
- Scorch Custom 5457（= 0x1551 有意义?）/ Manifest 6010——继续印证"错误码指纹"观察

### 暗池清单总览（13 条，2026-08-07 全部链上实测）

| # | 协议 | 状态 | 定价/保护机制 |
|---|---|---|---|
| 1 | Lifinity | 💀 关闭 | 预言机 AMM；claim 到 2026-12-31 |
| 2 | Obric | 🟢 活跃微小 | 预言机集中流动性；TVL $1.2K |
| 3 | Tessera V | 🟢 批量执行 | Wintermute RFQ（报价制，无公式） |
| 4 | HumidiFi | 🟢 活跃 | XOR 混淆指令；双变体 87/118；base/quote 反转坑 |
| 5 | GoonFi V1 | 🟡 冷清 | 用户已迁 V2 |
| 6 | GoonFi V2 | 🟡 全失败 | Custom 6008 |
| 7 | ZeroFi | 🟢 活跃 | 零费用 DEX |
| 8 | BisonFi | 🟢 活跃 | Jupiter 路由成员 |
| 9 | AlphaQ | 🟢 活跃 | Jupiter 路由成员 |
| 10 | WooFi | 🟡 冷清 | Woo 做市商控制（半暗池） |
| 11 | WhaleStreet | 🟢 活跃 | 鲸鱼聚合/大宗路由 |
| 12 | Manifest | 🟢 活跃 | 订单簿 DEX（Ellipsis/Phoenix 团队） |
| 13 | Scorch | 🟢 活跃 | 未知（错误码 5457） |

### 暗池光谱（三类对比，2026-08-07 实测）

| 协议 | 状态 | 定价机制 | 链上证据 |
|---|---|---|---|
| Lifinity | 💀 已关闭 | 预言机 AMM | 交易全失败 ProgramFailedToComplete；claim 到 2026-12-31 |
| SolFi V1 | 🟡 半死 | 恒定价格+硬上限 | V1 4 池交易冷清；V2 活跃（Slot 加速衰减定价） |
| Obric | 🟢 活跃但微小 | 预言机集中流动性 | 每 30s 一笔成功交易；TVL $1.2K |

## 参考资料（2026-08-07 归档，暗池文档完结）

1. **Solana's Proprietary AMM Revolution**（Helius 官方博客）— https://www.helius.dev/blog/solanas-proprietary-amm-revolution
   - Prop AMM 是 Solana 特有发展（结构性因素）；Obric V2 由小团队开发，先在 Aptos 上线后迁 Solana，2024-10 被 Jupiter 集成——最早期的 prop AMM 之一
2. **The Rise of Proprietary Market Makers on Solana**（Figment）— https://www.figment.io/insights/the-rise-of-proprietary-market-makers-on-solana
   - Prop/Dark AMM = 专业做市商运营的私有池，定价逻辑不暴露公开曲线；**吸收 Solana 成交量的可观份额**；JIT liquidity 同为新微观结构；价值主张：更低滑点 + 更少 adverse flow
3. **Why Are Proprietary AMMs Dominating Solana?**（Cyberk）— https://cyberk.io/blogs/why-are-proprietary-am-ms-is-dominating-solana
   - 三个架构因素：①链上价格更新便宜快速 ②做市逻辑 O(1) 更新（非 O(N) 订单簿）③Jupiter 聚合器输送大量非毒性零售流量
4. **How HumidiFi Became Solana's Largest Prop AMM**（Solana Compass/Lightspeed 播客）— https://solanacompass.com/learn/Lightspeed/how-humidifi-became-solanas-largest-prop-amm
   - **第一代 prop AMM 用自研定价模型而非外部预言机**（"每个 prop AMM 有自己的价格观"）；定价精度竞争驱动创新
5. **Understanding Proprietary AMMs**（Solana.com 官方）— https://solana.com/news/understanding-proprietary-amms
   - 传统 AMM 两个问题的解：①链上手续费使订单簿做市不盈利 ②AMM 不知道真实市场价被知情交易者狙击 → PropAMM 用实时价格流同时解决两者

**核心共识（5 篇）**：Prop AMM = 专业做市商自有资本 + 私有定价模型（预言机或自研）+ 链上高频更新 + 聚合器订单流——是 Solana 新市场微观结构（与 JIT liquidity 并列），正在重塑链上流动性的形态。

## 套利选手画像（2026-08-07 链上验证）

### 地址：`2npqrs8E9iWPGjRhWp7BsD9nG62xnBm9Av4rWgqF3ZPK`

**solanaBuild 观察（文档）**：
- 金额 **5000+ USDC** 在 HumidiFi 的 USDC/SOL 池子**来回套利**
- 使用 **Jito bundle** 将所有套利交易打包（bundle = 原子性 + 抢跑保护）

**Hermes 链上验证（2026-08-07 RPC）**：
- 地址活跃：300 笔/8h 窗口（02-07 16:06 → 02-08 00:26），**成功率 99.3%**（298/300）
- 近期行为：纯转账（System）+ **Jupiter swap（JUP6L）**为主
- **抽样 18 笔未发现直接调用 HumidiFi 程序**——套利可能发生在更早窗口，或通过 Jupiter route 间接调用（inner 指令层），需翻 >300 笔历史确认
- 附注：Jito bundle 是 RPC 层特性（bundle 内交易原子执行），on-chain 看不到 bundle 标记——只能从交易时间聚集/频率推断

### 对研究的意义
1. **暗池套利真实存在且有人在做**：5000+ USDC 规模 × HumidiFi USDC/SOL 池 × Jito bundle——与我们拆解的参考交易（Jupiter route 原子套利）同构
2. **Jito bundle = 专业玩家的标准动作**：套利交易打包 bundle（原子性 + 避免被夹）——这是"竞速场"的门票，印证我们不碰竞速的边界
3. **套利者画像方法**：地址 → 交易频率/成功率 → 程序构成 → 推断策略；本案例近期样本不足（转账为主），继续观察需翻历史

## 服务测试分析：LiteSVM 暗池询价服务（solanaBuild 实战，2026-08-07）

### 服务器配置
- 德国 IP，**4 核 8G**，Rust 服务
- 内存工具：**heaptrack**（⚠️ 不能用于生产级别——heaptrack 测试的询价时间不做参考）

### 踩坑（三条）
1. **litesvm 池子缓存机制导致内存溢出**（已解决）——缓存池子状态时未控制规模/未回收 → OOM；LiteSVM 长驻服务必须管理池子缓存生命周期
2. **USDT/USDC 池子询价持续报 0x17**——原因是 **USDT 池子经常被撤掉**（协议下线/迁移），询价服务还按旧列表请求 → 持续报错 + 大量垃圾日志。**0x17 不只是"数据过旧"（SolFi slot 验证），也可能是"池子不存在/已撤"**——要区分：过旧 vs 已撤
3. heaptrack 只用于开发期内存分析，性能数据不可信

### 询价耗时分布
- 时间主要占用在 **`[9] Execute SVM simulation`**——LiteSVM 模拟执行本身是询价路径的瓶颈（账户序列化/加载/执行），优化方向：缓存池子账户 + 复用 SVM 实例 + 最小化每笔询价的账户集

### 对我们的意义（如果搭暗池询价服务）
- 服务设计：LiteSVM 实例池 + 池子账户缓存（注意 OOM 坑）+ 池子有效性检查（0x17 = 过旧 or 已撤，撤了就从清单剔除）
- 询价延迟预算：模拟执行是主耗时 → 单次询价预算按"一次 SVM execution"估
- 生产不要 heaptrack；服务器 4C8G 够用（模拟是 CPU 密集）

## 获取所有协议：Jupiter program-id-to-label（2026-08-07 验证）

- **API**：`https://api.jup.ag/swap/v1/program-id-to-label`（实测可用，102 个程序；旧域名 quote-api.jup.ag 已失效）
- **存档**：`scripts/jupiter_program_labels.json`（程序 ID → 协议名映射，自动化的"协议清单"来源）
- 文档：https://developers.jup.ag/docs/api-reference/swap/v1/program-id-to-label

### 对照结果（16 项调研 vs Jupiter 官方）

- ✅ **14/16 在 Jupiter 清单**：Obric V2 / TesseraV / HumidiFi / GoonFi V2 / ZeroFi / BisonFi / AlphaQ / Woofi / WhaleStreet / Manifest / Scorch / SolFi(V1+V2) / Invariant
- ❌ **2 个不在**：Lifinity（已关闭被移除）、GoonFi V1（Jupiter 只留 V2）——**"不在 Jupiter 清单"本身就是死亡/弃用信号** ✅ 新的筛选器
- 注：Invariant 也在清单（Rust 测试路由成员）

### 未调研的下一层协议（77 个，含新发现）

BinaryFi、BisonFi Predict、Denali、Deriverse、Flint、Flux、GatorSwap、Hadron、Huma、Hylo Exchange、Hylo Stability Pool、JupLend AMM、**JupiterRfqV2**（Jupiter 自己的 RFQ 暗池！）、Kipseli、LemmingsFi、M Swap、Metric、Omnipair、**Quantum**（Rust 100 SOL 路由第一站）、Riptide、RunnerRodeo、Scale Amm、Scale Vmm、TaurusFi、Trends、Voltr、XOrca 等

### 意义

1. **协议清单自动化的入口**：以后找"有哪些协议/新协议"，拉这个 API 就行（可定时对比新旧差异 = 新协议发现器）
2. **死亡检测器**：被 Jupiter 移除 = 协议死了/被绕开（Lifinity/GoonFi V1 案例）
3. **暗池清单可扩展**：JupiterRfqV2、Quantum、Scale Amm/Vmm、Omnipair 等是下一批可调研对象

## 构建交易：Jupiter route 原子套利参考（2026-08-07 拆解）

> 参考交易：https://solscan.io/tx/4E9AAaHF35e7LR9JXD1S65ykQBB2vcBoxrptCP8DJ7DzMKL2ZzZSgXAdghcsFE5mBeuED77FRgohCqfcHMt9XDhq（2025-12-16）

### 指令结构（getTransaction json 解析）

```
[0] ComputeBudget        （CU 预算）
[1] C6DhWNV...（未公开 DEX 程序）  4 账户 — 池操作 1
[2] JUP6LkbZb... Jupiter V6      38 账户 — route/swap 核心指令 ⭐
[3] C6DhWNV...（未公开 DEX 程序）  5 账户 — 池操作 2
[4] Memo
[5] ComputeBudget
```

### token 流还原（SOL→USDC→SOL 往返闭环）

| 账户 | 变化 | 解读 |
|---|---|---|
| 池1 USDC | +1214.11 | 卖 SOL 买 USDC |
| 池1 SOL | −9.5 | |
| 池2 USDC | −1213.72 | 卖 USDC 买 SOL |
| 池2 SOL | +9.5 | |
| 签名者 SOL | +0.0012 | 微利（示例小额） |

- 卖出价 127.80 USDC/SOL，买入价 127.76 → 价差 ~0.04 USDC/SOL（示例规模利润极小，教学用）
- **关键**：`C6DhWNV2865yHPJzMQGpxbbDqHLE6kwNv1DHuKwc47Fu` 是**未公开程序**（explorer 显示 Unknown Program）——又一个暗池/私有 DEX，Jupiter route 直接把它当普通池子调用
- **方法**：原子套利 = Jupiter route 指令（38 账户）在**一个 tx 内**完成往返 swap，两个 DEX 池夹着 route 调用——这就是"构建原子套利交易"的标准模板

### 与 solana-rs 的对应

`solana-rs` 的 build()（/swap/v2/build）生成的正是这类结构：setup + computeBudget + **Jupiter swap 指令（含 route）** + cleanup——参考交易是手写版，build 是自动化版。

## 方法论纪律：做 LP 永远要看池子（Paxon 2026-08-07 定调）

**协议级别判断会骗人，池子级别才可信。** 13 条暗池实测的每个反例：

- GoonFi V1 冷清 ≠ GoonFi 不行 → 用户全迁 V2（V1/V2 两个池组完全不同的命运）
- Obric 交易活跃 ≠ 有钱可赚 → TVL 只有 $1.2K，吞吐量卡死
- HumidiFi 程序活跃 ≠ 能直接用 → 3/5 失败率 + XOR 混淆 + 方向反转坑
- WooFi 品牌知名（Woo Network）≠ 池子有用 → 10 天无交易、全失败
- 同 slot 批量成功 ≠ 协议健康 → 可能是作者自己在批量测试（12:39-12:41 那批）

**池子级检查清单（做 LP / 做套利前逐项过）**：
1. 该池子/该版本的**真实活跃度**（不是协议整体）——最近 3 笔交易的成败
2. **流动性规模**（TVL/储备）——吞吐上限
3. **手续费结构**（分档/动态/固定）——摩擦成本
4. **定价机制**（恒定/预言机/订单簿/黑箱）——可逆性
5. **失败率与错误码**——校验逻辑的松紧
6. **调用者是谁**——如果交易全是一个人在批量测试，那不是真实需求

一句话：**品牌、宣传、协议名气都是噪音；池子的交易记录、储备、费率、错误码才是信号。**

## 暗池协议清单（solanaBuild 分享文档，2026-08-07）

### 1. Lifinity（协议已关闭）——基于预言机的 AMM ⭐ 已调研

- 合约地址：`2wT8Yq49kHgDzXuPxZSaeLaH1qbmGXtEyPy64bL7aD3c`
- Twitter：@Lifinity_io
- **关闭时间线**（web + 链上验证）：
  - 2025-12-10：面对 prop AMMs 竞争压力，决定逐步停运
  - 2025-12-18：关闭提案接近全票通过；团队开发 xLFNTY→USDC 转换程序并审计
  - 2025-12-29：**Claims 上线**（lifinity.io/claim，将代币转成 USDC）
  - 2025-12-30：Solana 官方发帖称赞（"did right by their users to the very end"）
  - 2026-01-03：正式道别
  - **2026-12-31 前可领取资产，之后网站/支持全部终止**
- 分配规模：约 **$4340 万**资产分配给代币持有者
- **链上实测（2026-08-07 RPC）**：
  - 程序仍存在且 executable（BPFLoaderUpgradeable），未被删除
  - 最近 3 笔交易**全部失败**：`InstructionError: ProgramFailedToComplete`（slot 435753959 附近）——交易已停的确认，仍有残留交互尝试
- **捡尸体含义**：
  - xLFNTY→USDC claim 窗口开到 2026-12-31（约 5 个月）——持有者未 claim 的沉淀资金
  - 程序可 `solana program dump` 拉取——预言机 AMM 定价逻辑的逆向素材（暗池历史行为研究）
