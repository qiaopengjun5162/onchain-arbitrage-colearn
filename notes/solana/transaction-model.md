# Solana vs 以太坊：交易模型与套利机制对比

> 日期：2026-08-05
> 目的：理解为什么 Solana 上的套利玩法跟以太坊完全不同，为后续 Jito bundle 套利打基础

---

## 1. 核心差异总览

| 维度 | 以太坊 | Solana |
|---|---|---|
| 交易可见性 | 公共 mempool，所有 pending tx 公开可见 | **无公共 mempool**，交易通过 QUIC/TPU 直达当前 Leader |
| 共识机制 | Proof of Stake（Gaspar） | Proof of History + Tower BFT |
| 出块时间 | ~12s / slot | **~400ms / slot** |
| 排序规则 | Gas 竞价，价高者优先打包 | 先到先处理 + priority fee 影响 slot 内排序 |
| 费用模型 | Base fee（EIP-1559）+ priority tip | Base fee（销毁）+ **priority fee（归 Leader）** |
| 套利主流路径 | MEV-Boost / Flashbots（bundle 拍卖） | **Jito Block Engine**（链下 bundle 拍卖） |
| 关键基础设施 | Flashbots、Eden Network | Jito、Helius RPC、Triton RPC |

---

## 2. 交易生命周期对比

### 以太坊

```
用户签署 tx → 广播到 mempool（公开可见）
  → Searcher 扫描 mempool 找 MEV 机会
  → Builder 按 Gas 价排序打包 bundle
  → 通过 MEV-Boost 中继给 Proposer
  → 区块确认（~12s）
```

### Solana

```
用户签署 tx → QUIC 直接发给当前 Leader 的 TPU 端口
  → Leader 按到达顺序处理（无 mempool 阶段）
  → 4 个连续 slot 内确认（~1.6s）
  → 或通过 Jito Block Engine 提交 bundle（保证原子执行）
```

**关键差异：Solana 跳过了"公开可见的等待池"这一环。** 交易一旦离开你的节点，下一站就是 Leader。其他人无法在"路上"看到你的交易。

---

## 3. 费用模型的精确理解

### 常见误解："Solana Gas 几乎无关"

**不准确。** Solana 确实没有以太坊那样的"公开价高者得 mempool 拍卖"，但费用仍然影响交易排序。准确理解：

| 费用类型 | 机制 | 影响 |
|---|---|---|
| **Base fee** | 每笔交易固定 5000 lamports（~0.000005 SOL） | 销毁，防止垃圾交易 |
| **Priority fee** | 用户可选的附加费用，**归当前 Leader** | 影响同一 slot 内的交易排序——Leader 有动力优先处理 priority fee 更高的交易 |
| **Jito tip** | 提交给 Jito Block Engine 的小费 | 决定你的 bundle 能否被 searcher 选中打包进下一个 slot |

**结论：**
- 没有以太坊式的"Gas 价格公开竞拍"
- 但 priority fee 和 Jito tip 仍然构成**隐蔽的价格排序信号**
- Leader 在 slot 内部有自由度按 priority fee 调整顺序
- 低 Gas 只是**绝对门槛低**，不代表不需要优化费用策略

---

## 4. 三明治攻击在 Solana 上真的消失了吗？

### 常见误解："Solana 不能做三明治"

**过于绝对。** 准确版本：

### 事实时间线

1. **2023 年：Jito 曾开放公共 mempool**
   - Jito 的 Block Engine 在早期版本提供了类似以太坊的公开 mempool
   - 导致 Solana 上三明治攻击**泛滥成灾**
   - 大量用户被夹，社区强烈不满

2. **2024 年 3 月：Jito 主动关闭公共 mempool**
   - 面对巨大舆论压力和生态威胁，Jito 宣布关闭公开 mempool 功能
   - 这一决定直接让公开可见的三明治攻击大幅减少

3. **现在：三明治攻击没有完全消失**
   - 仍有渠道实现：
     - **私人 order flow**：某些 RPC 节点或交易聚合器内部可见订单
     - **Jito bundle**：searcher 可以通过 bundle 构建 front-run + victim + back-run 的原子序列
     - **快速轮询状态**：高频监控链上状态变化，在有利可图的交易发生时立即插入
   - 但难度大幅提高——没有公共 mempool 意味着对手方**看不到你的交易意图**

### 准确结论

> Solana 没有公共 mempool 让三明治攻击的**门槛大幅提高**，但不是**彻底消失**。通过私人 order flow 和 Jito bundle，三明治攻击仍然存在，只是从"人人都能看到"变成了"有特殊渠道的人才能做到"。对个人套利者来说，这不是主要威胁。

---

## 5. 这对套利策略意味着什么？

| 套利类型 | 以太坊运作方式 | Solana 运作方式 | 个人可行性 |
|---|---|---|---|
| **Sandwich（三明治）** | 盯 mempool 抢跑 | 需私人 order flow / Jito bundle | 极低 |
| **CEX-DEX 价差** | bot 监控 + 抢跑竞价 | bot 监控 + Jito bundle 原子执行 | 中等 |
| **三角套利** | 同一块内三笔 swap | Jito bundle 原子执行（全成功或全回滚） | 中等 |
| **跨链套利** | 慢（12s+桥延迟） | 快（400ms slot，但桥延迟仍存在） | 较低 |
| **资金费率套利** | 方便（perp 协议多） | Drift/Zeta 等原生协议 | 中等 |
| **原子套利** | Flashbots bundle | **Jito bundle（核心路径）** | 竞争最激烈 |

---

## 6. 关键结论

1. **Solana 套利的核心不再是 Gas 竞价，而是信息速度和 bundle 构建能力。**
2. **Jito Block Engine 是 Solana 套利的基建——理解它等于理解 Solana MEV。**
3. **低 Gas 不等于低竞争。** 正因成本低，竞争者更多，速度竞争更残酷。
4. **公共 mempool 的缺失保护了普通用户，但也提高了套利者的准入门槛——需要更主动的价格发现能力。**
5. **个人套利者的 edge 不来自速度军备竞赛，而来自信息差（币股价差、跨平台价差、资金费率周期）。**

---

## 参考资料

- [Helius: Solana Transaction Lifecycle](https://www.helius.dev/blog/solana-transaction-lifecycle)
- [Jito Labs Blog](https://www.jito.wtf/blog/)
- [Jito Mempool Shutdown Announcement (March 2024)](https://x.com/jito_labs/status/1766229863148519474)
