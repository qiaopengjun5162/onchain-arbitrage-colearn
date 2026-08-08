# Solana 链下存储 Token Metadata 获取方案（Paxon 实战解决）

> 来源：Paxon 群分享（2026-08-08）「获取 solana 链下存储的 token metadata 数据问题已解决」
> 关联：`notes/solana/` 研究线（token 元数据是链上分析的基础数据）

## 问题

获取 Solana 链下存储的 token metadata 数据（如名称、符号、URI、卖家费用等）。这些数据**不在 mint 账户里**，而是存在 Metaplex Token Metadata 程序的 PDA 账户（链下/链上但分离存储）。

## 解法（三步）

1. **计算出 metadataAccount**（PDA 地址）：
   - 种子：`["metadata", METAPLEX_PROGRAM_ID, mint_address]`
   - 用 Metaplex 的约定推导 PDA

2. **获取 metadataAccount 账户信息**（RPC `getAccountInfo`）

3. **解析**：使用 `@metaplex-foundation/js` 库的 `toMetadataAccount` 方法解析原始数据 → 得到 metadata 的 tokenURI 等字段

## 代码要点（Metaplex JS SDK）

```js
import { toMetadataAccount } from '@metaplex-foundation/js';

// 1. 计算 PDA
// 2. RPC 获取账户数据
// 3. 解析
const metadataAccount = toMetadataAccount(rawAccount);
// metadataAccount.data.uri / .name / .symbol / .sellerFeeBasisPoints ...
```

## 关键认知

- **Token metadata 不是存在 mint 里**：mint 只存 supply/decimals/mintAuthority 等核心字段，展示用的元数据（名称/图标/描述）走 Metaplex 的链下存储（URI 指向 JSON，JSON 里才是真正的图/描述）
- **metadataAccount 是 PDA**：用 mint + Metaplex 程序 ID 推导，不是查出来的
- **toMetadataAccount 是解析器**：把账户原始 bytes 解码成结构化对象

## 对套利研究的价值

- 识别新上币/山寨币时，metadata 的 URI/名称/图标可辅助判断「这是什么项目」（配合 listing 哨兵）
- 分析代币真实性：metadata 的 sellerFeeBasisPoints、creators 字段可帮助识别假币/复制币（同名不同 mint）
- 与 `jupiter_program_labels.json`（program label）互补：一个查程序、一个查 token

## 待做/延伸

- [x] ~~用 Helius RPC + Python 实现同款~~（2026-08-08 完成：`scripts/token_metadata.py`，实测 SOL/USDC 都读到）
- [ ] 批量扫描：给定 token 列表 → 拉 metadata → 比对 name/symbol 是否与预期一致（防同名假币）

## 2026-08-08 Python 实现实测记录

- **PDA 推导必须用官方库**：先自实现 base58+sha256+on-curve 检查，推导出 `4tgHLm...`（错误）；官方 solana-py `Pubkey.find_program_address` 得出 `5x38Kp...`（正确，账户存在 908 字节）
  - 教训：PDA 的 bump 检查是 **ed25519 曲线点验证**，不是简单的 `h[0] < 0xF0`——自研轮子不可靠，用官方实现
- 实测输出：
  - USDC: name=USD Coin, symbol=USDC, metadata_account=`5x38Kp4hvdomTCnCrAny4UtMUt5rQBdB6px2K1Ui45Wq`（与 Rust solana-sdk 权威一致 ✅）
  - SOL: name=Wrapped SOL, symbol=SOL（uri 空，原生 SOL 无 uri，符合预期）
- 字符串字段有 `\x00` 固定长度填充 → 用 `split("\x00")[0]` 截断
- 依赖：solana-py（solders）`uv pip install --python <venv> solana`
- JS 版（Metaplex toMetadataAccount）↔ Python 版（solders PDA + 手动解析）双实现完成
