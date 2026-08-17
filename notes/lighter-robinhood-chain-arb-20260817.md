# Lighter × Robinhood Chain 价差套利评估（臭臭 panda 推文 + 事实验证）

> 来源：@Chosmos110（臭臭 panda）「RobinHood Lighter ↔ Lighter 价差套利工具」推文（2026-08-17）+ Hermes 事实验证
> 原贴：https://x.com/Chosmos110/status/2088944635255406716
> 归档日期：2026-08-17（Hermes）

## 一句话

Lighter（Robinhood Wallet 默认 perp DEX）在 Robinhood Chain 上开了新订单簿，有人用「蚂蚁搬家」策略做 Lighter↔Lighter 价差套利（200U 实盘赚 2U）；**新市场形成期 + 1100 万 LIT 积分补贴 = 流动性红利期候选，但工具未开源，先当推广看不当机会看**。

## 推文内容

- 「RobinHood Lighter ↔ Lighter 价差套利工具」——蚂蚁搬家策略（每次小赚、高频累积）
- 实盘：200U 本金 → 盈利 2U 左右（≈1%）
- 宣称：Robinhood Chain Lighter 变相开启 Lighter S3
- 后续会继续分享实盘和更多工具（⚠️ 引流话术）

## 事实验证（2026-08-17 检索）

| 事实 | 状态 |
|---|---|
| Robinhood Chain 主网 2026-07-01 上线（Arbitrum L2） | ✅ Cryptobriefing/官方新闻稿 |
| Lighter 是 Robinhood Wallet 内默认 perp DEX（2400 万 funded accounts 入口） | ✅ |
| Lighter 承诺 1100 万 LIT 激励给 Robinhood 社区 | ✅ |
| Lighter Points Program：钱包内交易 2x 积分、web 1x，积分兑换 LIT | ✅ docs.lighter.xyz |
| LIT 因集成 +15~17%（~$2.14） | ✅ CoinMarketCap |

## 判断

**可偷的干货**：
1. **新订单簿形成期流动性红利**——与 08-15 digest「新公链/新市场初期流动性套利」同构，Lighter on Robinhood Chain 是活案例；L0008 候选清单「新公链窗口」同族，可加入观察
2. **积分补贴改变成本结构**——2x 钱包交易积分让吃单成本被补贴，蚂蚁搬家在补贴期可行；补贴结束成本结构完全不同
3. 与 048「天然价差」（Lighter vs EdgeX 0.04% 固定溢价）互证：Lighter 订单簿是天然价差观察标的
4. Robinhood Chain FCFS 排序（本库 08-17 归档）：订单簿抢单拼延迟不拼 gas

**泼冷水**：
1. 200U→2U 单日样本：无时间/成本/胜率/回撤明细，**gross vs net 五问过不了**（口径/成本占比/返佣依赖/样本窗口/最小规模）
2. **工具未命名未开源**：「实盘截图 + 后续分享更多工具」= 典型引流模式（对照骗术画像：搬运实操立人设→推工具；冰火岛验真标准：开源可审计 + dry-run + key 走环境变量才算数）
3. **积分规则风险**：Lighter Points 条款明确禁止刷量/机器人/自动化操纵（Abuse of Program Mechanics → 取消资格/没收积分）——自动套利刷量可能被反撸
4. 新订单簿深度浅，蚂蚁搬家规模上限低

## 结论

**信息价值 > 机会价值**：Lighter × Robinhood 集成是事实级新市场信号（新 perp 订单簿 + 补贴期），值得挂观察；但推文本身按推广处理。若真要碰：等工具开源可审计、我们自搭只读监控（按李胜利安全手册七问拆解）、小额独立钱包、明确积分规则边界。

## 关联

- `notes/robinhood-chain-fcfs-ordering-20260817.md`（Robinhood 排序机制）
- `notes/icl-incremental-notes-digest-20260815.md`（新公链/新市场流动性套利窗口）
- `notes/arb-software-safety-playbook-20260817.md`（工具安全七问）
- `notes/l0008-opportunity-candidate-list-v1-20260812.md`（候选清单）
