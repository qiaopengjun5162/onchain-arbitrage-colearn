# Term Finance 治理攻击链上取证（~$8.5-9.3M，2026-08-23）

> 来源：Defimon 检测帖（@term_labs 受害者）+ 用户转发的 2 笔交易 + 2 个攻击者地址 + **Phalcon 权威分析（用户补充）**
> 取证日期：2026-08-23 ｜ 取证人：Hermes（ETH 主网 RPC 直连 ethereum-rpc.publicnode.com）+ Phalcon 机制确认
> 关联：`notes/mistaken-limit-order-arb-line-20260822.md`（规则/治理套利反面）、D19 对比表（事件驱动方向）、近期治理攻击系列（BonkDAO $20M / Compound $24M / BarnBridge $777K）

## 攻击模式（一句话）✅ Phalcon 确认版

**攻击者用 0.5 ETH（~$951）买入 0.4852 股金库份额（pcETH/pcUSDC 等）→ 质押 → 拿到 90.66% 投票权 → 通过 TokenVoting 恶意提案获得金库控制权 → 对每个独立金库逐个执行提款。**

这是**治理攻击**（governance attack），攻击的是「治理流程」而非「代码缺陷」。与 BonkDAO（$4.4M 买 1% 供应过 quorum 偷 $20M）、Compound（$24M）、BarnBridge（$777K）同族。Blockaid 统计：8 周内 7 个协议被治理攻击卷走 ~$22M。

## 攻击成本（关键数据，Phalcon/链上确认）

| 项 | 值 | 含义 |
|---|---|---|
| 攻击买入 | **0.4852 股份额，0.5 ETH（8/17 约 $951）** | 攻击总成本 |
| 质押供应量 | 0.5352 股（占 2838.95 股总量的 **0.019%**） | 资金流失前区块上质押的量 |
| 攻击者投票权 | **90.66%** | 0.4852/0.5352 质押份额 |
| 未质押占比 | **99.94% 股份持有者从未质押** | 145 小时无投票 |
| 受害者反应 | 资金流失 **94 分钟后**（今早 7:59）才质押 | 亡羊补牢，太迟 |

**为什么 $951 能撬动 $8.5M+**：投票权只看**质押**份额，不质押 = 没投票权。99.94% 持有者从不质押 → 实际投票权池只剩 0.019% 供应量 → 攻击者 $951 买的 0.4852 股就是 90.66% 投票权。**这不是「低价收购 DAO 代币」（BonkDAO 模式），是「金库份额质押投票权俘获」——投票参与率趋近于零才是根本原因。**

## 根本原因：资产分散在多个独立金库

| 金库 | 份额代币 | 底层资产 | 攻击 tx |
|---|---|---|---|
| Parity Core ETH | pcETH | WETH (Morpho) | Tx #1（2,841 WETH ≈ $6.8M） |
| Parity Core USDC | pcUSDC | USDC (Morpho) | Tx #2 |
| Parity High Yield USDC | pcHYUSDC | USDC (Morpho) | Tx #2 |
| （+ HYUSDCv2 / RockX Tori 等 TSV） | pcHYUSDC / roxTORI | 各类底层 | Tx #2 |

**合计 ≈ $9.3M（Defimon 报 $8.5M，口径差异在结算时点/价格）**

## 为什么是 2 个 tx（金库结构决定）

- 每个金库是**独立合约**（pcETH / pcUSDC / pcHYUSDC 是不同的 vault），提款逻辑单独执行
- Tx #1 处理 pcETH（WETH）；Tx #2 处理 pcUSDC + pcHYUSDC + 其他 TSV（USDC）
- **Tx #2 不是「第二波」，是「第二个金库」**——攻击者用同一个治理权限，对每个金库分别执行提款
- Defimon 列 2 个 tx = 2 个（组）金库，不是 2 波攻击

## 链上证据链

### Tx1: 0xd354a15b...4129（from: 0xa908b3472d76...）
- **to**: 0x64e477800051efb06ae4086f4b258b270668b4df（145 字节 = SafeProxy）
- **status: 1（成功）** | gasUsed 2,802,767 | 78 条日志
- 提取 **2,841 WETH ≈ $6.8M**（pcETH 金库，Morpho 底层）
- log[0] `EnabledModule`（0x35c99cf4）为提案执行过程中的 Safe 模块变更（机制细节：提案执行可能升级金库实现/改 owner/启用模块以取得执行权）

