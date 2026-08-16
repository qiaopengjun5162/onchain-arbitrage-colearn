# Jito Swap Bundle 落地：发现→构造→提交→日志 闭环（D13 主线提前完成，2026-08-16）

> 来源：实测记录（2026-08-16，Paxon 批准 mainnet 小额 swap demo）
> 脚本：`scripts/jito_swap_bundle.py`
> 关联：`scripts/jito_bundle_pipeline.py`（纯 transfer 管线 v2）、`notes/jito-bundle-mainnet-first-land-20260815.md`（第一/二笔 bundle）
> 前置：D12 完成管线 v2（tip 自动定价 + JSONL 日志 + 状态机）

## 一句话

**真实 swap bundle 落地成功**：0.01 SOL → USDC（Flux 1 跳），bundle_id `2248d538…` confirmed，钱包 USDC +0.7553（与报价吻合）。**第四笔 bundle 证据**，且是第一条「Jupiter 构造 swap + Jito 提交」的自动化闭环。

## 关键坑：build v2 手动组装 vs 官方端点

**现象**：`/swap/v2/build` 拿 raw instructions 手动组装（setup+swap+cleanup+computeBudget + LUT）→ simulateTransaction err=None 通过 → 但 sendBundle 后 **Invalid**（inflight 无错误明细）。换成官方 `/swap/v1/swap` 端点交易 + 重签名 → **一次 confirmed**。

**排查链**（手动组装路径的 4 个坑，按出现顺序）：
1. **instruction data 是 base64** 不是 hex/bytes（`A+MEAAAAAAAA` 特征）——`b64decode(validate=True)` 兜底 hex
2. **cleanupInstruction 是单个 dict 不是 list**——遍历 dict 拿到的是 key 字符串，报 `string indices must be integers`
3. **LUT 解析三连坑**：`getAddressLookupTable` 公共 RPC 不支持（-32601）→ `getAccountInfo` + `AddressLookupTableAccount.from_bytes` 报 unexpected end of file（solders 需要预序列化格式）→ 手动解析 offset 又踩版本布局坑 → **最终发现 Jupiter build 响应里 `addressesByLookupTableAddress` 已直接给地址列表**，不用 RPC 拉
4. **simulate 报 BlockhashNotFound**：公共 RPC 对刚拿到的 blockhash 确认时序滞后 → 加 `replaceRecentBlockhash: true` 后 err=null

**为什么手动组装 Invalid 而官方端点成功**：虽然 simulate 通过，Jito block engine 的 bundle 模拟比公共 RPC simulate 更严格（LUT 序列化、账户顺序、fee payer 处理都可能不同）。**教训：能用官方端点组装交易就别手搓指令**——Jupiter 帮你处理了 LUT/账户顺序/计算单元预算的全部细节。

## 官方端点路径的正确用法

1. `GET /swap/v1/quote` 拿 quoteResponse
2. `POST /swap/v1/swap` body=`{"userPublicKey": …, "wrapAndUnwrapSol": true, "dynamicComputeUnitLimit": true, "quoteResponse": …}` → 返回 `swapTransaction`（base64）
3. **⚠️ 返回的交易是未签名的**（签名者全零 1111…）——`VersionedTransaction.from_bytes` 后必须用我们的 keypair 重建：`VersionedTransaction(tx.message, [kp])`
4. tip 交易用 swap tx 自带的 blockhash（bundle 内统一）
5. `sendBundle` with `{"encoding": "base64"}`

## 链上验证（证据）

- bundle_id: `2248d538115ba6e76f160b08f346ecf3f90be4301b14e35cb06bcea014be23dc` → **finalized, err=Ok, slot 439568445**
- swap tx: `9C45o2Mw…`，fee 5000 lamports；钱包 SOL -0.010005（0.01 swap 出 + 手续费）
- 收款方: Flux 池 `5BzogZvH…` +0.01 SOL（route 1 跳 label=Flux）
- 钱包 USDC 账户 `BuQnWXc1…` 31.717471（pre 30.962076 → post 31.717471，**+0.755395** ≈ quote outAmount 755419 吻合）
- tip 0.005 SOL（auto 定价下限）

## 沉淀（方法论）

1. **官方交易端点 > 手搓指令**：Jupiter `/swap/v1/swap` 返回完整可执行交易，自动处理 LUT/账户/预算；build v2 raw 组装是给需要深度定制的人用的，套利研究阶段用官方端点足够
2. **未签名交易重签名**：官方 swap 端点返回签名者全零，`VersionedTransaction(tx.message, [kp])` 重建即完成签名
3. **bundle 内所有交易用同一 blockhash**：swap tx 自带 blockhash，tip tx 直接复用
4. **公共 RPC simulate 要带 replaceRecentBlockhash**：否则刚拿到的 blockhash 报 BlockhashNotFound

## 下一步

- [ ] D13 正题完成度：发现→构造→提交→日志闭环 ✅（模拟器输出路径=单腿 swap，套利路径待 D15 pipeline 整合）
- [ ] 把 `jito_swap_bundle.py` 与 `arb_profit_simulator.py` 对接：模拟器选出正利润路径 → quote → swap → bundle
- [ ] Rust 双实现（用户偏好）：`scripts/solana-rs/` 加 jito swap bundle 版
- [ ] 与 `jito_bundle_monitor.py` 对接：落地确认后更新监控统计
