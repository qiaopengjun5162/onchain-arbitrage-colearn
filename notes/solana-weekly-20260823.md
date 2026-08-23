# Solana 官方周报（2026-08-23）：币股 RWA 线重大进展

> 来源：https://x.com/solana/status/2091504345216860553（33.7k views / 245 likes / 112 replies）
> 归档：2026-08-23 ｜ 关联：`notes/tokenized-stock-arbitrage.md`（币股线）、`notes/hip3-preipo-perps-entropy-20260821.md`、`notes/sec-supply-side-reform-20260823.md`（供给侧改革）、`notes/d19-four-direction-comparison-20260823.md`

## 本周大事（对我们相关度排序）

### 🚀 币股 RWA 线（3 条，全中 P0）
1. **$LLY（礼来）+ $MRNA（莫德纳）股票代币在 Solana 上线**——Backpack Securities 发行（via @sunrise）——**币股线继续扩张**（继 COIN/HL 系之后，制药股入场）
2. **Shinhan 资产管理（韩亚/新韩银行系）+ SolanaFndn + Etherfuse + Orca = KRW 代币化基金**——**法币计价的 RWA 基金**（非美元系入场）
3. **Securitize + Neuberger Berman 推 HINC on Solana**——Neuberger 背后 **$230B+ 资产管理平台**——机构级 RWA 落地

### ⚡ 性能里程碑
4. **Slot time 降到 350ms**（首次 slot 时间削减）——性能提升；**对 MEV/套利含义：区块更快 = 竞争窗口更短 = 我们 Jito 管线的时间预算变紧**

### 🏦 机构基建
5. Nexus Mutual 非 EVM 首秀（Solana 上保险覆盖 Kamino/Jupiter/Raydium/Orca）
6. MoonPay + CashApp Pay（美国用户现金余额直买 Solana 资产）
7. Interstice + FalconX 机构跨链 swap
8. Ramp x402 代理钱包（agent 钱包自动执行购买）

## 与我们的关系（关键）

1. **币股线（D19 P0）持续被验证**：本周 3 条 RWA/币股新闻 = 我们「币股闭市漂移」策略的**标的池在扩张**（更多股票代币 = 更多漂移事件 = 更多窗口）。$LLY/$MRNA 制药股加入，补上了「非科技股」象限
2. **KRW 基金 + HINC = 法币/机构级 RWA**：与供给侧改革（SEC 代币融资豁免）同向——**美国监管 + 传统机构 + 亚洲银行系三路并进**，币股 RWA 从「边缘实验」变「机构配置」
3. **350ms slot 对套利执行的影响**：需要评估——若 Solana 主网 slot 稳定降到 350ms，Jito bundle 竞争窗口变短，tip 定价和延迟预算要重新标定（D20 主网迁移清单可加此项）
4. **与 HIP-3 对照**：HIP-3 是 Hyperliquid 的 RWA 永续；Solana 是原生股票代币（Backpack 发行）——**两条 RWA 路线都在跑**

## 判定

归档。**币股 RWA 线宏观利好第 4 条证据链**（SEC 批代币化股票 → HIP-3 pre-IPO → 供给侧改革 → 本周 3 条）。可执行项：
- [x] 币股监控加 $LLY/$MRNA —— **已执行**（2026-08-23）：价差核验 + 开盘收敛 watchdog 部署，见 `notes/solana-native-bstock-lly-mrna-20260823.md`（结论：深度玩具仓不进场，监控已上线 cron `1da3deea43ef`）
- [ ] 350ms slot 对 Jito 管线的影响评估 → D20 主网迁移清单
- [ ] HINC / KRW 基金持续跟踪（代币化基金 = 未来闭市漂移/净值价差新标的）

## 一句话

**「从 350ms slot 记录到恐龙化石，中间 $230B 华尔街固收」——Solana 官方在向机构讲 RWA 故事，而我们的币股套利线正好站在这个故事的风口上。**
