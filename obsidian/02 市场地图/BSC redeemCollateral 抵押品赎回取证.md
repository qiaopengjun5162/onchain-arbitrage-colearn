---
title: BSC redeemCollateral 抵押品赎回取证
date: 2026-08-21
type: note
tags:
  - onchain-arbitrage
  - market-map
---

# BSC 交易取证：redeemCollateral 抵押品赎回（2026-08-21 群分享）

> 来源：https://bscscan.com/tx/0x809b7ac98b3e2567262808ac6d629b5d8b7ca5e3f0f11ebcad16d7839be95fff
> 归档日期：2026-08-21 ｜ 方法：BSC 公共 RPC + blockscout + 4byte 签名库（BSCScan API 全被 Cloudflare/免费限流挡）

## 交易画像

- **链**：BSC（chainId 56）｜ **状态**：成功（0x1）｜ gas 386,544 @ 50 gwei
- **from**：`0xccdf3a72…`（EOA 发起人）｜ **to**：`0x15102b75…`（借贷协议赎回合约）
- **method**：`0xbcd37526` = **`redeemCollateral(uint256,address,address,address,uint256,uint256,uint256)`**（4byte 签名库铁证）

## 路径还原（token 流）

| 步骤 | 方向 | 金额 | 说明 |
|---|---|---|---|
| ① | USDL 540.556 → burn（0x0000） | 540.556 USDL | 用户支付/销毁 USDL |
| ② | 金库 0xa1420e → 0xc250be | 0.034 WBNB | 协议费/保险（约 3.7%） |
| ③ | 金库 0xa1420e → 用户 | 0.919 WBNB | 赎回的抵押品 |

**input 解码**：arg0=540.556（USDL 数量）、arg1=arg3=`0xd3aa34a9…`（抵押品 token = WBNB）、arg4=0.198（min 输出滑点保护）、arg6=0.05（5% 滑点容差）

## 关键识别

- **USDL Stablecoin**：`0xd295f4b5…`，name="USDL Stablecoin"、symbol="USDL"、decimals=18——Paxos 系生息稳定币（Lift Dollar，Arbitrum 首发，BSC 部署）
- **WBNB**：`0xbb4cdb…` 标准 BEP-20
- **0xa1420e**：借贷协议金库/池（WBNB 抵押品托管）
- **0xc250be**：协议费收款（0.034 WBNB ≈ $30）
- **0x1510**：借贷协议的赎回合约（身份未完全确认，BSCScan 反爬——但从调用结构看是「USDL 抵押借贷协议」的赎回入口）

## 结论：这不是套利交易

1. **是「用 USDL 赎回 WBNB 抵押品」的单笔操作**——用户之前在协议里抵押 WBNB 借出 USDL（或类似结构），现在赎回
2. **无循环路径**（无 A→B→C→A 结构）、**无闪贷特征**（无借入-偿还对）、**无多池比价 staticcall**（仅单一金库转出）
3. 协议费 3.7% 是借贷协议的费用结构，不是套利利润
4. 隐含 USDL 价格 ≈ $1.46/枚？（540.556 USDL → 0.8848 WBNB 净值 ≈ $760）——**这个价格远离 1:1 锚定，可能是 USDL 在 BSC 的非官方/包装版本或已脱锚**，值得留意但非本交易结论

## 方法要点（沉淀）

- **BSCScan V1 API 已废弃**（NOTOK → V2 migration），V2 免费层不支持 BSC → 直接走公共 RPC `eth_getTransactionReceipt` + 自解码 logs
- **BEP-20 Transfer 事件签名是变体**：`0xddf252ad...c2b068...`（非标准 `...c2d068...`）——一个字节差异，用标准签名匹配会漏，必须精确比对
- **4byte.directory 查 method 签名**：`redeemCollateral` 直接定罪——不用猜协议名
- 判断是否套利的三板斧：循环路径？闪贷借还对？多池 staticcall 比价？——三个都没有 = 不是套利

## 关联

- `evm-arbitrage-tx-forensics` skill（本次实战：BSC 链 + 变体 Transfer 签名坑 + 4byte 定罪法）
- 与之前 R32xAccFis（Solana 盲套利 bot）对照：这笔是**协议常规操作**，不是 bot 行为
