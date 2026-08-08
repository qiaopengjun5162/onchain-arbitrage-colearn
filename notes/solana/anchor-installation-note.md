# Anchor Installation 摘记

来源：

- https://www.anchor-lang.com/docs/installation

## 定位

Anchor 安装页是 Solana 本地开发环境准备的基础入口，适合共学前置检查。

它覆盖：

- Rust
- Solana CLI
- Anchor CLI
- Anchor Version Manager, AVM
- Node.js / Yarn
- Solana CLI 基础命令
- devnet / localhost 配置
- devnet airdrop
- local validator
- `anchor init`
- `anchor build`
- `anchor deploy`
- `anchor test`

## 为什么和套利研究有关

即使不马上写执行 bot，也需要能在本地复现协议交互、跑测试、理解账户结构和构造交易。

Anchor 环境准备好后，可以用来：

- 复现 Solana 程序交互
- 阅读和测试 Anchor 协议代码
- 写只读 watcher 或 mock 交互
- 做本地模拟和失败条件测试
- 理解 IDL、账户约束、PDA、CPI 和测试框架

## 共学前置 Checklist

| 检查项 | 状态 | 结果 |
|---|---|---|
| `rustc --version` | ✅ | 1.96.0 (2026-05-25) |
| `solana --version` | ✅ | solana-cli 3.1.14 (Agave) |
| `anchor --version` | ✅ | anchor-cli 0.32.1 |
| `cargo --version` | ✅ | cargo 1.96.0 |
| `solana config get` | ✅ | devnet, keypair at ~/.config/solana/id.json |
| `solana address` | ✅ | `6MZDRo5v8K2NfdohdD76QNpSgk3GH3Aup53BeMaRAEpd` |
| `solana balance` | ✅ | 895.55 SOL (devnet, via Helius RPC) |
| `solana airdrop` | ⚠️ | Rate limit reached（但余额已充足，无需再领） |
| `avm --version` | ⏳ | 待查 |
| `solana-test-validator` | ⏳ | 待查 |
| `anchor init/build/test` | ⏳ | 待做 |

### 环境检查记录（2026-08-06）

版本全部达标：
- solana-cli 3.1.14 ≥ 2.x ✅
- anchor-cli 0.32.1 ≥ 0.30 ✅
- rustc 1.96.0 ≥ 1.75 ✅

Devnet 连接问题：
- `api.devnet.solana.com` 完全不可达（HTTP 000），airdrop 和 balance 均失败
- 这是已知坑：公共 devnet RPC 经常挂
- **下一步**：注册 [Helius](https://www.helius.dev) 免费 tier，获取 API key，配置 `solana config set --url "https://devnet.helius-rpc.com/?api-key=YOUR_KEY"`

## 安全边界

- 本地练习只用 devnet 或 localhost 钱包。
- 不把主钱包 keypair 放到默认 CLI 路径里做实验。
- 不在笔记里保存 seed phrase 或 keypair 内容。
- 任何第三方 bot 或脚本都不要读取主钱包。

## 下一步

1. 检查本机 Rust、Solana CLI、Anchor CLI 版本。
2. 建一个最小 Anchor demo，确认 `anchor build` 和 `anchor test` 能跑通。
3. 把 demo 过程整理成第一篇 Solana 打卡。
