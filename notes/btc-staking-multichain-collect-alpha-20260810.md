# 多链收集型 alpha：跨链 meme 入口 + BTC 质押凭证多链（2026-08-10）

> 来源：Paxon 口述想法（2026-08-10 群内）：①充值一个链买不同链 meme 的多链钱包；②质押 BTC 可在不同链提款的凭证（有手续费）——「主要靠日常收集」
> 状态：工具地图 + 机制拆解（待数据验证），先记后验
> 定位：确定性失衡时刻 + 容量内敞口 + 小幅优势复利——「日常收集」型 alpha

## 方向一：多链钱包 / 跨链 meme 入口

**本质**：fund-on-any-chain, buy-anywhere 的跨链意图执行（intent-based bridging + swap）。底层是跨链意图协议，钱包只是入口。

工具地图：
| 工具 | 类型 | 覆盖 | 备注 |
|---|---|---|---|
| MetaMask Swaps | 钱包内置跨链 swap | ETH/BTC/Solana/BNB 等 | 一次授权跨链兑换，报价聚合多家做市商 |
| GMGN (gmgn.ai) | meme 一站式（数据+执行） | Solana 为主 | 聪明钱追踪+交易执行，meme 场景专用 |
| Moonshot | meme 一站式 | Solana 等 | 数据整合+自动路由 |
| OKX Wallet / Bitget Wallet | 多链钱包+内置跨链聚合 | 30+ 链 | XDeFi 类聚合，各链 meme 入口 |
| Socket / LI.FI / Mayan / Across | 跨链意图协议（底层） | 多链 | 真正的「一条链的钱买另一条链的资产」执行层 |

**成本结构**（决定日常收集是否成立）：目标链 swap 费 + 跨链费（LI.FI 固定 0.25% 地板，见 day6 实验）+ Gas。跨链意图执行 ≈ 两层摩擦叠加 → 小额高频会被成本吃掉，**只有「跨链费补贴期」（钱包/协议获客补贴）或「同链可直接买」时才成立**。

## 方向二：BTC 质押凭证多链（核心）

### SolvBTC（Solv Protocol）
- 1:1 BTC 储备代币，11 链（BNB Chain / Ethereum / Merlin / Core / Soneium 等），TVL $415.83M（30 天 +6.3%）
- Wallet Partners 35（含 OKX / Binance / MetaMask），用户 1.2M，集成 325 项目
- 有 Mint/Redeem Fees（协议收入结构可见）
- xSolvBTC 变体：即时赎回 + 连续收益

### LBTC / BTC.b（Lombard，Babylon staking）
- LBTC：生息 BTC（Babylon 质押），10+ 链：Ethereum/Base/Arbitrum/BNB/Sonic/Sui/Monad/MegaETH/Stable/Katana/Ink（原生 CCIP 双保险）+ Solana（CCIP）+ Berachain/Scroll/Mantle
- BTC.b：非生息 bridged BTC（同一 Security Consortium 背书）
- 跨链机制：**Chainlink CCIP + Symbiotic 经济担保层**；burn-and-mint 跨链（源链 burn → 目标链 mint），总供应恒定
- 桥费：源链 gas + CCIP/LayerZero 消息费 + 目标链 gas——**协议声明不另收桥费**（隐藏成本是 basis risk）
- TVL 分布（DefiLlama）：Bitcoin $726.46M / Ethereum $7.52M / Base $3.31M / BSC $21.9K / Corn $0——**同一凭证在链间 TVL 差 3 个数量级 = 流动性不对称**
- 2025-07-22 起 LBTC 转 auto-compounding exchange-rate yield → 兑换率随收益增长，**不同链池价格天然不同步**

## 「日常收集」的套利逻辑（关键判断）

**可套利的前提 = 强制收敛机制**（笔记020 教训：相似 ticker 不构成收敛，必须有强制收敛机制）：
- ✅ LBTC/solvBTC 跨链 **burn-and-mint** = 有强制收敛（1:1 兑回 BTC + 跨链铸造使总供应恒定）→ 链间折溢价是**可回归的价差**（套利）
- ❌ 不同发行方的 BTC 凭证（LBTC vs solvBTC vs WBTC）之间 = **relative value**（无强制收敛，各自赎回机制独立）→ 不是套利，是方向判断
- ⚠️ 同凭证跨链虽然可收敛，但**收敛路径要经过赎回/铸造**（LBTC 赎回最长 10 天）→ 收敛速度取决于 burn-and-mint 桥的即时性 vs 赎回时长

**成本门槛**：链间价差 > 跨链桥费（CCIP 消息费 + 双端 gas）+ 滑点 + 目标链 swap 费 才有「收集」价值。跨链桥费通常远低于 LI.FI 聚合（CCIP 直连无 0.25% 服务费）——**这才是「日常收集」成立的结构性原因**：直连桥的摩擦低于聚合器。

**「充值一个链买不同链 meme」的真相**：钱包/聚合器会把跨链费加进报价（0.25%+），meme 本身滑点又高（5-20%）——**买 meme 场景跨链入口的日常收集价值低，直接在该链买 + 资金预置才是正解**（Trade First, Rebalance Later，笔记044 结论同构）。

## 风险（先讲尾部，后讲收益）

1. **赎回时间敞口**：LBTC unstake 最长 10 天——折溢价存在期间「搬过去」后无法快速回归，可能被套在中间（与吃尸体同构：收敛时间不由你定）
2. **slashing**：Babylon 已引入 0.1% slashing risk——质押凭证的隐含安全税
3. **basis risk**：auto-compounding 汇率制下，同凭证不同链的「兑换率」可能不一致（协议升级导致的结构性价差，非套利机会）
4. **小所/小链流动性**：TVL $21.9K 的链上池子（BSC LBTC）——报价虚高=假信号（无套利带雷达的深度过滤教训）
5. **无收敛凭证 = 赌博**：LBTC↔solvBTC↔WBTC 互搬是相对价值押注，不是套利

## 验证待办

- [ ] solvBTC / LBTC 各链实时价格差采集（CoinGecko 多链价格或 DEX 池价）——验证「日常收集」价差量级是否 > 桥费
- [ ] CCIP 直连桥费实测（Lombard bridge 界面/文档给的真实费用 vs LI.FI 0.25%）
- [ ] LBTC burn-and-mint 的收敛速度实测（小额跨链测试，观察到账时间）
- [ ] 钱包跨链买 meme 的总摩擦实测（MetaMask Swaps / OKX Wallet 报价 vs 直接链上买）
- [ ] GMGN/moonshot 是否支持 Base 链 meme（多链覆盖现状）

## 关联

- `notes/day6-lifi-quote-compare-20260810.md`（0.25% 跨链费地板——「日常收集」的成本基线）
- `notes/colearn-incremental-137-digest-20260810.md`（笔记020 资产身份/强制收敛；笔记044 Trade First）
- `notes/arb-risk-black-swan-20260809.md`（尾部风险框架）
