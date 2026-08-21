---
title: Solana Explorer 新功能
date: 2026-08-08
type: note
tags:
  - onchain-arbitrage
  - tool
---

# Solana Explorer 新功能（@solana_devs 官方，2026-08-21 群分享）

> 来源：https://x.com/solana_devs/status/2090439785303118198（Solana Developers，87.9k followers，50 likes）
> 引用：Jonas Hahn（Explorer 工程师）
> 归档日期：2026-08-21 ｜ 类型：工具更新

## 新功能清单

1. **Stake account 支持**（质押账户查看）
2. **更多移动端适配页面**
3. **Verified Builds V2 支持 + Squads 链接**（可验证构建 v2 = 合约开源验证升级）
4. **Verified Programs 搜索**（已验证程序搜索——之前要自己找，现在官方搜索）
5. **交易指令预览**（RPCv2 / cloudbreak / gTFA 支持）
6. **Subscriptions + Vote program 支持**
7. **IDLs for most native programs**（IDL 包覆盖大多数原生程序——可以直接读官方 IDL 解码）

## 对我们的意义

- **取证效率提升**：Verified Programs 搜索 + 原生程序 IDL = 识别未知程序（如之前 `HpNfyc2Saw7R…` 程序身份待查）更快——直接查 IDL 包解码指令
- **RPCv2 指令预览** = 交易解码不用全靠 4byte/自解码，Explorer 层面直接给
- 工具类更新，无策略含义；归档为环境/工具变更

## 结论

- 无紧急动作；工具类归档
- 下次取证遇到未知名程序，先试 Explorer 的 Verified Programs 搜索 + IDL 包
