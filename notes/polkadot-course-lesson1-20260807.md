# Polkadot 智能合约课程 · 第一课（个人学习线，非共学）

> 来源：飞书云文档「第一课」https://qqpk3rr9ibj.feishu.cn/docx/MAwHdGPWZozbMyx9Ta5cM4Gxnwd
> 归档日期：2026-08-07（Hermes 记录，Paxon 群内分享）
> 标注：**个人学习线（Polkadot 生态），不属于链上套利共学内容**；与共学的关系见文末"交叉点"

## 课程主线

Solidity 开发者生态迁移到 Polkadot：
```
Solidity 代码 → Revive 编译器 → PolkaVM 字节码 → Asset Hub（pallet_revive）执行
```

## 一、智能合约 / Solidity / EVM 基础

- 智能合约基于用户交易执行，需跨节点一致；初始不可变但可升级（代理 Proxy 技术）
- 共识机制保证状态一致性；合约依赖链上状态
- 以太坊制定 ERC20/ERC721 标准；Solidity 静态类型检查减少运行时错误
- EVM：图灵完备、执行隔离、确定性要求；Gas 机制防死循环
- 精确执行保证节点一致性

## 二、Polkadot 1.0 → 2.0 智能合约演进

- **1.0**：Relay Chain 不支持智能合约，只能在平行链部署
- **2.0**：直接支持智能合约，Solidity 开发更便捷
- 进展：EVM → **PolkaVM**（提高执行效率）；**Revive** 编译部署 Solidity 到 PolkaVM；**Frontier** 生态维护旧数据与合约迁移
- 2.0 引入 REPL 工具；PolkaVM 支持多种字节码（不限于 Solidity）
- 交互方式：JavaScript 和 Rust（ParityRevive 包，前端后端都有用）

## 三、Asset Hub 原生 EVM 合约（核心）

优势：无需跨链通信、无需额外治理/新代币、MetaMask + Revive Remix + Ethers.js 可直接交互

| 组件 | 作用 |
|---|---|
| pallet_revive | 运行时模块处理以太坊风格交易；代理模拟 JSON RPC；交易转 Polkadot 兼容格式；无需改节点代码 |
| PolkaVM | RISC-V 架构，比 EVM 快；支持 Solidity/Rust/C；多维 Gas 计量 |
| Revive | Solidity → PolkaVM 编译器，兼容所有 Solidity 版本 |
| Revive Remix | Remix IDE 增强版（https://remix.polkadot.io/） |

### PolkaVM vs EVM

| 特性 | PolkaVM | EVM |
|---|---|---|
| 架构 | RISC-V 寄存器架构 | 堆栈 |
| Gas | 多维（计算/存储/证明大小） | 单一（过度收费） |
| 兼容性 | 以太坊工具（少量调整） | 仅 EVM 合约 |
| 语言 | Solidity/Rust/C | Solidity |

### Hermes 精确化补充

1. **多维 Gas 的意义**：EVM 单维 Gas 按最坏情况计价（storage/compute 混算），PolkaVM 分维计量 → 高频调用合约边际成本更低
2. **地址模型坑**：Asset Hub 的 EVM 地址映射 Substrate 账户体系（H160 ↔ SS58），MetaMask 可连但签名/交易走 pallet_revive 转换层——开发最容易踩坑处
3. **2.0 的意义**：从"发一条平行链才能跑合约"降级为"直接在资产中心部署"，门槛数量级下降

## 四、作业

1. IDE：https://remix.polkadot.io/（file explorer → Solidity compiler → Deploy）
2. **Subscan 通过 Block Hash 查询**：https://assethub-westend.subscan.io/
3. **Polkadot.js Apps 查询**：https://polkadot.js.org/apps（代码示例：查询测试网账户余额、查询主网）

## 五、学习资料清单（官方优先）

- Polkadot 官网 https://polkadot.network/ · 文档 https://polkadot.network/docs/
- ethers.js https://docs.ethers.io/ · polkadot/api https://polkadot.js.org/docs/api/
- Wiki https://wiki.polkadot.network/ · GitHub paritytech/polkadot + polkadot-evm/frontier
- 论坛 forum.polkadot.network · Reddit r/polkadot · Discord discord.gg/polkadot
- Web3 Foundation https://web3.foundation/ · Medium blog

## 六、工作方向对照表（以太坊 → Polkadot）

| 方向 | 以太坊 | Polkadot 对应 | 技能 |
|---|---|---|---|
| 公链/合约 | Ethereum | Polkadot/Kusama/Astar/Moonbeam | Solidity、Rust、Ink! |
| DeFi | Aave/MakerDAO/Uniswap | Acala/Parallel/Bifrost/HydraDX | Solidity、Rust、跨链合约 |
| NFT | OpenSea/Rarible | Unique Network/RMRK/Efinity | 合约 + Web3 前端 |
| L2 | Optimism/zkSync/Arbitrum | Astar/Manta | ZK、Rollup |
| 跨链桥 | Polygon Bridge/LayerZero | BridgeHub/Darwinia | XCM、Substrate |
| 隐私/ZK | Aztec/Secret | Manta/Phala | ZK 开发 |
| 存储 | Filecoin/Arweave | Crust | IPFS、去中心化云 |
| DID | ENS/Civic | KILT | 身份认证 |
| DAO | Aragon/DAOstack | Collectives Polkadot | 治理工具 |

## 与个人技术线/共学的交叉点

- **Rust 直接可用**：PolkaVM 支持 Rust 写合约 → 无需新语言即可进入 Polkadot 合约开发（与 solana-rs 的 Rust 线复用）
- **套利视角**：Asset Hub 原生 EVM = Polkadot 上的 EVM 流动性；未来跨 Solana-Polkadot 桥/流动性出现 = "新链新池子"信息差机会（与共学监控体系同型）
- **Gas 成本**：若 PolkaVM Gas 显著低于 EVM，高频策略（套利/三明治）在 Polkadot 的成本结构更友好——持续跟踪

## 下一步（可选）

- ✅ ~~用 Polkadot.js Apps 实际完成作业：查询 Westend 测试网账户余额~~（2026-08-07 已完成，见下）
- 部署一个最简单的 Solidity 合约到 assethub-westend，Subscan 用 block hash 验证（链上证据习惯复用）

## 作业完成记录（2026-08-07，裸 RPC 方式）

**Westend 余额查询**（`scripts/westend_balance.py`，对照 Solana）：

| 维度 | Substrate (Westend) | Solana |
|---|---|---|
| 方法 | `state_getStorage(System.Account)` | `getBalance(account)` |
| 键 | twox128("System")+twox128("Account")+blake2_128_concat(pubkey) | 账户模型原生支持余额查询（无需构造键） |
| 地址 | SS58 编码（base58+校验） | base58 |
| 单位 | Planck（1 WND = 1e12 Planck） | lamports（1 SOL = 1e9） |
| 余额结构 | AccountInfo：free/reserved/frozen 多档 | 单一 lamports |

- 实测：`system_chain` = Westend；Alice 开发账户（d43593c7...）在 Westend 不存在（存储为空 = 余额 0，合理）
- 踩坑：Westend HTTP RPC 方法名用**下划线**（`system_chain`），`system.account`（点号）Method not found；余额必须走 `state_getStorage` 而非直接的 account 方法（该节点未开放）
- Westend 公共 RPC（westend-rpc.polkadot.io）**国内直连可用**，比 Solana 公共 RPC 还友好
- Python 3.9 LibreSSL 对 westend-rpc 的 TLS 握手失败（TLSV1_ALERT_PROTOCOL_VERSION）→ RPC 调用改用系统 curl 子进程绕过
