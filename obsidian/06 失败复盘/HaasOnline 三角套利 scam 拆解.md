---
title: HaasOnline 三角套利 scam 拆解
date: 2026-08-14
type: note
status: research
tags:
  - scam
  - security
  - private-key
  - fraud
source: notes/haasonline-scam-bot-case-20260814.md
related:
  - 链上套利工具栈与执行现实
  - 套利策略全景
---

# HaasOnline 三角套利 scam 拆解

> BlockBloomer 反诈帖（2026-08-14 归档）｜「表面套利程序背后上传私钥」的现实版

## 一句话

披 HaasOnline 外衣的「LP 三角套利 TG 机器人」骗局：完整 GitBook + 收益截图 + 专业终端图包装，核心骗术 = **要求导入私钥/助记词**。官方已辟谣，已知受害者损失 4.1 BNB。

## 红旗识别

- 要求导入私钥/助记词，用「AES-256 分片加密代签」高深话术包装 → 一票否决
- 「安全与合约」页引导验证但**不给可核验部署地址/BscScan 链接/审计**，代码是反编译片段
- 导流到 Telegram 机器人（脱离可审计环境）
- 官方品牌不承认（8-11 @haasonline 官方直接回复 "This is a SCAM"）

## 时间线

- 8-11：HaasOnline 官方辟谣（回复已删推广帖）
- 8-13：@RAY10168 陈述——新钱包转入 4.1 BNB，次日被要求再转 6 BNB，随后资产被秒转空
- 注：当事人公开陈述，**资金归因需独立链上核验**（陈述≠证据）

## 识别 check 五连问

1. 是否要求导入私钥/助记词？
2. 能否给出可核验部署地址 + BscScan + 第三方审计？
3. 官方品牌是否承认？
4. 界面/叙事是否与已知骗局相似？
5. 收益截图是否 gross 口径（过 5 问）？

## 教训

- 独立小额热钱包原则被破（新钱包转 4.1 BNB = 破了小额）
- 不明/未开源程序 = 私钥上传风险；真执行前必修独立 Signer
- 安全铁律：账号/私钥/Token 永不进聊天与长期记忆
