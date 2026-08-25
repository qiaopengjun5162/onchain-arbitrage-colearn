# 主网迁移清单（D20 补做）— 2026-08-25

> 触发：personal-learning-plan-v2.md D20 任务「共学结束后把 pipeline 从 devnet 搬到主网需要准备什么」——被同块排序挤掉，本日补做
> 关联：350ms slot 影响评估（`notes/solana/350ms-slot-jito-impact-20260825.md`）+ 21 天总结（`notes/21-day-summary-20260825.md`）

## 迁移范围（哪些 pipeline 值得上主网）

| 管线 | devnet 状态 | 主网迁移价值 | 判定 |
|---|---|---|---|
| 雷达 v4（no_arb_corridor_radar） | ✅ 只读监控 | 高——零资金风险，纯情报 | 🟢 可迁移 |
| priority fee 监控 | ✅ 只读 | 高——350ms 时代 tip 定价依据 | 🟢 可迁移 |
| execution quality tracker | ✅ 只读 | 高——达成率/失败率 KPI | 🟢 可迁移 |
| Jito bundle pipeline | ✅ devnet 跑通 | ⚠️ 实盘执行层，风险高 | 🟡 暂缓（等策略成熟） |
| 清算哨兵（Morpho/Base） | ⚠️ 已直连主网数据 | 高——只读情报链 | 🟢 已在主网侧 |

**结论：只读监控类全部可迁移（零资金风险），执行类（bundle）暂缓。**

## 一、RPC 节点

- 公共 RPC（api.mainnet-beta.solana.com / Helius free）：监控类够用，延迟 100-200ms 可接受
- 350ms 时代同块竞争：需 Helius 付费 WS 订阅 + 私有 RPC（当前只有 free key）→ 预算：Helius Developer ~$49/月 或自建 RPC 节点
- Base 侧：mainnet.base.org 公共 RPC 已验证可用（pending 可见）；Flashblocks 节点（Chainstack）~$29/月起,执行阶段再上

## 二、账户

- 新建迁移专用账户（不用主钱包）——安全铁律
- 预算账户：SOL 少量（监控类只读不需要余额；执行类需 ~0.1-0.5 SOL 覆盖 gas）
- Base 侧：新 EOA + 少量 ETH（~0.02 ETH 够几百笔清算尝试的 gas）
- 私钥存本地配置文件（~/.hermes/.env 风格,不进笔记不进 git,聊天只引用变量名）

## 三、Gas 预算（执行类才需要）

| 操作 | 预估成本 |
|---|---|
| Solana 监控类（只读） | 0（RPC 订阅费除外） |
| Jito bundle（若执行） | tip = P99×1.5 ≈ 0.005-0.01 SOL/笔 + 失败全额损耗 |
| Base 清算尝试 | ~$1-36 gas/笔（010 手册实测），抢输纯亏 |

## 四、监控告警

- 现有 cron 哨兵集群（49 个任务）已覆盖：OI/清算/费率/币股/雷达/基础设施自检
- 迁移后新增：
  - 账户余额告警（<0.05 SOL / <0.01 ETH 时推送）
  - 执行质量 KPI 告警（fill_rate 下降 20% 或失败率 >30% 推送）
  - Flashblocks 端点健康检查（接上后）
- 基建自检已有（infra_selfcheck 每小时）

## 五、风控规则（执行类铁律）

1. **蚂蚁仓起步**：单笔 <$1K,总敞口 <$5K（共学结论：先验证执行质量再放量）
2. **gross → net 验收门**：任何策略上线前先 2 周纸面/蚂蚁仓,净利为正才放量
3. **失败成本计入**：EV = p_land×P_land − p_revert×C_revert − p_drop×C_drop − C_infra − C_capital（055 模型）
4. **价差生死线**:机器执行,价差恶化 ≥ 已积累收益 × 1.5 即退（费率线退出纪律,已闭环）
5. **不因信号放宽滑点**（058 规则）;同状态为正 + 原子执行 + 可回滚才做（062 五问）
6. **止损**:单日亏损达资金 5% 停手复盘,连续 3 天亏损降级回纸面

## 六、最小测试资金（执行类启动包）

- Solana bundle：0.5 SOL（~$80,够 ~50 笔尝试）
- Base 清算：0.05 ETH（~$150,够 ~100 笔 gas 尝试）
- 总启动包：~$250（在「共学后深挖」确认策略正 EV 后才动用）

## 七、迁移顺序（建议）

1. ✅ 只读监控全部主网化（雷达/费率/执行质量/清算哨兵）——**现在就能做**
2. 执行质量数据积累 2 周（fill_rate 基线）
3. 清算线：高频偏离轮询原型 → Flashblocks 端点 → 蚂蚁仓实盘（~$150 启动包）
4. 费率线：等事件窗口信号（cron 已挂）,信号出现且验证后蚂蚁仓
5. Jito bundle：仅作为基础设施理解,不主动上主网执行（排序权资本游戏,无 edge）
