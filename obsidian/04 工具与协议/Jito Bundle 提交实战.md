---
title: Jito Bundle 提交实战（mainnet 首笔落地）
date: 2026-08-15
type: 实战记录
status: 已验证
tags: [Solana, Jito, MEV, bundle, 执行层]
source: notes/jito-bundle-mainnet-first-land-20260815.md
related: [[研究到生产五阶段管线]] [[执行清单五步法]] [[监控 Bot 入门]]
---

# Jito Bundle 提交实战（mainnet 首笔落地）

## 一句话

**sendBundle 两个教科书级坑**：① 必须带 `{"encoding":"base64"}`（默认 base58 → `could not be decoded`，报错无提示）② tip 必须 > 99 分位（1000~100000 lamports 全 pending/Invalid，0.005 SOL 才稳定落地）。

## 证据

- bundle_id `0302a15a…` → confirmed（10 秒内）
- 链上 tx `Cy8NLN1y…`：转账 0.005 SOL 到 tip account，pre/post balances 精确对账（-0.005005 SOL）
- tip 定价实时参考：`bundles.jito.wtf/api/v1/bundles/tip_floor`（50 分位 5e-6、99 分位 0.0011 SOL）

## 排查方法论（8 轮）

1. urllib 丢错误 body → curl 重放拿完整信息
2. 对照实验：同交易 Jito `sendTransaction` 成功 vs bundle 失败 → 问题锁定 bundle 路径
3. Invalid vs pending 分开诊断：pending=拍卖没选上（tip 低），Invalid=blockhash 过期/模拟失败
4. tip_floor 分位数定价：demo 直接给 >99 分位最省事

## 沉淀

### 管线 v2（2026-08-16，D12）

demo → 参数化管线 `scripts/jito_bundle_pipeline.py`：

- **tip 自动定价**：现场查 `bundles.jito.wtf/api/v1/bundles/tip_floor`，99 分位 ×1.5 安全垫，下限 0.003 / 上限 0.01 SOL。⚠️ tip_floor 是动态的（2 分钟内 99th 0.0009→0.0035 SOL）——写死 tip 的 demo 只适用当时市场
- **JSONL 结构化日志**：`data/jito_bundle_log.jsonl`（ts/network/n_tx/tip/basis/bundle_id/status/err），构造-提交-落地全程可追溯
- **状态机轮询**：getBundleStatuses 主查 + getInflightBundleStatuses 兜底（拿 Invalid 明细），landed/pending/invalid 三态区分
- 参数化：--network / --n-tx / --tip-mode auto|fixed / --dry-run

- 脚本 `scripts/jito_bundle_demo.py` 已修复（encoding + 默认 tip 5e6 lamports）可复跑
- bundle 状态机（landed/pending/invalid + blockhash 过期重提交）待做成可复用模块
- D12：真实 swap bundle（模拟器输出路径）
