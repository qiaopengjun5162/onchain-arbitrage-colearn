# DOS 多链搬砖三步落地：找币 → 监控 → 搬砖（2026-08-11）

> Paxon 思路落地：1) 找多链币 2) 监控多链价格 3) 判断价差搬砖。脚本 `scripts/multi_chain_spread_monitor.py`（配置化，可扩展）。
> 性质：只读调研 + paper 模拟。实盘须单独批准。

## 一、桥核验结论（已确认）

- DOS = LayerZero V2 OFT：BSC OFT（0xb0f09e…30e37）↔ ETH OFTAdapter（同地址）↔ ETH 原生 ERC20（0x951f…eb5E）；Endpoint V2（0x1a4407…）；peer 双向确认（EID 30101/30102）
- 桥 1:1 无代币费；实测桥费 ETH→BSC ~$0.02、BSC→ETH ~$0.69（BNB gas 贵）；到账 1-3 分钟
- 假币清单（§PDF）：BSC 0x951f… 同地址诱饵、0xab6278…、ETH 0xe034df…、Base 假币、旧 DOS Network——只认白名单

## 二、找多链币（实证结果）

- **方法**：给定 ETH 合约 → Uniswap V3 工厂（ETH）+ PancakeSwap V3 工厂（BSC）getPool 验证双链池存在
- **DOS**：✅ 双链深池（BSC PancakeSwap V3 0.01% 主池 $93 万 / ETH Uniswap V3 1% 浅池 $1.2 万）——特殊案例：新上币（8/10-8/11 Gate/OKX/Upbit 密集上币）驱动 BSC 侧流动性
- **候选 OFT 币验证（ZRO/ALT/W/PENDLE/ENA）**：ETH 侧多有池，**BSC 侧全部无主流 USDT 池** → 真正「BSC+ETH 双链都深」的多链币极度稀缺；找币的正确过滤条件是「两链池深度都够」，不是「币是否多链」
- 含义：跨链搬砖的候选池很小；DOS 这类「上币窗口 + BSC 主池」是新币特有的短期机会

## 三、监控（脚本实测，2026-08-11 08:32 UTC 快照）

| 配对 | 毛价差 | 净价差 | 方向 | 结论 |
|---|---|---|---|---|
| DOS BSC↔ETH | 136bps | **7.6bps** | BSC→ETH | 不达标（阈值 300bps） |

- 读取链路：BSC/ETH RPC 直读 V3 池 slot0（sqrtPriceX96 → 价格，decimals 自动换算）——已验证与 Gate ticker 精确一致（BSC 0.5292 vs Gate 0.529）
- 成本模型：桥费（方向相关：BSC→ETH $0.69 vs ETH→BSC $0.02）+ gas + DEX 费 + 滑点计提
- **关键发现**：BSC→ETH 方向桥费（$0.69）是主要杀手——毛 136bps 扣完只剩 7.6bps；ETH→BSC 方向（桥费 $0.02）若 ETH 折价会好很多
- 结论：DOS 当前净价差远低于 3% 阈值，**NO-GO**；监控挂着，等上币窗口价差放大（PDF 快照时 BSC 0.5645/ETH 0.557 毛 ~130bps，波动剧烈 0.274-0.758）
- 2026-08-12 补：integrator=jumper.exchange **不适用**——DOS 走 LayerZero 原生 OFT 桥（$0.69=消息费+BNB gas），与 LI.FI 平台费无关；且实测 LI.FI 对 BSC→ETH 无任何路由（404）。净 7.6bps 即无平台费口径，NO-GO 维持（详见 notes/l0006-integrator-retest-20260812.md 勘误）

## 四、搬砖（paper 判定，实盘须批准）

- 可行环路（PDF §4）：纯链上 BSC⇄ETH / CEX→ETH→BSC / BSC→ETH→CEX；净收益公式 = 卖价×(1−费−滑点) − 买价×(1+费+滑点) − 桥费 − 两链 gas − CEX 出入金费
- 当前判定：NO-GO（净 7.6bps << 300bps）；触发条件：ETH 侧相对 BSC 折价 >3% 且 ETH→BSC 方向（桥费 $0.02 便宜）→ 才有肉
- 风险红线：假币/克隆池、ETH 浅池滑点、桥延迟 vs 价差寿命、BscScan UNKNOWN 无审计、CEX 提现开放时间（Gate 08-11 19:00）、插针

## 五、下一步

- [ ] 监控脚本接 cron watchdog（净价差 ≥300bps 告警）——用户批准后
- [ ] 「找多链币」自动化：扫新上币公告（listing_monitor 已有）+ 双链池深度检查 → 自动加入监控（接 #14 Meme 微观结构思路）
- [ ] ETH→BSC 方向验证：当 ETH 折价时重算（桥费便宜的方向）
- [ ] 0xd21258ed22bebc33bbc6333e0ba6bbb44014a9ab 地址取证（用户待办，未完成——可能是 DOS 搬砖实证样本）
