# 以太坊 Aave 仓位管理案例（2026-07-14 tx 拆解）

> 来源：Paxon 分享（2026-08-07 分析）
> 链：Ethereum 主网 | tx：`0xefe4f89fe0fdd1b9842eff564a0fa8b426503bb9a8880c928823ff4d3e52762d`
> 方法：evm-arbitrage-tx-forensics skill

## 交易画像

- **时间**：2026-07-14 13:21 UTC（确认 171933）
- **from**：`0x8d64D775eFE48c75d5DFf5B3E7f58C6f384A1E05`（EOA）
- **to**：`0xf0570Ec48d03171a80fF796dcEADF0D385a00004`（**未验证合约**，method `0xd8f7ffd4` 未被 4byte 收录 = 私有/自定义函数）
- **fee**：0.00032 ETH（~$1，主网水平）；status ok

## 参与方

| 地址 | 身份 | 证据 |
|---|---|---|
| 0x87870Bca | **Aave v3 Ethereum 主池** | 内部调用 delegatecall 实现 |
| 0x5E8C8A72 | 代理合约（delegatecall → 0xadC45Df3），操作 LINK | call → 0x51491077（LINK 代币） |
| 0x51C72848c6 | 换汇池（USDC→LINK+WETH） | token 流 |
| 0x986bB0b2CC | Aave 相关（aUSDC/债务代币 mint/burn） | token 流 |
| 0x464C71f6c2 | aUSDC 接收（新头寸？） | token 流 |

## 操作还原（金额已按 decimals 换算）

```
① 换汇：0x51C728 池用 USDC $35,966 → 买 LINK 4193 个（~$35,640）+ WETH 0.543
② 还款：Aave 销毁 variableDebtEthLINK 4190.6e18（= 还清 LINK 借款）
③ 抵押品调整：销毁 aUSDC $35,942 + 部分重铸到 0x464C71f6c2（$312）
④ LINK 闭环：0x5E8C8A72 → 合约 → Aave 还债 → 剩余转回
```

## 结论

**不是三角套利/夹子，而是 Aave 借贷仓位管理交易**：
- 用 USDC 从 DEX 买 LINK → 偿还 Aave LINK 借款 → 同时调整抵押品
- 由**自定义策略合约**执行（未验证 + 私有函数签名 = 策略隐藏）
- 类型：仓位再平衡 / 降杠杆 / 清算前自救，三者之一（细节需 etherscan 完整数据确认）

## 结论修正（2026-08-07 图片分析后）

**⚠️ 原结论"仓位管理交易"不完整——真实性质：专业清算搜索器（searcher）**

图片分析（Paxon 分享截图）揭示完整执行链：
```
Aave V3 闪电贷 → 清算坏仓（抵押 USDC 借出 LINK）
→ 清算所得 USDC 经 Wintermute RFQ 换回 LINK + WETH 剩余
→ 偿还闪电贷
→ 利润绝大部分竞价支付给 BuilderNet（抢区块位置）
```

- **发起者画像**：0x8d64...A1E05 = 搜索器 EOA（签名/提交/付 gas，~0.0942 ETH，几乎无其他资产）
- **核心优势**（不是预测价格）：实时监控仓位健康度 → 发现可清算账户 → **从做市商取得原子 RFQ 报价** → 精确模拟 → 私有 Builder 通道竞价 → 只让模拟成功的交易上链
- **与暗池研究交叉**：Wintermute RFQ = Tessera V 的以太坊形态（同一做市商的报价制暗池）；BuilderNet 竞价 = 利润大部分流向区块构建者（"手续费生死线"在 MEV 层重现）
- **方法论更新**：单看 token 流会把清算搜索器误判为"仓位管理"——**识别"闪电贷 → 单边清偿 → RFQ 换币 → 竞价"的组合特征**才能正确分类

## 方法论要点

1. **Aave 仓位操作识别**：`variableDebt*` 销毁 = 还款；`aToken` mint/burn = 抵押品变动——看到这两个信号就知道是借贷操作
2. **未验证合约 + 未收录签名**（0xd8f7ffd4）→ 策略合约，只能从 token 流反推行为
3. **与 RHC 案例对比**：RHC = 闪铸三角套利（零本金高频）；本案 = 借贷仓位管理（资金密集型低频）——两种完全不同的机器人生态
4. blockscout 主网实例数据覆盖有限（token-balances 空），复杂案例需 etherscan 完整 API 交叉验证
