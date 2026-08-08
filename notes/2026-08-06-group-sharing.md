# 2026-08-06 群分享整理：套利工具、基础设施与概念区分

日期：2026-08-06
来源：共学群讨论 + X/Twitter 分享

---

## 一、核心概念：价差套利 vs MEV 套利

群里讨论时容易把两类混在一起，先厘清：

| | 价差套利 (Price Spread Arbitrage) | MEV 套利 (MEV Arbitrage) |
|---|---|---|
| **关注点** | 寻找**目标**：不同市场/资产间的价格不一致 | 寻找**手段**：利用交易排序权和mempool |
| **核心动作** | 买低卖高 | 抢跑/夹击/尾随 |
| **典型形式** | 跨所套利、三角套利、期现套利 | 三明治攻击、Back-running、清算抢跑 |
| **利润来源** | 市场定价失效 | 区块排序权 |
| **对普通用户** | 中性/正面（抹平价差=提供流动性） | 负面（抬高用户交易成本） |
| **依赖** | 多市场数据、快速执行 | Mempool可见性、区块构建权 |

实际策略中两者经常交织。比如：发现跨所价差（价差套利），但要用MEV手法抢在别人前面执行——此时价差是目标，MEV是手段。

---

## 二、Gate CrossEx — 跨所统一保证金套利工具

- **Repo**: https://github.com/your-quantguy/gate-crossex
- **原帖**: https://x.com/yourQuantGuy/status/2084965415122301322
- **类型**: 价差套利（跨所资金费率/价差）

### 核心机制

Gate CrossEx 聚合 Binance、OKX、Bybit、Kraken、Hyperliquid、Deribit 等7个交易所，提供**跨所统一保证金**。

传统跨所套利两大痛点被解决：
1. **单边爆仓风险** — 跨所统一保证金，波动造成的浮盈浮亏两边抵消。唯一爆仓可能是两个交易所价差往不利方向拉到极端（做大币/RWA资费套利时可能性极低）。
2. **保证金平衡** — 不需要像传统跨所那样频繁两边调仓。

### 开源前端功能

yourQuantGuy 做的开源前端（AGPL-3.0），本地运行，127.0.0.1 only：
- 多所统一保证金手动交易
- 资费监控面板 + 一键对冲开仓
- 海力士美股/韩股溢价监控及交易
- 本地运行，无遥测无云端后端

### 关键数字

- 作者实测：SKHYNIX/SKHY溢价40%+，6000u 10x杠杆，盈利3500u
- 5倍杠杆下，传统跨所波动20%单边爆仓；CrossEx需价差拉大20%才爆仓
- 技术栈：Node.js/TypeScript，monorepo结构

### 后续计划

Paxon 计划过两天实际安装跑一下 gate-crossex，验证跨所统一保证金的实际体验。

### 对共学的意义

属于**价差套利**类别，工具层而非策略层。价值在于降低跨所执行门槛。需要关注Gate的监管风险对CrossEx服务的影响。

---

## 三、Backpack 交易所 — 内置套利路径展示

- **Issue**: https://github.com/w3player/arbitrage-playbook/issues/4
- **原帖**: https://x.com/wepoets1107/status/2084886140054831155
- **类型**: 价差套利（聚合展示）

### 核心机制

Backpack（背包所）聚合数据，直接在界面上实时展示套利路径。交易所把套利路径喂给用户，"左套右套"。

附带固定奖励活动。

### 分析

- **优势**: 零门槛，不需要自己写脚本/搭基础设施
- **劣势**: 所有人看到同样的路径，利润窗口极短
- **本质**: 更像"搬砖"而非alpha。类似稳定币脱锚时所有人都在搬，利润被快速抹平
- **可持续性**: 取决于Backpack是否持续提供独特的数据聚合和速度优势

### 后续计划

Paxon 计划过两天实际安装跑一下 gate-crossex，验证跨所统一保证金的实际体验。

### 对共学的意义

提醒我们：交易所展示的"套利机会"往往是已经被充分竞争过的。真正的edge不来自公开信息，来自信息不对称或基础设施优势。

---

## 四、LI.FI — 跨链套利执行基础设施

- **原文**: https://x.com/brucexu_eth/status/2085022891339554855 (Bruce)
- **类型**: 执行层工具（价差套利的基础设施）

### LI.FI 是什么

链上流动性的路径和执行层。聚合 Bridge、DEX、Solver 和 DeFi Protocol，通过统一 API、SDK、Widget、CLI 和 MCP Server 提供查询与执行能力。

对套利系统来说：**策略系统负责"哪里有机会"和"扣完所有成本后是否值得做"；LI.FI负责"资金具体怎么走""这条 Route 现在要付出多少成本""如何构造交易"和"执行到哪一步了"。**

### 主要服务

