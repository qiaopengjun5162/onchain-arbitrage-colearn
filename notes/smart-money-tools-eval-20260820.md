# 聪明钱/链上钱包监控工具评估（对照自建能力，2026-08-20）

> 来源：@WY_mask 无颜 X 帖（2026-08-19，8.2K views）→ `sources/smart-money-wallet-tools-20260819.txt`
> 评估视角：每个工具 vs 我们已有自建能力（whale_dump_radar / meme-dev 四本账 / onchain-address-forensics），结论=值不值得用/订阅/借鉴

## 结论先行

**6 个工具里只有 2 个值得用：Arkham（实体识别补强取证）+ GMGN（胜率筛选思路借鉴）。** Nansen/Cielo/DeBank 与自建能力重叠，Bubblemaps 作为可视化辅助可偶尔用。

## 逐一对照

| 工具 | 主打 | 我们已有 | 评估 |
|---|---|---|---|
| **GMGN** | Meme 聪明钱：盈利钱包排行、跟单雷达、胜率筛选 | meme-dev-harvest-pattern（Dev 四本账状态机）是手动/半自动版 | 🟡 **借鉴胜率筛选**：5M 壳价 cohort 研究（backlog #14）可以学习它的「胜率」定义（盈利钱包占比/回撤），但跟单功能=博弈非套利，不实盘 |
| **Nansen** | 多链聪明钱、资金流、Token God Mode | onchain-address-forensics 横纵分析法（自建取证） | 🔴 订阅贵（$150+/mo），多链标签我们主要用 Solana+EVM 两线，自建 RPC 直读够用；不订阅 |
| **Arkham** | **实体识别最强，免费层看钱包归属+资金流向图** | 地址取证最耗时环节=实体归因（这钱包是谁的） | 🟢 **值得用（免费层）**：正好补 onchain-address-forensics 的实体识别环节——查证一个地址的归属/关联图谱，免费层够 90% 场景 |
| **Cielo** | 实时钱包监控+警报+TG 推送，自定义追踪列表 | whale_dump_radar.py（自建：已知巨鲸大额流出+暴涨信号） | 🔴 功能重叠，自建已覆盖核心场景且信号定义我们自己可控（「流出+24h/7d暴涨」）；不订阅 |
| **Bubblemaps** | 持仓分布气泡图：集中度/老鼠仓/集群 | meme-dev 藏仓转子钱包是链上手动验证 | 🟡 偶尔用：做 Dev 出货研究的「藏仓集群可视化」验证很方便，免费层够；不订阅 |
| **DeBank** | 输入地址看持仓/DeFi/历史交易 | RPC 直读 + DeFi 协议查询脚本 | 🔴 最基础，自建脚本已覆盖；收藏备用 |

## 落地建议

1. **Arkham 免费层纳入取证 SOP**：onchain-address-forensics 流程里加一步「Arkham 实体归因」（钱包归属 + 资金流图谱），省掉手动查实体时间
2. **GMGN 胜率定义借鉴**：meme cohort 研究（backlog #14）补充「胜率」维度——盈利钱包占比、平均持有周期、最大回撤，用数据验证「5M 壳价难亏钱」假设
3. **不订阅任何付费层**：Nansen/Cielo 的付费功能与自建能力重叠，省下订阅费
4. **同作者清算热力图合集**（CoinGlass/CoinAnk/Hyblock）可作爆仓监控参考——CoinGlass 已是业界标准，但我们已有 DeFi Sphere 清算哨兵（链上口径），CEX 口径可补充 CoinGlass 免费热力图（不进付费）

## Arkham 免费层实测（2026-08-20 已验证，写入了 onchain-address-forensics skill）

用 HFT 狗庄地址 0x4bfd879f 实测（browser 过 Cloudflare，web_extract 抓不到）：

- ✅ **EXCHANGE USAGE / TOP COUNTERPARTIES**：一页给出 25 天资金流交易所归因——Binance 49% 入金/55% 出金、ChangeNOW 15%、Gate 12%、Coinbase 10%、OKX 7%、Upbit/Bithumb 小额——**正好补我们取证最耗时的实体归因环节**
- ✅ **对端实体标签**：资金流自动标对手方实体（Quasar/Titan/Eureka Builder 区块构建者），跨链持仓聚合（ETH/Robinhood/BSC/Polygon/Hyperliquid 一页）
- ✅ PORTFOLIO / BALANCES HISTORY / PROFIT & LOSS / PERFORMANCE 免费可见
- ⚠️ **边界**：Labels 页需登录；API 需 key；「Change address label」社区标注可被污染 → 实体归因结论仍须链上资金流对账兜底
- 用法已写进 skill：取证第一步 Arkham 拿实体假设 → 链上 RPC 逐笔对账验证（假设-否证循环）

## 意义

- 工具评估的判据 = **「我们已有能力的缺口」而不是「工具好不好用」**：Arkham 补实体归因（真缺口），Cielo/Nansen 与自建重叠（不订阅），GMGN 借鉴方法论（胜率定义）
- 验证了自建路线：whale_dump_radar + meme-dev 四本账在功能上已覆盖 2/3 商业工具的核心场景，差别只在 UI 和标签库
- 下一步：把 Arkham 免费层实测一次（找一个已知地址跑归属查询），确认免费层能力边界再写入取证 SOP
