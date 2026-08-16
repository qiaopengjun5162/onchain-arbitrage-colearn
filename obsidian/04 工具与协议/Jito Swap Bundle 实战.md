---
title: Jito Swap Bundle 实战（真实 swap 落地）
date: 2026-08-16
type: 实战记录
status: 已验证
tags: [Solana, Jito, MEV, bundle, Jupiter, swap, 执行层]
source: notes/jito-swap-bundle-first-land-20260816.md
related: [[Jito Bundle 提交实战]] [[研究到生产五阶段管线]] [[监控 Bot 入门]]
---

# Jito Swap Bundle 实战（真实 swap 落地）

## 一句话

**真实 swap bundle 落地**：0.01 SOL → USDC（Flux 1 跳），bundle `2248d538…` finalized err=Ok。第四笔 bundle 证据，第一条「Jupiter 构造 swap + Jito 提交」自动化闭环。

## 核心坑：build v2 手动组装 vs 官方端点

- 手动组装（`/swap/v2/build` raw instructions + LUT）：simulate err=None 通过，但 **sendBundle Invalid**（inflight 无错误明细）
- 官方端点（`/swap/v1/swap`）+ 重签名：**一次 confirmed**
- 排查链 4 坑：① instruction data 是 base64 非 hex ② cleanupInstruction 是 dict 非 list ③ LUT 解析三连坑（公共 RPC 无 getAddressLookupTable / from_bytes 报错 / 手动解析 offset 踩布局坑——最终发现 **Jupiter 响应直接给地址列表**）④ simulate 需 `replaceRecentBlockhash: true`
- **教训：能用官方交易端点就别手搓指令**——Jupiter 自动处理 LUT/账户顺序/计算预算；手搓 simulate 过了 Jito 也拒

## 官方端点正确用法

1. `GET /swap/v1/quote` → quoteResponse
2. `POST /swap/v1/swap` body=`{"userPublicKey":…, "wrapAndUnwrapSol": true, "dynamicComputeUnitLimit": true, "quoteResponse":…}` → swapTransaction（base64）
3. **⚠️ 返回未签名**（签名者全零）→ `VersionedTransaction(tx.message, [kp])` 重建签名
4. tip 交易复用 swap tx 的 blockhash；`sendBundle` 带 `{"encoding": "base64"}`

## 证据

- bundle `2248d538…` → finalized err=Ok，slot 439568445
- swap tx `9C45o2Mw…`：钱包 -0.010005 SOL（swap 出 + 手续费），Flux 池 +0.01 SOL
- 钱包 USDC +0.755395（≈ quote outAmount 755419 吻合）

## 沉淀

1. **官方交易端点 > 手搓指令**（LUT/账户/预算全自动）
2. 未签名交易重签名 = `VersionedTransaction(tx.message, [kp])`
3. bundle 内所有交易用同一 blockhash
4. 公共 RPC simulate 带 `replaceRecentBlockhash: true`（blockhash 确认时序滞后）

## 下一步

- swap bundle ↔ `arb_profit_simulator.py` 对接（模拟器正利润路径 → quote → swap → bundle）
- Rust 双实现版（scripts/solana-rs/）
- 与 `jito_bundle_monitor.py` 对接落地统计
