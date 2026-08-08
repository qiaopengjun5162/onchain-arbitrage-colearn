# LI.FI 实战实验：Ethereum USDC → Arbitrum USDC

日期：2026-08-06
状态：研究（只读，未签名未广播）

## 实验数据

### Token 验证

| | Ethereum USDC | Arbitrum USDC |
|---|---|---|
| 地址 | `0xA0b86991...` | `0xaf88d065...` |
| Price (LI.FI) | $0.9994 | $1.0003 |
| 验证状态 | verified | verified |
| Decimals | 6 | 6 |

**表面价差**: ~0.09% (9 bps)，几乎可以忽略。USDC 作为稳定币，跨链价差极小。

### /quote 结果

```
Route 工具:     Polymer (Standard)
输入:           1,000.00 USDC
预计到手:       997.50 USDC
最低到手:       997.50 USDC
LI.FI Fee:      2.50 USDC (25 bps)
Gas (SEND):     ~$0.15
总显性成本:     ~$2.65 (26.5 bps)
执行时间:       ~7s
```

## Break-even 计算

```
最低所需价差 = LI.FI Service Fee (25 bps)
             + Gas (1.5 bps)
             + 目标链交易滑点 (est. 2-5 bps)
             + Price Impact (≈0 for USDC)
             + 延迟/失败/资金占用 (est. 2-3 bps)
             ────────────────────────────
             ≈ 30-35 bps
```

## 结论

1. **USDC 跨链不存在套利机会** — 表面价差仅 9 bps，远低于 35 bps 的 break-even 线。这是预期内的，稳定币价差极小。

2. **主要成本来源**：LI.FI 25 bps 是绝对大头。即使免去这 25 bps（联系 Bruce 拿优惠），仍需 5-10 bps 的成本。

3. **这条路更适合的场景**：
   - 非稳定币跨链价差（代币化股票如 NVDAB、波动性资产）
   - 多链库存再平衡（低时效要求，可以等 Gas 低时走）
   - 预置资金模式（提前在各链放好钱，不临时跨链）

4. **/advanced/routes 未跑通**：返回 404，可能需要 POST 请求或其他认证方式。不影响本实验结论。

5. **实验中遇到的实际问题**：
   - Binance API 被墙（中国大陆网络限制）
   - LI.FI `/advanced/routes` GET 返回 404
   - 这些都是真实环境中的摩擦成本

## 下一步

- 换一个非稳定币 pair（如 ETH、代币化股票）重做实验
- 联系 Bruce 申请套利场景优惠 bps 方案
- 用 Hermes MCP Server 接入 LI.FI，让 Agent 自动执行 Quote 比较
