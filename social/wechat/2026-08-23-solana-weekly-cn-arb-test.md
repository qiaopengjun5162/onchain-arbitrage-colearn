---
title: Solana 官方周报全文翻译：350ms 区块、40 亿 RWA、礼来莫德纳上链，附链上实测数据
wechat_title: Solana 官方周报全文翻译：350ms 区块、40 亿 RWA、礼来莫德纳上链，附链上实测数据
digest: Solana 官方 8 月 23 日周报全文中文翻译。350ms 区块首次削减，链上 RWA 破 40 亿，礼来莫德纳股票代币上线。翻译之外做了数据测试，莫德纳链上比美股贵 210bps，两个代币流动性都还很薄，规模不大。
author: Paxon Qiao
wechat_author: Paxon Qiao
---

# Solana 官方周报全文翻译：350ms 区块、40 亿 RWA、礼来莫德纳上链，附链上实测数据

> 原文：https://x.com/solana/status/2091504345216860553（Solana 官方账号，2026-08-23）

2026 年 8 月 23 日，Solana 官方账号发布周报，回顾这周生态里上线的一切。原文开头一句话很提气，钟走得更快了。从 350 毫秒的区块记录，到医疗股，再到一块真正的恐龙化石，中间还夹着 2300 亿美元的华尔街固收，这些事放在上周还都像疯话。

这篇周报我们做了两件事。第一，把它完整翻译成中文。第二，对里面关注度最高的礼来和莫德纳股票代币，拉了一组真实链上数据做对照。翻译在前，实测在后。

## 一、周报全文翻译

### 📰 头条新闻

- **Solana 把区块时间降到 350 毫秒**，这是 Solana 历史上第一次削减 slot 时间
- **新韩资产管理**联手 Solana 基金会、Etherfuse 和 Orca，打造一支**韩元计价的代币化基金**
- **Securitize 和 Neuberger Berman 在 Solana 推出 HINC**，背靠 Neuberger 超过 2300 亿美元的资产管理平台

### 📰 产品发布

- **Nexus Mutual 在 Solana 完成非 EVM 首秀**，面向 Kamino、Jupiter、Raydium 和 Orca 开放公开承保
- **礼来（$LLY）和莫德纳（$MRNA）股票代币上线 Solana**，经 Sunrise 发行，由 Backpack Securities 承销
- **MoonPay 接入 Cash App Pay**，符合条件的美国用户可以直接用 Cash App 余额购买 Solana 资产
- **Backpack 推出 Graphs 功能**，支持多指标股票分析和持仓论点绘图
- **Solana Mobile 在 Seed Vault Wallet 里上线 USDC Earn Vault**，由 Kamino 提供支持
- **Ramp 支持为 agent 钱包注资**，agent 可以通过 x402 协议在 Solana 上自动执行购买
- **Sphere Labs 上线 Onramper Accounts**，自动把美元和欧元的银行资金路由成稳定币
- **Interstice Digital 联手 FalconX**，在 Solana 上推出机构级跨链兑换
- **Jupiter 在 Portfolio v2 里加入 DeFi 持仓直接管理**
- **Clawpump 启动 AnsemHack Clawrena**，奖金池 32 万美元
- **Solana Mobile 开启 Seeker Summer 最后一轮**
- **Meteora 上线自定义 DLMM 提醒**，覆盖流动性出区间和 PnL 目标
- **JurassicFi 启动 Deaton 募资**，这是 Solana 上第一个代币化的恐龙化石
- **FOMO 把实时 Solana 新闻接入交易终端**
- **Solflare 预告即将上线永续合约交易**
- **Solana School 秋季班申请进入最后几天**，8 月 31 日开课
- **Breakpoint 2026 落地伦敦**，距今不到 90 天

### 📰 里程碑

- **Solana 链上 RWA 总值突破 40 亿美元**
- **代币化股票供给突破 4.65 亿美元**，创周新高
- **Raydium 累计代币化股票交易量突破 40 亿美元**
- **Solana 单日处理 2.16 亿笔非投票交易**，创历史新高
- **Kamino 机构商品收益金库达到 3000 万美元容量**
- **FOMO 进入美国 App Store 金融类 Top 3**
- **Solmate 金库持有约 125 万枚 SOL**
- **Commons 的 VibeFi 活动突破 10 万条帖子**
- **$MRNA 上线 Solana 首个 24 小时链上交易量突破 450 万美元**

