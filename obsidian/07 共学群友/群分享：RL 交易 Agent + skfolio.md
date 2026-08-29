---
title: 群分享：RL 交易 Agent + skfolio
date: 2026-08-08
type: note
tags:
  - onchain-arbitrage
  - colearners
---

# 群分享：RL 交易 Agent 教程 + skfolio（2026-08-28）

> 触发：https://x.com/_zheergen/status/2092927081953030592（08-27 10:47 UTC，65 likes/6.9k views）
> 作者 _zheergen（折耳根 Ace）已归档：08-21 quant-trading 工具合集、08-09 awesome-systematic-trading——聚合/教程型账号
> 方法：fxtwitter 全文（主帖 + 引用帖）
> 结论：**教程帖，与套利线弱相关；方法论一条（样本外验证防过拟合）与库内互证，归档不深挖**

## 内容 digest

**主帖：PPO+Gym 强化学习交易 Agent**
- 思路：不写死规则（指标→阈值→开平仓），让 AI 自己学——30 根 K 线 + RSI/SMA/ATR 输入，Agent 自己决定观望/做多/做空 + 止盈止损，真实盈亏做奖励，处理止盈止损冲突防回测作弊
- 结果：训练 5 万步样本内好看但**过拟合**；1 万步样本外更稳
- 20 分钟视频 + 代码

**引用帖：skfolio（scikit-learn 生态投资组合优化库）**
- pip install skfolio：20+ 组合优化模型（均值方差/风险平价/HRP/Black-Litterman/CVaR）+ 因子模型 + Walk-Forward/Purged CV 样本外验证 + 交易成本/换手率/权重约束 + 压力测试
- 亮点：把 sklearn 工作流（fit/predict/Pipeline/GridSearchCV）接到资产配置

## 判定与可执行项

1. **方法论互证**：「5 万步样本内好看 vs 1 万步样本外稳」= 我们的回测铁律（样本外/幸存者偏差核验，backtest-playbook）——RL 交易 Agent 的过拟合教训与我们 21 天结论一致：**样本内曲线再漂亮不作数，可执行只看样本外**
2. skfolio：工具备选记入（若费率套利做多标的组合的资金分配/风险平价优化，可用它；当前单标的为主，用不上）
3. RL 交易 Agent 与套利线无关（方向交易 ≠ 价差/事件套利），不深挖；PPO 教程当通识储备
4. 无返佣/无盈利数字，无核验需求

## 红旗

- 无（教程帖，作者一贯聚合风格）
