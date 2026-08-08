# 币股发行方间价差验证：bNVDA vs NVDAx（负结果）

日期：2026-08-06
状态：研究（只读验证）
结论：**假价差，无流动性**

## 实验过程

### 1. 发现表面价差

LI.FI Token Service 显示同一只 NVDA 的不同发行方版本（全部 verified）：

| 版本 | LI.FI 标价 | 相对 NVDAx |
|---|---|---|
| NVDAx | $220.20 | 基准 |
| NVDAon | $220.99 | +0.4% |
| wNVDAx | $218.06 | -1.0% |
| **bNVDA** | **$204.56** | **-7.1%** |
| **wbNVDA** | **$205.98** | **-6.5%** |
| NVDA | $623,070 | 数据错误 |

表面看 bNVDA 折价 7%，符合"发行方间价差"（tokenized-stock-arbitrage.md 路线 D）的假设。

### 2. 验证可执行性

**直接 swap（bNVDA → NVDAx）**：无报价 ❌
**卖腿（bNVDA → USDC）**：无报价 ❌
**买腿（USDC → NVDAx）**：205 USDC → 0.9286 NVDAx ✅

### 3. 结论

**bNVDA 没有流动性，7% 价差不可执行，是假价差。**

- bNVDA 只有买入报价没有卖出报价（或反之），单边市场
- LI.FI 的 priceUSD 来自 CoinGecko，可能取的是最后一次成交或做市商报价，不代表可成交价格
- **verified 只代表合约真实性（Hypernative 验证），不代表价格有效性**

## 教训

1. **永远用 swap quote 验证价差，不要信 token price 表**。价差要能"成交"才算数。
2. **单边市场 = 假价差**。买得到卖不出的"折价"没有任何意义。
3. 这正是"幻觉价差"的机制解释：数据源显示的价格 ≠ 可成交价格。
4. CoinGecko 脏数据（NVDA $623K）说明第三方价格源需要交叉验证。

## 对币股 D 路线的影响

不是否定路线 D，而是修正假设：
- 发行方间价差**真实存在**（bNVDA 确实便宜 7%）
- 但**流动性是执行前提**，先查两个版本各自的买卖盘深度
- 可行的是**有活跃交易的发行方对**（如多个主流版本之间），bNVDA 这种边缘版本是死池

## 下一步

- 对比其他发行方对：NVDAx / NVDAon / wNVDAx 之间的真实 swap quote
- 用 /advanced/routes 找多跳路径（如 bNVDA → USDC → NVDAx 如果未来有流动性）
- 检查 bNVDA 在 Binance Web3 是否有独立买卖盘（BN 自家流动性可能不走 LI.FI）

## 追加：主流版本流动性验证（2026-08-06 下午）

### 实测可成交价格（LI.FI quote，非 CoinGecko 标价）

| 版本 | 买价 (USDC→token) | 卖价 (token→USDC) | 往返成本 |
|---|---|---|---|
| NVDAx | $220.78 | $219.23 | -0.70% |
| NVDAon | 无报价 | $219.21 | - |
| wNVDAx | $218.76 | $217.26 | -0.69% |

### 版本间价差（以卖出价为基准）

- NVDAx vs wNVDAx: **0.90%**
- NVDAx vs NVDAon: 0.01%
- NVDAon vs wNVDAx: 0.89%

### 直接转换路径

wNVDAx → NVDAx 有直接 swap（kyberswap）：**1 wNVDAx → 0.9885 NVDAx**（折价 1.15%）

### 结论

- 当前价差 0.9% < 转换成本 1.15% → **目前不可套利**
- 但**接近临界点**：价差扩大到 1.15%+ 或转换成本下降即触发
- 需要持续监控这个对（wNVDAx/NVDAx 是候选监控对象）
- NVDAon 与 NVDAx 几乎零价差（同流动性来源），不是监控目标
