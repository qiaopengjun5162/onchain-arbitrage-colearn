//! Solana v0 交易组装 + 签名 + 广播（Rust 版）
//!
//! 对标 Node 版 `scripts/swap_mainnet.mjs`：
//! build 指令 → 组装 v0 message（含 ALT）→ 本地签名 → （默认 dry-run）→ --send 广播。
//!
//! 安全：私钥只从 ~/.config/solana/id.json 本地读取用于签名，不打印、不传输。

use anyhow::{Context, Result};
use base64::Engine;
use solana_sdk::hash::Hash;
use solana_sdk::instruction::{AccountMeta, Instruction};
use solana_sdk::message::v0::Message as V0Message;
use solana_sdk::message::AddressLookupTableAccount;
use solana_sdk::message::VersionedMessage;
use solana_sdk::pubkey::Pubkey;
use solana_sdk::signer::keypair::Keypair;
use solana_sdk::signer::Signer;
use solana_sdk::transaction::VersionedTransaction;
use std::path::Path;
use std::str::FromStr;

use crate::jupiter::{Build, IxDto};

/// 从本地 id.json 读取 Keypair（数组格式：64 字节 + 32 字节 pubkey 的 JSON 数组）
pub fn load_keypair(path: &Path) -> Result<Keypair> {
    let raw = std::fs::read_to_string(path)
        .with_context(|| format!("读取密钥文件失败: {}", path.display()))?;
    let bytes: Vec<u8> = serde_json::from_str(&raw)
        .with_context(|| "id.json 不是合法的字节数组（确认是 solana-keygen 生成的文件）")?;
    Keypair::try_from(bytes.as_slice()).context("Keypair 字节解析失败（长度应为 64）")
}

fn ix_from_dto(dto: &IxDto) -> Result<Instruction> {
    let program_id = Pubkey::from_str(&dto.program_id)
        .with_context(|| format!("非法 programId: {}", dto.program_id))?;
    let accounts = dto
        .accounts
        .iter()
        .map(|a| {
            Ok(AccountMeta {
                pubkey: Pubkey::from_str(&a.pubkey)
                    .with_context(|| format!("非法账户地址: {}", a.pubkey))?,
                is_signer: a.is_signer,
                is_writable: a.is_writable,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let data = base64::engine::general_purpose::STANDARD
        .decode(&dto.data)
        .context("指令 data 不是合法 base64")?;
    Ok(Instruction {
        program_id,
        accounts,
        data,
    })
}

/// 用 build 响应组装 v0 消息（不签名）。blockhash 需在签名前获取最新值。
pub fn assemble_v0(build: &Build, payer: &Pubkey, blockhash: Hash) -> Result<V0Message> {
    // 指令顺序与 Node 版一致：computeBudget + setup + swap + cleanup
    let mut ixs: Vec<Instruction> = Vec::new();
    for dto in &build.compute_budget_instructions {
        ixs.push(ix_from_dto(dto)?);
    }
    for dto in &build.setup_instructions {
        ixs.push(ix_from_dto(dto)?);
    }
    ixs.push(ix_from_dto(&build.swap_instruction)?);
    if let Some(cleanup) = &build.cleanup_instruction {
        ixs.push(ix_from_dto(cleanup)?);
    }

    // ALT 表：build 响应已给出每张表的完整地址列表，无需再查 RPC
    let alts: Vec<AddressLookupTableAccount> = build
        .alts
        .iter()
        .map(|(key, addrs)| {
            Ok(AddressLookupTableAccount {
                key: Pubkey::from_str(key).with_context(|| format!("非法 ALT 地址: {key}"))?,
                addresses: addrs
                    .iter()
                    .map(|a| Pubkey::from_str(a))
                    .collect::<std::result::Result<Vec<_>, _>>()
                    .context("ALT 内存在非法地址")?,
            })
        })
        .collect::<Result<Vec<_>>>()?;

    let message = V0Message::try_compile(payer, &ixs, &alts, blockhash)
        .context("v0 消息编译失败（账户超出限制？）")?;
    Ok(message)
}

/// 用 Keypair 对 v0 消息签名，返回已签名交易
pub fn sign_message(message: V0Message, keypair: &Keypair) -> Result<VersionedTransaction> {
    VersionedTransaction::try_new(VersionedMessage::V0(message), &[keypair])
        .context("交易签名失败")
}

/// 序列化交易（bincode）
pub fn serialize_tx(tx: &VersionedTransaction) -> Result<Vec<u8>> {
    bincode::serialize(tx).context("交易序列化失败")
}

/// 广播交易到 RPC。encoding 用 base64（v0 交易默认支持）。
pub async fn send_tx(proxy: Option<&str>, rpc_url: &str, tx: &VersionedTransaction) -> Result<String> {
    let b64 = base64::engine::general_purpose::STANDARD.encode(serialize_tx(tx)?);
    let body = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sendTransaction",
        "params": [b64, {"encoding": "base64", "preflightCommitment": "confirmed"}]
    });

    let mut builder = reqwest::Client::builder().user_agent("solana-rs/0.1");
    if let Some(p) = proxy {
        builder = builder.proxy(
            reqwest::Proxy::all(p).with_context(|| format!("非法代理地址: {p}"))?,
        );
    }
    let client = builder.build()?;
    let resp = client.post(rpc_url).json(&body).send().await?;
    let status = resp.status();
    let text = resp.text().await?;
    if !status.is_success() {
        anyhow::bail!("RPC HTTP {status}: {}", text.chars().take(300).collect::<String>());
    }
    let v: serde_json::Value = serde_json::from_str(&text)?;
    if let Some(err) = v.get("error") {
        anyhow::bail!("RPC 错误: {err}");
    }
    v["result"]
        .as_str()
        .map(|s| s.to_string())
        .context("RPC 响应缺少 result 字段")
}

/// 从环境变量或默认值解析 RPC 地址（HELIUS_RPC_URL 优先，其次 HELIUS_API_KEY，最后公共 RPC）
pub fn rpc_url_from_env() -> Result<String> {
    if let Ok(u) = std::env::var("HELIUS_RPC_URL") {
        return Ok(u);
    }
    if let Ok(k) = std::env::var("HELIUS_API_KEY") {
        return Ok(format!("https://mainnet.helius-rpc.com/?api-key={k}"));
    }
    // 公共 RPC（国内网络需配代理）
    Ok("https://api.mainnet-beta.solana.com".to_string())
}

/// 获取最新 blockhash（finalized），用于组装交易
pub async fn fetch_blockhash(proxy: Option<&str>, rpc_url: &str) -> Result<Hash> {
    let body = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getLatestBlockhash",
        "params": [{"commitment": "finalized"}]
    });

    let mut builder = reqwest::Client::builder().user_agent("solana-rs/0.1");
    if let Some(p) = proxy {
        builder = builder.proxy(reqwest::Proxy::all(p)?);
    }
    let client = builder.build()?;
    let resp = client.post(rpc_url).json(&body).send().await?;
    let status = resp.status();
    let text = resp.text().await?;
    if !status.is_success() {
        anyhow::bail!("RPC HTTP {status}: {}", text.chars().take(300).collect::<String>());
    }
    let v: serde_json::Value = serde_json::from_str(&text)?;
    if let Some(err) = v.get("error") {
        anyhow::bail!("RPC 错误: {err}");
    }
    let bh = v["result"]["value"]["blockhash"]
        .as_str()
        .context("RPC 响应缺少 blockhash")?;
    Hash::from_str(bh).context("非法 blockhash")
}

#[allow(dead_code)]
pub fn payer_of(kp: &Keypair) -> Pubkey {
    kp.pubkey()
}
