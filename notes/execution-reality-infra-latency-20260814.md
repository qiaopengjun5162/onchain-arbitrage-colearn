# 执行现实学：服务器方案评估 + Sequencer 287ms + 官方工具栈 digest（2026-08-14）

> 来源：Paxon 群内分享（服务器拆分方案 + Sequencer 延迟测量）+ Bruce Xu 官方工具文《做链上套利需要哪些工具？API、RPC、钱包与服务器配置》https://mp.weixin.qq.com/s/MbuIBm_-j4sJQBqWSvwJRg
> 定位：阶段三「执行现实学」补充案例，接 L0011 研究拆解工作流

## 一、服务器拆分方案评估（方案一：个人使用）

群友推荐的配置：

| 服务器 | 部署 | 建议配置 | 估算成本 |
|---|---|---|---|
| H1 | Ethereum + Base + Robinhood | 12-16c / 64GB / 4TB NVMe | $70-120/月 |
| H2 | BSC | 8c / 32GB / 4TB NVMe | $50-90/月 |
| H3 | Solana | 16-24c / 128GB / 2-4TB NVMe | $100-180/月 |
| 备份/监控/日志 | — | — | $20-40/月 |
| **合计** | | | **$240-430/月 ≈ ¥1,900-3,400/月** |

**评估结论：对「共学+监控+研究」阶段是过度配置。** 我们现有整套基建（8 个哨兵 + 证据流水线 + 雷达）跑在 0 成本上：公共 RPC + Helius 免费层 + 本地 cron。自建全节点只在三种情况才值得：
1. 大数据量回测（历史拉取不受限）
2. 低延迟 MEV/Jito 竞赛（省 10-50ms 节点往返）
3. 公共 RPC 429 卡死业务（但 Helius 付费层 $49/月封顶即可解，成本差 10 倍）

**配置点评**：
- H1：Ethereum 全节点 64GB 够、4TB 富余（snap sync ~2TB）；Base/RHC 是 OP-stack L2 轻量。首次同步的「竞争」= 带宽+磁盘 IO 打满（Ethereum.org 最低 2c/8G/2TB/10Mbps，推荐 25Mbps+ 不限流量）——**别在跑监控的盘上做首次同步**，先同步完再迁移，或直接快照同步
- H3：Solana 128GB 是硬门槛（官方下限），配置合理；磁盘增速 ~1TB+/年，4TB 更稳
- 替代：Hetzner 欧区同配置便宜 30-50%

**关键认知（Bruce 原文金句）**：「工具当然有用，但顺序不能反过来。套利的关键是发现机会，不是基建。」Bruce 自嘲花了 $2,000+ 组服务器最后装了 Steam 玩了一年 CS——**先找到长期存在的价差，再谈优化速度**。

## 二、Sequencer 287ms 延迟拆解

实测数据（OP-stack L2，公共 RPC 路径）：

| 环节 | 耗时 | 占比 | 解读 |
|---|---|---|---|
| 模拟 + Gas 估算 | 47.76ms | 17% | 每次候选都要 simulate，候选越多越慢 |
| Rust 签名 | 0.084ms | ~0% | 本地签名不是瓶颈（nonce 7-8 = 已在预签名） |
| 广播 | 55.43ms | 19% | RPC 往返，换更快端点收益直接 |
| 候选触发→提交 | ~145ms | 50% | 程序逻辑+模拟+广播合计 |
| 链上确认 | 142ms | — | sequencer 接收→包含，这半段控制不了 |
| **总计** | **287ms** | | **公共路径速度地板** |

**三个结论**：
1. **别跟 287ms 竞赛**。L2 无 Solana Jito 式排序拍卖，sequencer 说了算——拼到达时间+priority fee，个人 bot 在毫秒级抢跑里是被卷一方。这印证 L0008 结论：结构性机会（错价池/事件驱动/费率窗口）不需要抢 287ms
2. **要优化先打大头**：广播（55ms）+ 模拟（48ms）占 36%——并行多端点广播 + 预模拟缓存可把 145ms 压到 ~70ms；但链上确认 142ms 省不掉
3. **287ms 是公共路径地板**：专业队 sequencer 直连/私有端点再砍一半——差距在基础设施不在代码，这正是「低容量结构性价差」优于「低延迟军备竞赛」的证据

## 三、官方工具栈 digest（Bruce Xu 工具文）

### API 栈（按流程环节）
1. **机会发现**：行情/资金费面板/LI.FI/Taoli.tools/Binance Web3 API/自建 Scanner
2. **市场数据与报价**：LI.FI Quote+Route（同链/跨链）→ Binance Web3 API/池子数据交叉验证
3. **标准化**：对齐交易对/链/Token 地址/Decimals/方向/金额/时间戳
4. **构建执行**：合约/交易构建/RPC 广播
5. **钱包签名**：余额/Gas/nonce/allowance 检查，独立 Signer
6. **广播确认复盘**：receipt/跨链状态/到账/P&L

### 各工具关键参数
| 工具 | 免费额度/成本 | 备注 |
|---|---|---|
| LI.FI | 100 RPM，**25bps 平台费**（交易部分） | 70+ 链/200 万+ Token；Partner Portal 生成 Key；**我们已实测 integrator=jumper.exchange 可让 25bps 归零**（L0006 复测）；长期高频可找 Bruce 谈费率 |
| Binance Web3 API | 免费 | Market/Trading/Transaction/Wallet 四类；Wallet 是 LI.FI 集成伙伴 |
| Taoli.tools | VIP0 免费，资金上限 $5,000 | 本地运行 U 本位对冲套利工具；开源 Signer 支持 EVM+Solana |
| DEX Screener / DeFiLlama / Dune / Etherscan | 免费（Dune 60-300 次/分限流） | 发现层，先产品后 API |
| RPC | 公共免费（chainlist）→ QuickNode/Alchemy/Infura | 自建全节点预算 **$1k-1.5k**（不只是月租：NVMe/流量/同步/监控/升级）；初期用托管 |
| 私有交易 RPC | Flashbots Protect / MEV Blocker / bloXroute Protect | 防抢跑夹子，不保证成交/最佳价/跨链原子性 |

### 安全五规则（私钥=资产归零线）
1. 独立小额热钱包（真丢不心疼）
2. 交易所 API Key 不开放提现
3. 链上限制单笔/日累计/目标合约/Token + 监控
4. 检查 allowance，停止期间取消授权
5. **独立 Signer 签名机**：业务程序生成待签交易，签名机最高安全规则（禁用密码登录），只对外签名——Taoli Signer 开源实现

### 与我们现有栈对照
- LI.FI：已做 120 轮报价实验 ✅（integrator 参数已验证）
- Binance Web3 API：未接（候选，币股双腿数据源已有 tvscreener）
- Taoli.tools：未用（$5,000 资金上限 vs 我们研究期定位）
- 私有 RPC：未接（当前无低延迟需求，正确）
- 独立 Signer：**未做（真上执行前的必修课）**

## 四、关联

- `notes/l0011-research-decomposition-workflow-20260814.md`（工作流）
- `notes/morpho-flashloan-vault-snusd-arb-case-20260813.md`（287ms 不需要的结构性案例）
- `notes/l0008-opportunity-candidate-list-v1-20260812.md`（机会清单：结构性 > 高频）
- `notes/solana-prikey-security-20260809.md`（私钥安全）
- `notes/haasonline-scam-bot-case-20260814.md`（反诈案例：文章「表面套利程序上传私钥」的现实版）