- **Bridge**: 跨链资产转移
- **Swap**: 同链或跨链 Token 兑换
- **Intents**: 用户描述结果，Solver 竞争报价并执行
- **Composer**: 把 Bridge/Swap/Deposit/Stake 组合成一条 DeFi Flow
- **Earn**: 查询收益机会 + 执行 Deposit
- **Token Service**: Token Metadata、priceUSD、验证状态
- **Gas API**: 各链 Gas Price 和 Gas Suggestion
- **Status Service**: 跟踪跨链交易（PENDING → DONE/FAILED，DONE 下分 COMPLETED/PARTIAL/REFUNDED）

### Quote 核心字段

| 字段 | 含义 |
|---|---|
| `toAmount` | 预计收到多少 |
| `toAmountMin` | 考虑滑点后最低保证多少 |
| `feeCosts` | LI.FI / Bridge / DEX 各层费用 |
| `gasCosts` | 链上 Gas 估算 |
| `executionDuration` | 预计完成时间 |
| `tool` / `includedSteps` | 实际走了哪些工具和步骤 |
| `transactionRequest` | 等待钱包签名的交易数据 |

简单场景用 `/quote` 拿最佳单步 Route。多步流程用 `/advanced/routes` 比较多个候选，每个 Step 单独生成交易数据。广播后用 `/status` 跟踪。

### 执行前必查清单

在做任何跨链套利执行前，至少确认以下数字：

1. **真实 Quote** — 调用 LI.FI `/v1/quote` 或 `/advanced/routes` 获取真实报价
2. **Service Fee** — LI.FI / Bridge / DEX / Solver 各层费用
3. **Gas** — 源链 + 目标链的 Gas 估算
4. **滑点 (Slippage)** — `toAmountMin` vs `toAmount` 的差距
5. **Price Impact** — 交易对池子价格的冲击
6. **最低到手数量** — 最坏情况能收到多少
7. **预计耗时** — `executionDuration`，跨链秒级窗口能否赶上
8. **链上模拟** — 最好做一次 simulate，不签不广播

只有这些数字都放进去之后，才能判断机会是否还有利润。

### 真实案例：Ethereum USDC → Arbitrum USDC

```
输入: 1,000 USDC (Ethereum)
Route: Eco
预计到手: 997.5 USDC
最低到手: 997.5 USDC
LI.FI Service Fee: 2.5 USDC (0.25% = 25 bps)
Ethereum Gas: ~$0.2456
预计耗时: 7秒
总显性成本: ~$2.7455 (27.455 bps)
```

### 对套利策略的关键约束

**25 bps的服务费直接抬高Break-even线。** 如果表面价差只有20 bps，光LI.FI费用就吃掉了。即使价差40 bps，扣完Gas、目标交易滑点、延迟风险后也未必有利润。

计算公式：
```
最低所需价差 = LI.FI Service Fee
             + Bridge/DEX/Solver Fee
             + 源链与目标链 Gas
             + 两端交易滑点和Price Impact
             + 延迟、失败与资金占用成本
```

### 更适合的做法

- **预置资金**：在多条链预先放好资金，两端同时交易，再用LI.FI做库存再平衡（把"抓机会"和"跨链调仓"拆开）
- **Route比较**：同时请求多个候选路径，比较toAmountMin、Gas、Fee、Duration和工具风险
- **Token验证**：用LI.FI Token Service确认地址、decimals、priceUSD（基于CoinGecko，覆盖40+链/200万+资产）

### Agent集成 (Hermes)

LI.FI提供MCP Server: `https://mcp.li.quest/mcp`

### 注册与 API Key

