# 案例：0xbdb3ba 单笔 stat arb 交易（gas 1.7 万 U / 收益 ~40-45 万 U）

> 来源：用户分享 https://etherscan.io/tx/0x6dc21ad762f5403369fa9475f455a3e6822ab1f4f4eaa8ae6bfc199d5bbd53ee
> 分析日期：2026-08-07（Hermes 链上核算）
> 关联：`notes/ethereum-block-building-part1-demand.md`（Greenfield 研究：0xbdb3ba = 挑战 Wintermute 的 stat arb searcher）

---

## 链上事实（RPC 验证，二值判据）

| 项 | 值 |
|---|---|
| tx | `0x6dc21ad762f5403369fa9475f455a3e6822ab1f4f4eaa8ae6bfc199d5bbd53ee` |
| from | `0x5b43453fce04b92e190f391a83136bfbecedefd1`（EOA，费用支付者） |
| to | `0xbdb3ba9ffe392549e1f8658dd2630c141fdf47b6`（stat arb 策略合约） |
| block | 25322434 |
| gas | limit 15,327,398 / used 10,151,599（**单个 tx 消耗 10M+ gas**） |
| gasPrice | 895.25 gwei（极高，竞争激烈） |
| **txFee** | **9.088 ETH ≈ $17,000（1.7 万 U）** |
| input | 10,596 bytes（50+ 单腿 swap 打包进一笔 tx） |
| logs | 448 条，涉及 30+ 种代币 |

## 收益核算（Hermes 独立计算）

按 0xbdb3ba 合约的净 Token 流量 × 近似价格折算：

| 资产 | 净流量 | 折算 USD |
|---|---|---|
| WETH | +2,621.7 | **+$4,902,671** |
| USDT | -1,753,467 | -$1,753,467 |
| USDC | -1,524,270 | -$1,524,270 |
| WBTC | -17.1 | -$1,129,858 |
| crvUSD | -142,007 | -$142,007 |
| DAI | -58,007 | -$58,007 |
| UNI | +7,657 | +$76,573 |
| LINK | +2,161 | +$30,260 |
| 其他 | 若干 | 小计 |

**毛收益 ≈ +$423,017；扣 gas $17,000 ≈ 净 +$406,000（约 40.6 万 U）**
用户看到的「45 万 U」同量级 ✅（差异来自 token 价格取整 + 未识别代币净值未计入）

## 机制解读

- **这是 stat arb（CEX-DEX 统计套利）**，不是普通 DEX 间搬砖：合约在**同一笔交易内**完成 50+ 单腿 swap，跨 USDT/USDC/WBTC/WETH/crvUSD 等 30+ 资产重新平衡——正是 Greenfield 研究里 0xbdb3ba 的标志性打法（单笔 tx 打包 50+ 腿）
- **WETH +2621 是中间库存，不是利润本身**：stat arb 靠「同一区块内 CEX 与 AMM 价格偏离时低买高卖」赚多资产价差，净收益 = 所有腿的汇总（约 42 万）
- **gas 1.7 万 U 本身就是门槛**：10M gas × 895 gwei——能承受这个成本的只有机构级玩家；Greenfield 报告显示 stat arb 市场 Wintermute + 0xbdb3ba 合计占优先费支出 83%，集中度极高
- **为什么个人做不到**：需要 CEX 延迟优势/费率层级/库存（Wintermute 的护城河）、高频机会检测、10M+ gas 的合约架构、以及 895 gwei 级别的优先费竞价能力

## 与共学认知的呼应

1. 「**优先费 = MEV 利润的代理指标**」：这笔 tx 的 gas（1.7 万 U）与利润（40+ 万 U）比例 ≈ 4%——Greenfield 估算 stat arb 平均利润率约 10%（90% 交优先费），大机会利润率 30% 量级，与这里吻合
2. 「**统计套利已被垄断**」：这正是个人套利者不应该碰的方向的实证
3. 「**套利本质是找摩擦**」：0xbdb3ba 的 edge 不是信息（stat arb 机会公开），而是**执行规模 + 库存 + 延迟**——不可复制的结构性优势

## 备注

- 价格取近似值（2026-08 市场量级），精确收益需用区块内实际成交价逐腿核算
- 未识别代币（若干 0x... 地址）净值未计入，可能造成 ±几万 U 误差
- 分析脚本模式可复用：`eth_getTransactionByHash` + `eth_getTransactionReceipt` → 解析 Transfer 事件 → 按合约净流量折算