## 二、我们做了什么测试

周报里最受关注的是礼来和莫德纳两个股票代币，上线当天就上了头条。我们拉了一组链上真实数据，看看这两个新代币的实际市场状态。

**测试对象**，$LLY 和 $MRNA 两个代币。

**测试内容**，三组数据，链上最新交易价格、主池流动性、24 小时成交额。美股这边取周五（8 月 21 日）收盘价作对照。

**测试方法**，链上数据用 DeFiLlama 的聚合价格接口加 GeckoTerminal 的池子数据，美股收盘价用 Yahoo Finance 数据。测试时间是周六，美股闭市，链上市场仍在交易，这个时间差本身也值得观察。

**快照结果**。

| 代币 | 链上价 | 美股收盘 | 偏差 | 主池流动性 | 24h 量 |
|---|---|---|---|---|---|
| LLY 礼来 | 1252.04 | 1255.40 | -26bps | 15.5 万美元 | 2.3 万美元 |
| MRNA 莫德纳 | 148.18 | 145.13 | +210bps | 15.1 万美元 | 0.8 万美元 |

两个代币一个比美股收盘低 26 个基点，一个高 210 个基点。

## 三、测试结果怎么看

**价格层面，链上价和美股收盘价贴得很近。** LLY 偏差 0.26%，MRNA 偏差 2.1%，对刚上线三天的新代币来说不算大。再看 MRNA 上市以来链上价和美股收盘的对照，三天轨迹。

| 日期 | 链上收盘 | 美股收盘 | 偏差 |
|---|---|---|---|
| 8/19 | 165.39 | 174.38 | -5.2% |
| 8/20 | 130.29 | 133.32 | -2.3% |
| 8/21 | 145.52 | 145.13 | +0.3% |

链上价一直在向美股收盘价靠拢，美股跌它跟着跌，美股反弹它跟着反弹，偏差从 5.2% 收敛到 0.3%。周六那 210bps 的溢价，更合理的解释是市场在美股闭市期间提前定价下周的走势，而不是定价失灵。

**流动性层面，两个代币都还很薄。** 主池流动性 15 万美元左右，全生态加起来不到 30 万，24 小时成交额一个 2.3 万、一个 0.8 万美元。对比 $MRNA 官方宣布的首日 24 小时 450 万美元链上交易量，可以看到热度集中在上市头两天，之后回落明显。想参与的人要注意，这个体量下大额买入会直接推高成交价，小额体验没问题。

**工具层面，踩了个坑也换了两条路。** 查 Solana 链上报价，第一反应是 Jupiter 的 API，结果三个入口全部连接失败，代理也救不回来。换了 DeFiLlama 和 GeckoTerminal 两条不需要密钥的公开接口，数据稳定，以后查 Solana 代币价格可以直接走这两条。

## 四、总结

这篇周报的信息量很大。Solana 正在把真实世界的资产大规模搬上链，医疗股、韩元基金、华尔街固收、连恐龙化石都来了，链上 RWA 突破 40 亿美元，代币化股票供给创周新高。350 毫秒的区块时间，让这条链在性能上继续领先。

翻译之外，我们顺手验证了两个新代币的市场状态。价格层面链上美股两边贴得很近，定价机制正常，偏差随时间收敛。流动性层面两个代币都还很薄，属于新上市阶段的正常状态，后续可以持续观察，等市场把流动性做起来。

## 参考链接

- 推特原文（Solana 官方周报） https://x.com/solana/status/2091504345216860553
- Backpack 官方公告，莫德纳（$MRNA）上线 https://learn.backpack.exchange/blog/tokenized-moderna-mrna
- Backpack 官方公告，礼来（$LLY）上线 https://learn.backpack.exchange/blog/tokenized-eli-lilly-lly
- $LLY 代币信息（Solscan） https://solscan.io/token/LLYuwZ33keFihgwoxXsBawy31AiRFLFSva32TYq5TvD
- $MRNA 代币信息（Solscan） https://solscan.io/token/MRNAzXzhNcaEXJPibHEn8cd4vyekCDiivTyEwswLUCT
