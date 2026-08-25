# Flashblocks 决胜层研究（清算线第 3 步）— 2026-08-25 D21

> 状态：**研究完成，暂不实盘**（符合 010 手册「触发前 30s 进场路径设计，先研究」）
> 上游：010 清算执行手册（`icl-incremental-notes-digest-20260824.md`）+ 清算哨兵三件套（prey radar / HF 扫描器 / USDe 联动）

## 一、Flashblocks 机制（200ms 子区块，决定「先到先得」）

- Base 每 2s 一个完整区块 = **10 个 200ms 的 Flashblock** 组成；Flashblock 由 builder 用 base-builder（Flashbots）构建，经 WebSocket 流式推给启用 Flashblocks 模块的节点
- **先到先得**：Flashblock 一旦构建并广播，其交易排序**锁定**——晚到的高 priority fee 交易无法插入已构建的 Flashblock（与旧 2s 区块「按 gas 全局排序」根本不同）
- **动态 mempool**：builder 构建每个 Flashblock 时持续收新交易，按**当时的 fee 排序**，不是全窗口全局排序
- **gas 预算递增**：Flashblock N 可用 N/10 的区块 gas（第 1 个桶 1/10，第 10 个桶全量）
- 订阅/读取：标准 RPC `eth_getBlockByNumber`（`pending` tag）、`eth_getTransactionReceipt`；Chainstack 实测 Flashblocks 端点确认延迟 **300-500ms**（vs 标准端点 ~2000ms）

**对清算的含义（010 实证）**：同场竞争，赢家付 2.5 gwei 赚 $10,679，付 25 gwei 的晚一个桶只捞 $254——**快一个桶 > 贵一个数量级**。清算机会在预言机更新后的第一个 Flashblock 窗口被抢光，拼的是「交易到达 builder 的时机」，不是 gas 竞价。

## 二、清算时点为什么可预测（前置情报链）

1. **预言机 30s 节奏**：Base 上清算价格来自预言机（Chainlink 类），~30s 更新一次 → 清算只可能发生在预言机更新后的窗口
2. **HF 预计算**：HF = 抵押品×oracle×LTV / 债务。010 手册式：`1.008 × 985/1000 = 0.99288`——预言机更新把价格推到 HF<1 的临界 → 清算人可提前算准「下一轮更新后谁会被清算」
3. **触发阶梯已有**（HF 扫描器）：`priceVariationToLiquidationPrice` 直接给出「价格跌 X% → 清算 Y 规模」；USDe→USDC $286M 贴线、-2% 累计 $260M 连环
4. **埋雷检测已有**（prey radar）：oracle vs 现货偏离 ≥2% 是「预言机修正方向」的提前量——修正方向朝清算线 = 确定性触发

## 三、进场路径设计（触发前 30s → 0-200ms 窗口）

### 信号层（T-30s：预判清算窗口）
- prey radar 偏离方向 + HF 扫描器触发阶梯 → 得出「候选清算仓 + 触发价」
- 预测下一次预言机更新时间（30s 节奏对齐）→ 该时间点是清算竞争窗口

### 构建层（T-1s：预构建交易）
- 用 **onMorphoLiquidate 回调路径**（010）：零本金、回调先给抵押品再还债、**不用闪贷**
- 交易内容：调用 Morpho 清算函数，指定目标仓（预先由触发阶梯选出），calldata 3 bytes 级
- 预估 gas 与利润：毛利润 = 清算折扣×抵押品规模（如 5-10%），扣 gas（$1-36 级）与滑点

### 竞争层（T-0：0-200ms 决胜）
- **目标 = 让清算交易成为预言机更新后第一个 Flashblock 里的前位**：
  - 提前把交易提交到 builder 的 mempool（预签名、非最终执行状态，等触发价满足）
  - 或监听预言机更新交易（Chainlink 合约的 mempool 广播）→ 收到即提交清算交易（下一 Flashblock 窗口前）
- fee 策略：**正常偏上即可**（动态 mempool 同窗口按 fee 排；但晚一个桶就出局，fee 高没用）——010 赢家 2.5 gwei
- 反竞争：多路径广播（多个 Flashblocks 节点）、预构建加速

### 出场层（触发后）
- 落袋率 81.7% 的教训：**出货深度是天花板**——清算拿到抵押品后（如 cbXRP/cbDOGE 长尾币）流动性薄，出货滑点吃掉利润
- 出场路径需预设计：直接市场单 / 路由到深池 / 分批；010 手册 22 笔 $58,060 理论 → $47,420 实际，差的就是出场

## 四、我们的哨兵怎么接（落地依赖清单）

