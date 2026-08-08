# solana-rs — Solana 套利研究脚本（Rust 版）

把之前 Python 版的 Solana 交互脚本用 Rust 重写，加深 Solana 执行层理解。
Rust 与 Python 双版本并存，同一套逻辑两种实现。

## 状态（2026-08-07）

| 功能 | Python/Node 版 | Rust 版 |
|---|---|---|
| Jupiter quote（新 API v1） | `jupiter_swap_d3.py` ✅ | ✅ `quote` |
| swap build（v2/build） | `jupiter_swap_d3.py` ✅ | ✅ `build` |
| tx 组装 + 签名（v0 + ALT） | `swap_mainnet.mjs` ✅ | ✅ `swap`（dry-run 验证，753B 签名成功） |
| 广播 | `swap_mainnet.mjs --send` ✅ | ✅ `swap --send`（2026-08-07 真发验证，finalized） |
| 价格/池子读取 | `pool_price.py` | ✅ `spread`（2026-08-08：Raydium 直读 vs Jupiter 多金额采样，实测 20.7bps 池间价差） |
| DEX 价差监控 | `solana_dex_spread_monitor.py` ✅ | ✅ `spread` |

## 使用

```bash
# SOL → USDC（默认 1 SOL）
cargo run -- quote --proxy http://127.0.0.1:7890

# 反向
cargo run -- quote --in-token USDC --out-token SOL --amount 100 --proxy http://127.0.0.1:7890

# 只看 build 指令（只读）
cargo run -- build --amount 0.01 --taker <钱包地址> --proxy http://127.0.0.1:7890

# 完整 swap（默认 dry-run：组装+签名，不广播）
cargo run -- swap --amount 0.01 --proxy http://127.0.0.1:7890

# 真发（消耗真实 SOL + Gas；密钥从 ~/.config/solana/id.json 本地读取）
# cargo run -- swap --amount 0.01 --send --proxy http://127.0.0.1:7890

# 不传 --proxy 时读 HTTPS_PROXY 环境变量；RPC 用 HELIUS_RPC_URL / HELIUS_API_KEY，缺省公共 RPC
```

## 结构

- `src/main.rs` — CLI（clap：quote/build/swap 子命令 + 全局 --proxy）
- `src/jupiter.rs` — Jupiter Swap API 客户端（quote v1 + build v2）
- `src/tx.rs` — v0 交易组装（ALT）+ 签名 + bincode 序列化 + RPC 广播

## 实测记录（2026-08-07）

- 1 SOL → 73.626 USDC（$73.63），路由 Aquifer
- 100 USDC → 1.3583 SOL（$73.62），路由 SolFi V2 —— 正反向一致 ✅
- 100 SOL → 7362 USDC，4 池多跳（Quantum → AlphaQ → HumidiFi → BisonFi），价格影响 0.0000099%
- API：`api.jup.ag/swap/v1/quote`（Metis 路由引擎，v6/v7 已下线）
- **真发验证（--send）**：0.01 SOL → USDC，tx `3P8LZEoBz9FhQw52hycpNbAXPYzB6Qfg2NM8sjRhvdAidTVi3LsBfJSdcP3FZF3LAvsQb4DfEvpHwbWYCZg9aVS`，路由 Invariant → Aquifer，627B v0 交易，fee 7074 lamports（≈$0.0005），**getSignatureStatuses = finalized**（slot 437781453）

## 踩坑

- reqwest 0.12 的代理是内置能力（无 `proxy` feature，加会解析失败）
- Jupiter 响应字段是 camelCase，serde 需逐个 `#[serde(rename)]`
- 国内网络需代理访问 api.jup.ag（Clash 127.0.0.1:7890）
- 首次 cargo build 需下载依赖（crates.io 直连可用，21s 编译完成）
- **solana-sdk 2.x API 迁移**（vs 1.x）：
  - `Message::try_compile_v0` → `solana_sdk::message::v0::Message::try_compile`
  - `AddressLookupTableAccount` 在 `solana_sdk::message` 顶层（不再有 address_lookup_table_account 子模块）
  - `VersionedMessage` 在 `solana_sdk::message` 顶层（versions 模块是私有的）
  - `VersionedTransaction::sign()` 移除 → 用 `VersionedTransaction::try_new(VersionedMessage::V0(msg), &[&keypair])` 一步签名
  - `tx.serialize()` 移除 → `bincode::serialize(&tx)`（需 bincode 依赖）
  - `Keypair::from_bytes` 弃用 → `Keypair::try_from(bytes.as_slice())`

## 路线图

1. ✅ quote（v1）
2. ✅ build（v2/build，Router 路径）
3. ✅ tx 组装（v0 + ALT + computeBudget + cleanup）与本地签名（dry-run 753B 验证）
4. ⏳ `--send` 真发验证（与 swap_mainnet.mjs 对照，同钱包同金额）
5. ⏳ 池子价格直读（对标 pool_price.py）