### Tx2: 0x9f273f9a...8a0（from: 0x686457a7468b...）
- **to**: 0x4f4b614d2aa533e6e3b11a6a32295bd147eba17f（145 字节 = SafeProxy）
- **status: 1（成功）** | 159 条日志
- **攻击链（Phalcon 确认）**：
  - 攻击者2 → 0x4f4b614d（攻击合约）
  - → `ERC1967Proxy.execute(_proposalId=0)` ← 治理提案执行
  - → `TokenVoting.execute(_proposalId=0)` ← Aragon TokenVoting 投票
  - → 批量操作（multiCall）：
    - tsvParityPrimeUSDC 赎回 pcUSDC → USDC（-13,964 pcUSDC）
    - tsvParityCoreUSDC 赎回 pcUSDC → USDC（-14,003 pcUSDC）
    - tsvParityHYUSDCv2 / tsvParityHYUSDC 赎回 pcHYUSDC（-836,611 / -344,025 pcHYUSDC）
    - tsvRockXToriUSDC 赎回 roxTORI（-452,688 roxTORI）
    - Morpho 提取 USDC（**-$1,679,639 USDC**）
  - 全部 USDC → 攻击者2（+$1,679,639 USDC 归集）
- 每笔走「TSV → 中间合约 → 攻击者」的赎回结构（RPC 看到的 4 跳 = 赎回链，不是模块转账）

### 攻击者
- 0xa908b3472d76e7744bab0a5911768a4a6300612b（Tx1 发起，治理收购 + 提案）
- 0x686457a7468b9b31c5dba43b1b16077b48520691（Tx2 提取，资金归集）
- 当前 ETH 余额 ~0.0001/0.0002（已洗走或转 ERC20）

## 与我们的知识库互证

| 攻击要素 | 我们的认知 | 结论 |
|---|---|---|
| $951 买份额质押→90.66% 投票权 | 规则套利=利用「规则设计的失衡」 | 治理攻击是规则套利的恶意版；**质押参与率≈0 比份额流动性更致命** |
| 控制治理层=控制所有金库 | 权限集中 = 单点失效 | 金库分散 ≠ 风险分散（治理层集中） |
| 事件驱动 | D19「事件驱动=吃尸体」方向 | 攻击后受害者代币暴跌/金库被掏 = 波动窗口 |
| 与 CEX 套利无关 | 纯链上治理层 | 对我们的策略线是「风险提示 + 事件素材」 |

## 对我们策略的意义（3 条）

1. **风险提示**：任何「份额代币质押治理 + 多金库」的项目（Term/Parity 模式），**质押参与率≈0 = 投票权可被 $1K 级成本俘获 → 掏空所有金库**。我们未来评估持有任何份额代币/治理代币，先查：**质押率、投票权分布、quorum、提案时间锁、金库权限结构**（质押率比持有分散度更关键）
2. **事件驱动素材**：治理攻击 = 代币暴跌 + 金库资产抛售窗口——「吃尸体」候选场景，可纳入事件雷达（当前监控：下架/清算/上币，可加「治理攻击」类别）
3. **取证方法论沉淀**：攻击特征 = `TokenVoting.execute` + 提案执行 + 多金库批量赎回 + `EnabledModule`（提案执行伴随的权限变更）；金库份额代币低流动性是前置条件

## 取证方法（可复用）

- ETH 主网 RPC 直连（ethereum-rpc.publicnode.com）绕代理 SSL 问题；blockscout/etherscan API 被代理挡 → 走 RPC + receipt logs
- 交易特征识别：to=SafeProxy（145 字节）+ `TokenVoting.execute` 提案执行 + 多 TSV 赎回 + 大额 USDC 归集
- 4byte.directory 查事件签名（EnabledModule/Withdraw/Transfer 快速定罪）
- **RPC 推断 vs Phalcon 确认的差异教训**：仅凭 logs 推「模块后门」是过度推断；机制判定应以权威工具（Phalcon/Blockscout trace）为准，RPC 证据做佐证

## 待办

- [ ] 事件雷达加「治理攻击」监控类别（X 帖/Defimon 类安全监测源）
- [ ] 份额代币治理风险检查清单（投票权分布/quorum/时间锁/金库权限）→ 用于未来任何份额代币评估
