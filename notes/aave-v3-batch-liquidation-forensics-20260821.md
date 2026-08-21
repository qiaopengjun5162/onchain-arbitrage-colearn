# Aave V3 批量清算交易取证（2026-08-21 群分享）

> 来源：https://etherscan.io/tx/0x25552f9d622ad99070e0bfa595142c7a88a4744b0ae6055c0a0bacc3e630f4ee
> 归档日期：2026-08-21 ｜ 方法：ETH 公共 RPC + blockscout + 4byte 事件签名库

## 交易画像

- **链**：Ethereum 主网 ｜ **状态**：成功 ｜ gas 2,416,565 @ **0.1 gwei**（flashbots 私有交易特征，总成本仅 $0.78）
- **from**：`0xf1c4ce71…`（EOA 清算人）｜ **to**：`0xea6d5b39…`（清算执行合约，未公开命名 = 私有 bot）
- **method**：`0x398a7da0`（私有合约入口，4byte 未收录）
- **logs**：97 个

## 定性：Aave V3 闪贷清算 bot——一笔交易清算 6 个仓位

### 关键证据

1. **LiquidationCall 事件 ×6**（`0xe413a321e8681d831f4d...`）——Aave V3 标准清算事件，清算人全部 = `0xea6d5b39`（to 合约）
2. **被清算仓位 6 个**：

| # | 抵押品 | 债务 | 被清算地址 | debtToCover | 清算量 |
|---|---|---|---|---|---|
| 1 | WBTC | WETH | 0x1ded4809 | 87.29 WETH | 0.294 WBTC |
| 2 | WETH | wstETH | 0xa1b9f5b8 | 19.42 WETH | 25.15 WETH |
| 3 | WETH | wstETH | 0x7d84a568 | 2.84 WETH | 4.27 WETH |
| 4 | WBTC | WETH | 0xbabbb7a7 | 1.77 WETH | 0.006 WBTC |
| 5 | WETH | wstETH | 0xdc51882c | 0.003 WETH | 0.004 WETH |
| 6 | sUSDe | WETH | 0x63365304 | 0.003 WETH | 5.35 sUSDe |

3. **Aave 支持事件**：`ReserveDataUpdated`（利率更新 ×14）、`Burn`（aToken 销毁=清算人收抵押品）、`Mint`、`ReserveUsedAsCollateralDisabled`（抵押品标志关闭）
4. **Uniswap V3 Swap ×5**（0x4585fe/0x109830/0xc7bbec/0x7eb593）+ **Uniswap Universal Router**（0x0000…0004）= 闪贷还债路径
5. **token 流**：WETH → WBTC → wstETH → USDT → sUSDe 多池链式 swap——闪贷（Aave 借）→ 清算 → swap 还款 → 利润归清算人

### 经济结构

- 6 个仓位批量清算，多数是**小仓位**（#5 #6 是 dust 级 $1-10）——清算 bot 连 dust 都不放过（Aave 规则：partial liquidation 后必须留 ≥$1000，否则全清）
- 清算人收益 = 清算折扣（Aave V3 通常 5-10%）− 闪贷费（0.05%）− gas（$0.78 几乎可忽略）
- flashbots 私有交易 = 避免被其他 bot 抢（MEV 竞争）

## 方法论沉淀

1. **LiquidationCall 事件 = 清算交易的指纹**（4byte 一查即定罪，比猜合约名快）
2. **0.1 gwei gas = flashbots 私有交易** = MEV bot 特征（普通用户不会用这么低的 gas 优先级）
3. **清算利润模型**：折扣（5-10%）− 闪贷费（0.05%）− gas——**这就是清算套利的经济学**，与我们 4 方向第 4 名（清算）直接相关
4. 连 dust 仓位都清 = 专业清算 bot 的扫描粒度（我们雷达也要覆盖 dust）

## 与我们方向的关系

- **这是 Aave 清算 bot 的真实操作样本**——我们🥉4 方向「清算（含拍卖）」的实证参考：bot 用闪贷 + 多池 swap 完成清算，gas 成本近乎为零（flashbots），利润全靠折扣
- 可提取：清算执行的标准路径（LiquidationCall → swap 还款 → 利润归己）
- 与 Solana 侧（Maker 哨兵/清算监控）形成 EVM 对照样本

## 结论

- **这是 Aave V3 清算机器人**（私有 bot，一笔 6 仓位），不是用户手工操作
- 对我们：清算方向的可执行路径实证（闪贷+多池+flashbots 三件套）；「连 dust 都清」提示雷达覆盖粒度
- 无新研究动作；归档为清算方向参考样本
