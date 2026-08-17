# Robinhood Chain 排序机制：FCFS 无优先费拍卖（执行层）

> 来源：Paxon 冷知识分享（2026-08-17）+ 官方文档/第三方查证
> 证据：Robinhood Chain 官方文档（FCFS 明确）、Jess 开发者文章（x.com/0xjesstech/article/2079909645359939818）、BlockRazor 博客（blockrazor.io/blog/RobinhoodChainRPC）、L2BEAT（l2beat.com/scaling/projects/robinhood）
> 归档日期：2026-08-17（Hermes）

## 一句话

Robinhood Chain 交易排序 = **先到先得（FCFS）**，严格按到达排序器的时间定序；**付费不能插队，没有 priority gas auction** → 竞争形态从「拼 tip」变成「拼延迟」。

## 机制细节

- 技术栈：Arbitrum Nitro L2，中心化排序器（L2BEAT：privileged sequencer），数据回帖以太坊 blob
- 排序策略：官方文档明确 FCFS，交易顺序 = 到达排序器的时间
- 无优先费拍卖：提高 gas 不会让你排到已排队交易前面
- 衍生结论：**基于费用排序的协议机制在 Robinhood 上失效**——keeper race、清算优先级拍卖这类玩法直接不能用（Jess 原文）

## 对我们研究线的意义（0xd7121208 执行层画面补全）

- 价格侧：预言机更新 calldata 人人同时拿到（08-15 digest 的 SVR 结论「抢先看到价格不存在」）→ 无信息差
- 排序侧：FCFS 无竞价（本条）→ 无 tip 竞争
- 合起来 = **纯延迟竞赛**：谁先到排序器谁赢，钱花在基建（私有 RPC/直连排序器/同可用区）不花在 gas 上
- 反推 0xd7121208 用 V4-hook 开窗 + 私有通道 = 绕开公开 mempool 的延迟优势

## 未来变量

Arbitrum 正在推 **Timeboost**（付费把时间戳提前最多 0.5 秒，sealed-bid priority gas auction）——若 Robinhood 接入，排序格局从纯 FCFS 变「FCFS + 0.5s 竞价窗口」，执行层评估需重做。

## 关联

- `notes/robinhood-arb-0xd7121208-address-research-20260808.md`（Robinhood 套利地址取证）
- `notes/icl-incremental-notes-digest-20260815.md`（SVR「抢先看到价格不存在」）
- `notes/execution-reality-infra-latency-20260814.md`（执行现实学：L2 公共路径速度地板）