| 依赖 | 现状 | 缺口 |
|---|---|---|
| Morpho GraphQL（持仓 HF/触发跌幅） | ✅ HF 扫描器已用 | 无 |
| 预言机偏离（oracle vs spot） | ✅ prey radar 已用 | 无 |
| **Base Flashblocks 节点**（WS 流 + pending 读取） | ⚠️ 部分 | 公共 RPC 已见 pending（见下），逐桶 WS 流需 Chainstack 类端点 |
| Chainlink 预言机更新交易监听（mempool） | ❌ 未接 | 需 Base mempool 数据源（Flashblocks 节点的 txpool / 私有 RPC） |
| Morpho Liquidated 事件流 | ❌ 未接 | 已结算事件是滞后的（≈2s 区块），仅可做统计不能做执行 |
| 执行端（构建+广播清算 tx） | ❌ 未接 | 需合约调用封装 + 私钥管理（安全铁律：本地配置） |

### 实测（2026-08-25，Base 公共 RPC）

| 端点 | pending 视图 | 延迟 |
|---|---|---|
| mainnet.base.org | ✅ 可用（#50426929，46 txs，比 latest 新） | 581ms（blockNumber 753ms） |
| base-rpc.publicnode.com | ❌ 返回 latest 同值（落后） | 414ms |

- **Base 官方公共 RPC 已暴露 Flashblocks 相关 pending 状态**——不接 Chainstack 也能拿到「下一个桶」的部分视图，但它是快照不是 200ms 逐桶流
- 结论：验证门槛比预期低——先用 `mainnet.base.org` pending 轮询（~500ms 级）就能跑通清算信号 demo；逐桶 WS 流是第二阶段优化

### 第一步验证已完成（2026-08-25，原型 `scripts/base_flashblocks_probe.py`）

实测 30 轮 / 34.8s：
- **pending 可见性确认**：18 个滚动块号（≈1s 级）——公共 RPC 能追踪下一个 2s 区块的构建过程
- **Morpho liquidate selector 已算**：`0xe72c76fe`（keccak("liquidate(address,address,address,uint256,bytes)")[:4]），可做交易匹配
- **清算交易 0 命中**：合理（010 手册 ~1 笔/小时），30s 窗口命中概率≈0

**关键设计结论**：信号策略**不能等清算交易**（太稀有）——正确链路 =
1. 监听 **Chainlink 预言机更新交易**（~30s 一次，高频可捕捉）
2. 命中后按 HF 预计算（触发阶梯）判断「本轮更新是否把候选仓打到 HF<1」
3. 若命中 → 下一个 Flashblock 窗口内轮询/提交清算交易

**⚠️ 信号策略修正（2026-08-25 补充实测，`base_flashblocks_probe.py` 扩展）**：
- 40 轮 / 43.1s 检测 Chainlink transmit + oracle 地址，**预言机更新 0 命中** → Chainlink 更新是**事件驱动**（偏离超阈值 + 心跳），平稳市况可能数小时一次，010 的「30s 节奏」是波动期特例
- Morpho oracle = ChainlinkOracle **包装合约**，更新交易发往底层 aggregator（≠ oracle 地址）——按 oracle 地址匹配无效
- **修正后的信号链**：高频轮询（1s 级）现货价 vs oracle 价偏离（prey radar 思路提速 1800 倍）→ 偏离突变 = 预言机即将更新 = 清算窗口临近；比监听预言机交易更直接

下一步候选：识别 Chainlink 聚合器地址 + transmit selector，把预言机更新检测接入原型。

## 五、风险与门槛（为什么暂不实盘）

1. **抢输纯亏 gas**：010 手册 $1-36 残渣扣 $6 gas 几乎全赔——错误预判的代价是每笔 $6
2. **SVR 中心化**：067 笔记 Top1 solver 回收 84.6% 清算奖励——大仓被专业 solver 垄断，我们只能吃长尾（cbXRP/cbDOGE/cbADA 类小仓）
3. **基础设施成本**：Flashblocks 节点 + mempool 数据源是硬门槛；公共 RPC 只给 2s 区块视图，等于盲跑
4. **长尾抵押品流动性**：目标仓越小越安全但利润越薄；5-10% 清算折扣 × $10K 级仓 = $500-1000 毛利，扣 infra 后空间有限
5. **与 010 手册的差距**：手册作者 7 天 159 笔事件驱动的执行经验，我们只有哨兵（情报层），执行层从零

## 六、结论

- Flashblocks 决胜层机制已研究透：**先到先得 > gas 竞价**，决胜变量是「交易到达 builder 的时机」
- 清算线情报链（预言机节奏 + HF 阶梯 + 埋雷）已闭环，缺的是**执行基础设施**（Flashblocks 节点 + mempool 监听 + 构建广播）
- 暂不实盘；若推进，第一步 = 接 Chainstack Flashblocks 端点 + 验证 pending 数据可用性（低成本验证，~1 天）
- 与 Solana 线对照：Solana 拼排序权（资本游戏），Base 清算拼预言机节奏预测 + 事件检测（不拼排序权）——这是 L2 对散户相对友好的结构，值得持续投入研究

## 下一步候选

- [ ] 接 Flashblocks 端点验证 pending 数据（低成本验证项）
- [ ] 编写清算交易构建器原型（测试网，dry-run）
- [ ] 010 手册完整回读（从 PDF 源，补齐执行细节：回调 gas 结构、失败模式）
