# PM 5-min 涨跌盘双买套利检测器（2026-08-24）

> 脚本：`scripts/pm_binary_dual_buy.py` ｜ 数据：`data/pm_binary_dual_buy.jsonl` + `_state.json`
> 触发：群分享 0xBinTang（Up 22.5¢+Down 59.8¢=82.3¢→锁 17.7¢/对，$588K 利润转述未核验）
> cron `20995c6cc361`：每 2 分钟 watchdog（窗口级去重），有信号才推

## 机制

- Polymarket 5-min 涨跌盘：每窗口一个 event（BTC/ETH/SOL/XRP），outcomes [Up, Down]，赢家每份兑 $1
- 双买：ask_Up + ask_Down < $1 → 无方向敞口锁差价（无需猜涨跌）
- 本检测器口径（执行可兑现）：**盘口 ask-ask**（不用 outcomePrices/midpoint）+ taker 费（0.07×p×(1-p) 每腿）+ 容量门槛（两腿最优档 ≥20 股）+ 幽灵墙降级（≥1000 股且 ≥10× 次档）

## 实测发现（2026-08-24）

1. **slug 模式**：`{btc|eth|sol|xrp}-updown-5m-{窗口起始epoch}`，Gamma /events?slug= 直取，四币全通
2. **常态盘口结构**：任意时刻通常一侧只剩 bids（无 ask）另一侧 ask 在 0.95-0.99——互补定价 ≈1.0，**主流币双买 <$1 是稀有事件**（快速行情盘口滞后才出现）
3. **窗口开头是 MM 播种**：0.99/0.99 双边 ask（无意义），扫描需等窗口中期
4. 闭窗后 book 清空 → 历史窗口无法回测信号频率（只能靠 cron 攒新数据）

## 结论

- 检测器工作正常，当前无信号（市场有效）——0xBinTang 声称的 82.3¢ 组合是**瞬时盘口滞后**，非常态
- 与 PM 线已有结论一致：概率森林论文「一年 $3,960 万已实现套利、~99% 机会未被执行」= 机会稀有且执行难
- **执行现实**：2 分钟轮询只能检测存在性，真正吃需要 ws 级订阅 + 极速下单（0xBinTang 说"差半秒成本回 1 美元以上"）——本轮只做检测层（研究阶段），执行层不做

## 可执行项

- [ ] cron 攒 1-2 周信号频率数据（jsonl）→ 统计双买 <$1 的出现频率/持续时间/资产分布
- [ ] 若频率足够：升级 ws 订阅（CLOB websocket）+ 下单执行（需钱包签名，先 paper）
- [ ] 0xBinTang 钱包核验：/activity?user=0xce25... 拉真实成交/返佣，验证 $588K 是否 gross/net
