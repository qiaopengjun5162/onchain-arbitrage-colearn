# Jito Bundle 基础（D11 预习，2026-08-14 提前完成）

> 来源：docs.jito.wtf/lowlatencytxnsend（官方）+ QuickNode Jito Bundles guide（2026-05 更新）
> 定位：21 天产出表 #5「Jito Bundle pipeline」第一阶段——理解 bundle 提交流程，为 D12 devnet 第一笔 bundle 铺路
> 关联：`notes/jito-bundle-monitor-20260809.md`（已有监控层）、`scripts/jito_bundle_monitor.py`（tip 活跃度）

## 一、架构（谁在跑什么）

```
Searchers/dApps/bots ──(gRPC 或 JSON-RPC)──► Block Engine ──► Jito-Solana 验证者
                                                    │
                                                    └─► 竞价拍卖（tip 归验证者+质押者）
```
- 验证者跑修改版 Agave 客户端（Jito-Solana），连接 Block Engine
- Block Engine 模拟 bundle、选出最赚钱组合、提交给验证者
- Bundle 的 tip 作为竞价，重新分配给验证者和质押者

## 二、Bundle 三个特性（记牢）

1. **最多 5 笔交易**，按顺序执行
2. **原子性**：同一 slot 内执行；任何一笔失败 → 全部不提交（all-or-nothing）
3. **跨 slot 边界不行**：bundle 不能跨 slot

> 为什么需要：单笔交易有 1.4M CU 上限，复杂操作（多跳 swap）超预算；多笔交易分开发不原子

## 三、API 端点（JSON-RPC）

| 方法 | 作用 |
|---|---|
| `sendBundle` | 提交已签名交易列表（base64，最多 5 笔）→ 返回 `bundle_id`（= 签名 SHA-256）；**不代表已上链** |
| `getBundleStatuses` | 用 bundle_id 查状态（landed/pending/invalid） |
| `getInflightBundleStatuses` | 最近 5 分钟内的进行中状态 |
| `getTipAccounts` | 获取 8 个 tip 收款账户（随机选一个） |
| `simulateBundle` | 提交前模拟验证（Jito-Solana RPC 支持） |

URL 结构：
- 单笔：`https://<region>.mainnet.block-engine.jito.wtf/api/v1/transactions`
- bundle：`https://<region>.mainnet.block-engine.jito.wtf/api/v1`（bundles 方法）
- **devnet**：`https://devnet.block-engine.jito.wtf/api/v1`（D12 用）
- 区域：amsterdam/dublin/frankfurt/london/ny/slc/singapore/tokyo

## 四、Tip 机制（bundle 能不能被选中的核心）

- **最低 1000 lamports**（0.000001 SOL）；太低 → 拍卖直接不选
- tip = 任意指令（顶层或 CPI）转 SOL 到 8 个 tip accounts 之一
- **随机选 tip account** 减少竞争（8 选 1，大家别挤同一个）
- 拍卖：**50ms tick** 一轮；锁定模式相交（同账户 w/w、r/w、w/r）的 bundle 在同一拍卖竞争，按「tip / CU 效率」排序；不相交的并行
- 竞争机会时 tip 要按当前市场价调（可查 tip 定价接口）

## 五、失败常见原因（D12 会踩的坑）

1. **tip 太低** → bundle 不被选中（永远 pending）
2. **未模拟** → 交易无效直接 invalid；先 `simulateBundle` 或 Jito-Solana `simulateTransaction`
3. **uncled blocks（叔块）**：leader 的块没被超多数接受 → 交易被第三方重播，**bundle 原子性失效**，可能部分落地/失败
   - 防护：① tip 指令放主逻辑同一交易内（失败就不付 tip）② 交易内加 pre/post 状态断言（防重播伤害）③ 别把 tip 单独开交易
4. **blockhash 过期** → 需在有效期内提交（每 slot 更新）
5. **编码**：base64 推荐；base58 已弃用（慢）

## 六、D12 计划（devnet 第一笔 bundle）

```
1. 确认 devnet block engine 可达：curl -X POST https://devnet.block-engine.jito.wtf/api/v1 \
   -d '{"jsonrpc":"2.0","id":1,"method":"getTipAccounts","params":[]}'
2. 构造 2-3 笔简单交易（如 memo/transfer），按顺序签名（versioned tx, base64）
3. 第一笔或主逻辑交易内带 tip 转账（≥1000 lamports，随机 tip account）
4. sendBundle → 拿 bundle_id → getBundleStatuses 轮询
5. explorer.jito.wtf 查落地
```

## 七、要点一句话

**Bundle = 用 tip 竞价的原子交易组**。理解排序层（auction 50ms tick + tip/CU 效率）比会调 API 更重要——这就是为什么 devnet 跑通不等于赚钱（预期管理已对齐）。
