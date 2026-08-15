# Jito Bundle mainnet 首笔落地（D11/D12 主线，2026-08-15）

> 来源：实测记录（2026-08-15 晚间，Paxon 批准 mainnet 小额 demo）
> 脚本：`scripts/jito_bundle_demo.py`（已修复，可复跑）
> 关联：`notes/solana/jito-bundle-basics-20260815.md`（预习）、`notes/jito-bundle-monitor-20260809.md`（监控层）
> 前置：devnet block engine 已退役（2026-08-14 实测 SSL EOF）；testnet 领水全渠道阻塞（2026-08-15 二次探测 6 渠道全挂）

## 一句话

**mainnet 首笔 Jito bundle 落地成功**：纯 tip 转账单笔 bundle，`bundle_id=0302a15a…`，链上 tx `Cy8NLN1y…` 转账 0.005 SOL 到 tip account，confirmed。**两个坑是教科书级的：encoding 参数缺失 + tip 太低**。

## 完整排查过程（8 轮测试，记录失败路径）

| 轮 | 结构 | tip | encoding | 结果 |
|---|---|---|---|---|
| 1 | 3 tx（2 self-transfer + tip 最后） | 1000 | ❌ 无 | `transaction #0 could not be decoded` |
| 2 | curl 重放验证 | - | ❌ 无 | 同左（urllib 丢了错误 body，curl 才看到） |
| 3 | 3 tx + encoding | 1000 | ✅ | bundle_id 拿到 → pending 45s+ |
| 4 | 2 tx（diff self-transfer） | 1000 | ✅ | 同上 |
| 5 | 2 tx + tip 50000 | 50000 | ✅ | bundle_id → pending 60s+ |
| 6 | tip 75000 | 75000 | ✅ | bundle_id → **Invalid**（inflight 查到） |
| 7 | memo+tip 合并（文档同款） | 100000 | ✅ | bundle_id → **Invalid** |
| 8 | 纯 tip 单笔 | **5,000,000 (0.005 SOL)** | ✅ | **✅ confirmed（10 秒内）** |

关键中间发现：
- **RPC simulateTransaction 一直 success**（Program success），但 Jito 拒——问题在 Jito 路径不在交易本身
- 对照实验：同一 memo 交易 Jito `sendTransaction` 端点成功（签名 `5N2jUUUJ…`）与公共 RPC 返回相同签名 → **Jito 单笔路径正常，问题锁定 bundle 路径**
- tip 定价参考：`bundles.jito.wtf/api/v1/bundles/tip_floor` 显示 50 分位 5.1e-6 SOL、99 分位 0.0011 SOL → 我们前几轮 tip 全部 < 99 分位

## 根因（两个独立问题，缺一不可）

1. **`sendBundle` 的 encoding 参数**：文档说默认 base58（deprecated），不带 `{"encoding": "base64"}` 时 block engine 按 base58 解 base64 串 → `could not be decoded`。修复：`params=[txs, {"encoding": "base64"}]`
2. **tip 太低**：1000~100000 lamports（1e-6~1e-4 SOL）全部 < 99 分位 tip → 拍卖不选中 → 永远 pending 直到 blockhash 过期变 Invalid。0.005 SOL（5e6 lamports）> 99 分位 → 下一 leader 立即打包 confirmed

## 链上验证（证据）

- bundle_id: `0302a15a588279d36726cf168368323d377e44a281d2dfcb3805479429fc0a5e`
- tx: `Cy8NLN1y8Evn5PM9e6S3e3abE12eVv…` err=None
- 指令：transfer 5,000,000 lamports → tip account `ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt`
- pre/post balances：181129255 → 176124255（-0.005005 SOL = tip + 手续费 5000）
- 钱包余额核对：0.181139255 → 0.181129255 SOL（含 3 笔 memo 手续费各 5000 lamports）
- explorer.jito.wtf/bundle/0302a15a… 可查

## 沉淀（方法论）

1. **Jito 文档的坑**：`encoding` 默认 base58 是「文档里写着但一眼忽略」的坑——报错信息 `could not be decoded` 完全没提示是编码问题
2. **tip 是 bundle 的命门**：最小 1000 lamports 是「能被拍卖考虑」的下限，不是「能落地」的下限；实际要盯 `tip_floor` 分位数，demo 级别直接给 >99 分位最省事
3. **Invalid vs pending 的诊断价值**：pending = 拍卖没选上（tip 不够），Invalid = 模拟失败/blockhash 过期——前几轮 tip 低是 pending，后来 blockhash 过期变 Invalid，两个状态要分开看
4. **对照实验法**：单笔 sendTransaction 成功 vs bundle 失败 → 隔离出问题在 bundle 路径而非交易本身
5. **urllib 丢错误 body**：用 curl 重放拿完整错误信息（本项目环境代理下 urllib SSL EOF 常见）

## 下一步

- [ ] D12 正题：用 `sendBundle` 提交真实 swap bundle（模拟器输出路径），tip 用默认 0.005 SOL
- [ ] testnet 领水若恢复，用 testnet 复跑验证（0 成本路径）
- [ ] bundle 状态机（landed/pending/invalid + blockhash 过期重提交）做成可复用模块
- [ ] 与 `jito_bundle_monitor.py` 对接：落地确认后更新监控统计
