# Term Finance 治理攻击链上取证（$8.5M，2026-08-23）

> 来源：Defimon 检测帖（@term_labs 受害者）+ 用户转发的 2 笔交易 + 2 个攻击者地址
> 取证日期：2026-08-23 ｜ 取证人：Hermes（ETH 主网 RPC 直连 ethereum-rpc.publicnode.com）
> 关联：`notes/mistaken-limit-order-arb-line-20260822.md`（规则/治理套利反面）、D19 对比表（事件驱动方向）、近期治理攻击系列（BonkDAO $20M / Compound $24M / BarnBridge $777K）

## 攻击模式（一句话）

**攻击者低价收购持有量稀少的 DAO 治理代币 → 通过恶意提案让 Term 金库（Gnosis Safe）启用攻击者控制的恶意模块 → 模块绕过 owner 签名直接提取金库资产。**

这是**治理攻击**（governance attack），不是合约漏洞 exploit——攻击的是「治理流程」而非「代码缺陷」。与 BonkDAO（$4.4M 买 1% 供应过 quorum 偷 $20M）、Compound（$24M）、BarnBridge（$777K）同族。Blockaid 统计：8 周内 7 个协议被治理攻击卷走 ~$22M。

## 链上证据链（RPC 取证）

### Tx1: 0xd354a15b...4129（from: 0xa908b3472d76...）
- **to**: 0x64e477800051efb06ae4086f4b258b270668b4df（145 字节 = **SafeProxy**）
- **status: 1（成功）** | gasUsed 2,802,767 | 78 条日志
- **🔴 log[0]**: `EnabledModule(module=0x0ae12af3878a2d896f5c4dce3be7250fb187c0a6)` @ Safe 0x35c99cf4a5df2d9bcd822bee32676d9590229e33
  - 模块 = **833 字节自研实现合约**（非标准 Safe 模块）→ 攻击者控制的后门
  - 恶意提案的执行结果：给金库 Safe 装上「无需签名即可转钱」的模块
- 后续 WETH 44.37 循环（0x4d5f47fa → 0x33073258 → 0x26fcb50e）显示模块在搬运资产

### Tx2: 0x9f273f9a...8a0（from: 0x686457a7468b...）
- **to**: 0x4f4b614d2aa533e6e3b11a6a32295bd147eba17f（145 字节 = SafeProxy）
- **status: 1（成功）** | 159 条日志
- **7 个不同 Safe 金库各启用 1 个恶意模块**（EnabledModule ×7，模块地址各不相同：0x0b9f1296 / 0x4874eed7 / 0xb33153fc / 0x0d149c53 / 0x1c731c75 等）
- **USDC 提取流水**（每笔都走「来源合约 → 中间合约 → 恶意模块 → 攻击者」四跳）：
  - $14,132 + $14,172 + $348,877 + $200,276 + $324,011 + $324,124 + $848,411 + $454,046
  - **合计 ≈ $2.55M**（Tx2 单笔内），全部流向攻击者 0x686457a7
- 资产来源合约 0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb（15623 字节复杂合约 = Term 金库聚合）

### 攻击者
- 0xa908b3472d76e7744bab0a5911768a4a6300612b（Tx1 发起，治理收购 + 提案）
- 0x686457a7468b9b31c5dba43b1b16077b48520691（Tx2 提取，资金归集）
- 当前 ETH 余额 ~0.0001/0.0002（已洗走或转 ERC20）

## 与我们的知识库互证

| 攻击要素 | 我们的认知 | 结论 |
|---|---|---|
| 低价收治理代币 → 过 quorum | 规则套利=利用「规则设计的失衡」 | 治理攻击是规则套利的恶意版 |
| 金库用 Gnosis Safe + 模块机制 | Safe 模块 = 权限扩展点 | **审计盲区**：模块可绕过 owner 多签 |
| 事件驱动 | D19「事件驱动=吃尸体」方向 | 攻击后受害者代币暴跌/金库被掏 = 波动窗口 |
| 与 CEX 套利无关 | 纯链上治理层 | 对我们的策略线是「风险提示 + 事件素材」 |

## 对我们策略的意义（3 条）

1. **风险提示**：任何「DAO 治理代币 + 金库 Safe」的项目，若治理代币分散（quorum 低）→ 攻击面大。我们未来若评估持有治理代币（如 HIP-3/PM 生态），先查 quorum/时间锁/模块清单
2. **事件驱动素材**：治理攻击 = 代币暴跌 + 金库资产抛售窗口（类似下架/插针）——极端事件是「吃尸体」候选场景，可纳入事件雷达的监控类别（当前监控：下架/清算/上币，可加「治理攻击」类别）
3. **Safe 模块审计法**：取证方法论沉淀——查 Safe 金库先调 `getModules()`（0xa0e67e2b？本次 eth_call revert，可能是 Safe 版本差异），攻击特征 = `EnabledModule` 事件 + 自研模块合约（非 Gnosis 官方模块）

## 取证方法（可复用）

- ETH 主网 RPC 直连（ethereum-rpc.publicnode.com）绕代理 SSL 问题；blockscout/etherscan API 被代理挡 → 走 RPC + receipt logs
- 攻击交易特征识别：`EnabledModule` 事件（0xecdf3a3e...）+ to=SafeProxy（145 字节）+ 恶意模块非标准实现 + 大额 USDC 四跳转移
- 4byte.directory 查事件签名（EnabledModule/Withdraw/Transfer 快速定罪）

## 待办

- [ ] 事件雷达加「治理攻击」监控类别（X 帖/Defimon 类安全监测源）
- [ ] Safe 金库审计清单：getModules() 正确调用方式 + 模块合约校验（官方 vs 自研）
