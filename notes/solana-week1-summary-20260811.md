# Solana 个人线第一周总结（D1-D7，2026-08-05→08-11）

> 按 personal-learning-plan-v2 D6 要求产出（D6 当天被 137 篇增量消化占位，D7 缓冲日补齐）。对照 v1 校准意见（`notes/personal-learning-plan-v1.md`）自查完成度。

## 一、本周产出清单（D1-D7）

| Day | 任务 | 产出 | 状态 |
|---|---|---|---|
| D1 | Solana 交易模型 | `notes/solana/transaction-model.md`（无 mempool、400ms slot、leader schedule、交易生命周期）+ 全地图概念清单 | ✅ |
| D2 | CLI+Anchor 环境 | `notes/solana/anchor-installation-note.md`（solana-cli 3.1.14 / anchor 0.32.1 / rustc 1.96.0 / devnet Helius RPC）+ 环境坑归档 `solana-rustc-mismatch-issue-34987.md`、`solana-sbf-build-issue-27598.md` | ✅ |
| D3 | 第一笔真实 swap | Jupiter v1 quote/build + @solana/web3.js 组装 v0 tx + 本地签名 + mainnet 极小金额（tx `27QRepQ1pewa…`）；发现 Jupiter v6/v7 已下线 → `api.jup.ag/swap/v1/quote`；devnet 无流动性教训 | ✅ |
| D4 | 价格监控 v0 | `pool_price.py`（Helius RPC 直读 Raydium vault 定价）+ `solana_dex_spread_monitor.py`（**Python+Rust 双实现**，实测同链跨 DEX 17-20bps）+ `token_metadata.py` | ✅ |
| D5 | 双监控 + 执行层 | 币股闭市漂移哨兵 `run_stock_sentinel.sh`（DEX 价差+币股一个脚本两个用途）+ 执行层 5 哨兵（priority_fee / jito_bundle / drift_funding / failed_tx / jupiter_route）+ `execution_quality_tracker.py`（达成率+门槛公式） | ✅ |
| D6 | 周总结 | 本文（补） | ✅ 补 |
| D7 | 缓冲/预习 | D8 AMM 数学预习 `amm_v2_verify.py`（x*y=k 精确复现 Raydium 73.9612，费率反推 0.30%） | ✅ |

## 二、对照 v1 校准意见自查

1. **节奏（3 周到 devnet bundle）** ✅：第 1 周目标（交易模型+环境+监控脚本）全部达成且超前——监控脚本 D4 就出了，比校准预期的「周末产出」早两天。下周进 AMM 数学（D8-D9）→ 模拟器（D10）→ Jito devnet bundle（D11-D13），节奏可控。
2. **深度 vs 广度折中** ✅：主线 Solana 未断，广度每天有进账（零基础学习版概念、群讨论归档、137 篇增量消化——广度实际超额）。教训：广度任务容易被当天的热点主线挤掉（D6 周总结就是这样被占位的），缓冲日兜底机制有效。
3. **Jito 定位** ✅：执行层 5 哨兵已建（priority fee 竞价 / jito tip / drift funding / 失败率 / 路由变化），把「理解排序层和执行层」落成了可观测的基建；未把它当盈利路径。与群复盘结论「个人别和专业 MEV 团队拼速度」一致。
4. **监控脚本 == 币股双用** ✅：`run_stock_sentinel.sh` 已在跑，币股闭市漂移哨兵 cron 正常。tvscreener 验证（今天）又给这条线加了个双腿数据源（`notes/tvscreener-verified-20260811.md`）。
5. **新增资产（本周超预期）**：066/128 验证日（Solana priority fee 30h 全 0 → 门槛=费率地板 0.50%）、无套利带雷达 v1（Solana 配对全在走廊内=市场有效）、Jupiter 路由监控 v2（双报价漂移+新鲜度）、网格回测（方法论层）。

## 三、未完成/顺延（下周插空）

- [ ] TUT Rust 双实现主体：时间对齐 + OI/funding 因子提取 + 报告对齐 Python 版（已开头：`scripts/tut_backtest/rust/`）
- [ ] 雷达 v2：池深度过滤 + Raydium 锚点校准（v4 vault 是否活跃）
- [ ] backrun 模拟器升级：接链上实时池子储备 + 全市场薄池扫描（与 backlog #13 低容量量化合并做）
- [ ] 拍卖哨兵 v1（EVM 侧 Maker LIQ2.0，与 Solana 线并行）

## 四、广度标注（D6 补）：research-backlog 感兴趣的候选方向

按 v1 校准「第三周选题时不至于只知道原子套利」，从 backlog 标注 3 个：

1. **#4 RWA/币股（D 路线）** ★★★ —— 已建哨兵+双腿数据源，闭市漂移实测 30-100bps，基础设施最全，个人可切入
2. **#13 低容量结构性价差量化** ★★★ —— 今天新增，群复盘结论「个人活路在低容量」的直接量化项，接 backrun 薄池扫描
3. **#3 链上 Perp / Hyperliquid** ★★ —— Drift funding 哨兵已在跑，仓位/清算/订单流全可观察，结构性机会候选

（原子套利 Jito 列为必修基建而非终局方向，与群共识一致。）

## 五、下周衔接（D8-D14）

- D8/D9 AMM 数学（V2 已验证，CLMM 可视化待做）
- D10 套利利润模拟器 v0
- D11-D13 Jito devnet bundle（读文档 → 第一笔 → 加套利逻辑）
- D14 第二周总结（对照 21 天产出总表：监控脚本 ✅ / 模拟器 / Jito pipeline）

## 关联

- 计划：`notes/personal-learning-plan-v2.md`（D6 行）、`notes/personal-learning-plan-v1.md`（校准意见）
- 周内打卡：daily/2026-08-05.md ~ 2026-08-11.md
- 知识总结：`notes/knowledge-summary-days1-2-20260806.md`（D1-2 概念版）