1. 邮箱注册 [LI.FI Partner Portal](https://portal.li.fi/)，完成邮箱验证
2. 创建 Integration，设置 `integrator string`
3. 创建 API Key（仅显示一次，立即保存到环境变量）
4. 调用 `/v1/keys/test` 验证 Key 有效
5. 测试 `/chains`、`/tokens`、`/tools`、`/quote`

公开 API 不带 Key 也能调，但额度低（每2小时75次）。API Key 提高至 100 req/min。Key 只存后端环境变量，不要写进前端 JS、公开仓库、截图或文章。

Hermes配置 (`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  lifi:
    url: "https://mcp.li.quest/mcp"
```

如需API Key提高Rate Limit:
```yaml
mcp_servers:
  lifi:
    url: "https://mcp.li.quest/mcp"
    headers:
      X-LiFi-Api-Key: "${LIFI_API_KEY}"
```

MCP Server是只读的：返回unsigned transactionRequest，不签名不广播。涉及Approve/签名/广播应交给隔离的钱包执行层。

MCP 暴露的工具：`get-chains`、`get-token`、`get-quote`、`get-allowance`、`get-status` 等。Agent 不需要自己拼 HTTP 请求。

⚠️ 自动化套利时，签名/广播交给隔离的钱包执行层 + 金额/滑点/Token/Bridge allowlist + 人工审批规则。

### Rate Limit

- 未认证: /quote和/advanced/routes各每2小时75次
- API Key: 100 req/min，Quote按2小时滚动窗口
- 超限返回HTTP 429

### 登记优惠

Bruce在推进专属套利场景优惠bps方案：
- 大套利团队联系: https://t.me/brucexu_eth
- 新团队登记: https://docs.google.com/forms/d/e/1FAIpQLScjhus2oM718UCkiT7zAi4qcnjPTeuh2e1gNxxJJFGsUZo2jg/viewform

---

## 五、MEV-Flashbot-Sandwich-RS — 以太坊三明治机器人

- **Repo**: https://github.com/theoweb3/mev-flashbot-sandwich-rs
- **类型**: MEV套利（三明治攻击）

### 技术特点

- Rust + Tokio异步运行时
- ethers-rs 以太坊交互
- WebSocket 实时监听mempool pending tx
- Flashbots 私有交易bundle提交
- AES-GCM 私钥加密存储

### 项目结构

```
src/
  main.rs      -- 启动WebSocket + 核心策略
  mev.rs       -- 三明治/套利等策略逻辑
  mempool.rs   -- Mempool监听
  tx_sender.rs -- 打包发送Flashbots Bundle
```

### 后续计划

Paxon 计划过两天实际安装跑一下 gate-crossex，验证跨所统一保证金的实际体验。

### 对共学的意义

这是**以太坊**的MEV实现，不是Solana的。但有以下参考价值：

1. **模块化设计**: mev策略/mempool/交易发送分离，方便扩展
2. **Rust实现参考**: 如果以后做Solana MEV bot（通过Jito bundle），Rust代码结构可借鉴
3. **概念对照**: 以太坊有公开mempool → 三明治可行；Solana无公开mempool → 需要Jito bundle + 私有订单流

---

---

## 六、LP过路费策略 — 从套利机器人身上套利

- **Issue**: https://github.com/w3player/arbitrage-playbook/issues/1
- **原帖**: https://x.com/hunterweb303/status/2084815706252841060
- **类型**: 价差+MEV交叉（LP收费池）

### 核心思路

常规路径卷不过套利机器人 → 换个方向，从套利机器人的路线上收过路费。

### 做法

在大涨大跌场景中，不和套利机器人抢价差。在机器人**经常经过的位置**（高流量交易对、反复穿越的价格区间）放置一个**高费率池**，收取套利机器人的过路费。

### 入场条件

- 爆量（交易量激增）
- 缺池（流动性枯竭，费率被推高）
- 剧烈波动（价格反复穿越LP区间）
- 反复穿越（机器人反复搬砖，持续贡献手续费）

### 风险

待补充（主要是无常损失、单边行情LP被搬穿）。

### 后续计划

Paxon 计划过两天实际安装跑一下 gate-crossex，验证跨所统一保证金的实际体验。

### 对共学的意义

这条思路的精妙之处在于**不卷速度**。承认自己在MEV层面卷不过专业团队，转而利用他们的存在本身作为收益来源。本质是：做套利机器人的对手盘（LP），而不是和它们同向竞争。

---

## 七、MEV vs API套利：补充分层

- **原帖**: https://x.com/theoweb33/status/2085177094376669441

在第一节"价差套利 vs MEV套利"的基础上，进一步分层：

| | MEV（链底层） | API套利（应用层） |
|---|---|---|
| **拼什么** | mempool监听、交易排序、Gas优化、Builder竞争 | 多DEX报价、价差发现、自动执行 |
| **需要什么** | 节点、低延迟基础设施 | 不需要节点，API即可 |
| **核心竞争** | 毫秒级链上优势 | 策略、资金、滑点管理 |
| **适合谁** | 专业团队（基础设施重） | 个人开发者 |
| **典型工具** | Flashbots、Jito、自建节点 | LI.FI、1inch、Jupiter API |

### 结论

个人开发者更适合先做**聚合套利、CEX-DEX套利**（API层），积累策略能力后再考虑MEV方向。一层一层往上打，不要跳过API层直接冲链底层。

---

## 连接

- `notes/tokenized-stock-arbitrage.md` — 币股套利（价差套利类）
- `notes/funding-fee-arbitrage-1token.md` — 资金费率套利（价差套利类）
- `notes/solana/atomic-arb-and-circular.md` — Solana原子套利
- `notes/mempool-and-ordering.md` — 排序权（MEV类）
- `notes/case-toll-fee-pool.md` — LP收费池（价差+MEV交叉）
- `notes/solana/transaction-model.md` — Solana vs Ethereum交易模型
