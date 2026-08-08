# Polymarket TWAP 结算变更 + $1M 流动性奖励（Leo 实测拆解）

> 来源：https://x.com/runes_leo/status/2085585584886817200（Paxon 分享 2026-08-08）
> 作者：Leo｜一个人 + AI（@runes_leo），博客 leolabs.me

## 背景：Polymarket crypto up/down 改成 TWAP 结算 + $1M 奖励

原来结算：比开盘/收盘「那一刻」的单点价格 → 尾盘几秒砸一下就能翻方向（盘薄成本极低）=「尾盘翻转」攻击
现在：两端都看 Chainlink **30 秒 TWAP feed**（加权均价）→ 翻方向要推整个 30 秒均价，成本量级完全不同

## 窗口映射（实测 59 个市场，非文档口径）

| 市场时长 | TWAP 窗口 |
|---|---|
| 5m | 30 秒 |
| 15m | 60 秒 |
| 4h | 60 秒 |

坑：不是「30/60 两个窗口同时用」，而是**按时长分配，一个市场只对应一个窗口**（作者自己踩过，第一次读文档理解错了）

## 公告没写的两条（实拉 API 才知道）

1. **资产不是 7 个**：官方列 BTC/ETH/SOL/XRP/HYPE/BNB/DOGE，实测 8 个（多 **ZCash**）
2. **$1M 奖励有硬门槛**（市场对象里两个参数）：
   - `rewardsMinSize: 50` —— 挂单至少 50 股才计入
   - `rewardsMaxSpread: 4.5` —— 距中价 4.5 分以内才算
   - 挂 20 股或挂远价 = 奖励 0，全程无提示

## 验证方法（可复现）

- 市场对象里直接带 `twapEnabled`（8/5 false → 8/7 true）+ `rewardsMinSize`/`rewardsMaxSpread`，**不用登录不用 key**
- 作者博客完整规则：https://leolabs.me/blog/polymarket-twap-counterparty/

## 对共学的意义

1. **做市/奖励机会**：$1M 流动性奖励有明确参数门槛——如果做 Polymarket 做市，先把 rewardsMinSize/rewardsMaxSpread 拉出来核对
2. **TWAP 结算机制**：结算机制改变 = 套利结构改变（尾盘翻转成本量级不同）——「规则变更」本身就是机会源（信息差型）
3. **方法论**：作者「官方文档 vs 实测 API」双源核验 = 我们的证据优先原则；「公告没写的门槛」= 读原始数据不读二手宣传
