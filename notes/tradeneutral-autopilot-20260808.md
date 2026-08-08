# TradeNeutral Autopilot：多策略自动切换产品（Solar 推广）

> 来源：https://x.com/Solana_zh/status/2085908862972887258（Paxon 分享 2026-08-08）
> 关联：`notes/ma-cross-trend-strategy-review-20260808.md`（PnL 健康度风控）、`notes/funding-rate-signal-engineering-20260808.md`

## 推文内容（Solar 社区推广）

TradeNeutral 上线**自动驾驶仪（Autopilot）**：
- 自动学习一系列策略、跟踪表现、判断回撤、知道何时切换最佳策略
- 一次存款覆盖多元化组合的不同策略和中性收益
- 福利：9/1 前免手续费 + 2 倍 NT 积分；10/7 前通过 Solar 链接存款叠加 1.2 倍积分
- 产品页：https://www.neutral.trade/strategies/neutral-autopilot

## 评论中的信号

- Supanode：»finally some alpha with actual automation behind it, no more babysitting strategies just to chase drawdowns«（终于有真自动化的 alpha，不用再盯着策略追回撤）——痛点 = 手动盯策略回撤
- 辉哥：复述推广内容

## 分析：这个产品设计 = 我们刚学的 PnL 健康度风控的产品化

TradeNeutral Autopilot 的卖点（自动跟踪表现 / 判断回撤 / 切换最佳策略）正是我们 MA 复盘里「把 PnL 曲线当行情交易」的完整落地：

| Autopilot 功能 | 对应方法论 |
|---|---|
| 自动学习策略 | 策略池 + 历史回测 |
| 跟踪表现 | PnL 曲线监控 |
| 判断回撤 | 回撤 X% 暂停/止盈锁利 |
| 切换最佳策略 | 策略轮换（当前策略失效 → 切下一个） |

## 对共学的价值

1. **产品形态参考**：证明「策略自动切换」是真实市场需求（有人愿意付手续费），验证了我们 PnL 风控思路的方向
2. **中性收益（neutral yield）定位**：与用户「信息差型/中性策略」偏好一致
3. **待验证**：Autopilot 具体策略构成、回撤判断阈值、切换逻辑——如需要可查 neutral.trade 文档/合约
4. **竞品对照**：与 Astro（CEX 套利策略产品）对比——Astro 是用户自己配 pair，TradeNeutral 是平台自动管策略

## 待做

- [ ] 如感兴趣：调研 neutral.trade 的策略构成和回撤切换机制（对照我们哨兵的 PnL 风控设计）
- [ ] 关注其「策略切换」实现：是基于净值曲线规则还是模型预测？
