---
title: LI.FI 跨链实战实验
date: 2026-08-06
type: note
status: research
tags:
  - tool
  - lifi
  - experiment
source: notes/lifi-experiment-20260806.md
---

## 实验数据

只读实验，未签名未广播。路径：Ethereum USDC → Arbitrum USDC。

### Token 验证

| | Ethereum USDC | Arbitrum USDC |
|---|---|---|
| 地址 | `0xA0b86991...` | `0xaf88d065...` |
| Price (LI.FI) | $0.9994 | $1.0003 |
| Decimals | 6 | 6 |

**表面价差**：~0.09%（9 bps），几乎可忽略。

### /quote 结果

```
Route:        Polymer (Standard)
输入:         1,000.00 USDC
预计到手:     997.50 USDC
最低到手:     997.50 USDC
LI.FI Fee:    2.50 USDC (25 bps)
Gas (SEND):   ~$0.15
总显性成本:   ~$2.65 (26.5 bps)
执行时间:     ~7s
```

## Break-even 计算

```
最低所需价差 = LI.FI Service Fee (25 bps)
             + Gas (1.5 bps)
             + 目标链交易滑点 (2-5 bps)
             + Price Impact (≈0 for USDC)
             + 延迟/失败/资金占用 (2-3 bps)
             ≈ 30-35 bps
```

## 结论

1. **USDC 跨链不存在套利机会**——表面价差仅 9 bps，远低于 35 bps break-even。稳定币价差极小。
2. **主要成本来源**：LI.FI 25 bps 是绝对大头。即使免去仍需 5-10 bps。
3. **更适合的场景**：非稳定币跨链价差（代币化股票如 NVDAB）、多链库存再平衡、预置资金模式。
4. `/advanced/routes` 未跑通（404，可能需 POST 或其他认证）。
5. **真实环境摩擦**：Binance API 被墙（中国大陆网络限制）、LI.FI `/advanced/routes` GET 404。

## 下一步

- 换非稳定币 pair（ETH、代币化股票）重做实验
- 联系 Bruce 申请套利场景优惠 bps
- 用 Hermes MCP Server 接入 LI.FI，让 Agent 自动执行 Quote 比较

> 关联：[[LI.FI 跨链可执行价差 120 轮实测]]、[[LI.FI 成本观测方法论]]
