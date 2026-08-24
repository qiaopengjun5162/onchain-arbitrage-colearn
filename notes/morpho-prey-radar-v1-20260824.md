# Morpho prey radar v1（预言机偏离扫描哨兵）— 2026-08-24

> 脚本：`scripts/morpho_prey_radar.py` ｜ 数据：`data/prey_radar.jsonl` + `prey_radar_state.json`
> 触发：132 篇 digest 笔记 010「清算套利执行手册」→ 预言机节奏预测（事件驱动清算哨兵）落地
> 关联：`notes/morpho-discovery-monitoring-digest-20260814.md`（GraphQL 数据源 + 埋雷路径）

## 做了什么

- GraphQL 拉 Morpho 市场（含 listed=false 下架市场——埋雷高发区）→ eth_call `price()`（selector **0xa035b1fe**，`0x57e871e7` 会 revert）→ DeFiLlama 现货 → deviation = |oracle−spot|/oracle 分层
- 级别：≥2% INFO / ≥5% SIGNAL / 冻结论价机 BROKEN_ORACLE（raw≥1e40 且无缩放吻合）/ no_price / scale?
- watchdog 模式：24h 状态去重 + 偏离变化 >50% 才重报（防常驻信号刷屏）；同信号多市场聚合（HERMES ×24）
- cron `run_morpho_prey.sh` 每 30 分钟，静默契约

## 关键实测发现（2026-08-24）

1. **oracle 缩放 = 代币 decimals 决定，不能写死**：18 位币（WETH/cbETH/wstETH→USDC）→ 1e24；9 位币（SOL/JitoSOL）→ 1e33；8 位币（cbBTC/cbDOGE）→ 1e34；比值预言机（cbXRP/cbADA/wstETH→WETH）→ 1e36。解法 = 候选缩放档自动探测（[18,20,24,30,33,34,36,37,42,45]，对现货 <10% 吻合即用）
2. **GraphQL 字段坑**：`chainId` 不是合法参数（`chain` 才是）；`MarketState.price` 字段语义不可靠（cbBTC 少 2 位/USDe=0/HERMES=1e9）→ 不用，走 eth_call
3. **HERMES→USDC ×24 下架市场 = 冻结论价机埋雷实锤**：code 203 字节、price() 恒 1e45（≈1e9）、lltv 98%、util 100%、名义供给 $1.08B（oracle 价估值）——预言机一旦修正向下 → 清算连环
4. **mGLO→USDC SIGNAL 638bps**：oracle $0.94 vs spot $1.00（oracle 落后 6.4%，方向偏安全；注意与 HERMES 型"oracle 高于现货=危险方向"相反）
5. 14 个活市场全部健康（cbXRP 48.7 / cbDOGE 27.0 / JitoSOL 20.8 / SOL 7.6 / cbBTC 0.2bps）——cb 币长尾抵押品（010 目标）已在雷达内

## 可执行项

- [ ] PM 5-min 双买套利（群分享 0xBinTang，08-24）：给 PM 雷达加「Up+Down 双买成本 <$1」检测——与概率森林论文"~99% 机会未被执行"同族，钱包 $588K 利润转述未独立核验
- [ ] taoli.tools 反向对冲系列（brucexu，08-24）：工具推广（$5k 不装决策不变），跟踪 Bruce 系列实战复盘篇
- [ ] prey radar 下一步：oracle 更新节奏观测（30s cadence 验证）、Base Flashblocks 200ms 决胜层（010 执行手册第 2 步）、候选市场 eth_call HF 预计算（borrowable=oracle×lltv vs debt）
