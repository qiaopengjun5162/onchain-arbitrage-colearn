//! Solana 套利研究 CLI（Rust 版）
//!
//! 用法示例：
//!   cargo run -- quote                                    # SOL→USDC 三档 + 反向
//!   cargo run -- quote --in SOL --out USDC --amount 1     # 自定义
//!   cargo run -- quote --proxy http://127.0.0.1:7890
//!
//! 代理：默认读 HTTPS_PROXY 环境变量；显式 --proxy 优先。

mod jupiter;
mod spread;
mod tx;

use anyhow::Result;
use clap::{Parser, Subcommand};
use solana_sdk::signer::Signer;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "solana-rs", version, about = "Solana 套利研究脚本（Rust 版）")]
struct Cli {
    /// 代理地址，如 http://127.0.0.1:7890（默认读 HTTPS_PROXY）
    #[arg(long, global = true)]
    proxy: Option<String>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// 获取 Jupiter 报价（SOL/USDC 双向）
    Quote {
        /// 输入代币：SOL 或 USDC
        #[arg(long, default_value = "SOL")]
        in_token: String,
        /// 输出代币：SOL 或 USDC
        #[arg(long, default_value = "USDC")]
        out_token: String,
        /// 输入数量（原生单位，如 1 = 1 SOL / 1 USDC）
        #[arg(long, default_value_t = 1.0)]
        amount: f64,
        /// 滑点 bps（50 = 0.5%）
        #[arg(long, default_value_t = 50)]
        slippage_bps: u32,
    },
    /// 构造 swap 交易指令（Router 路径，只读不发送）
    Build {
        #[arg(long, default_value = "SOL")]
        in_token: String,
        #[arg(long, default_value = "USDC")]
        out_token: String,
        /// 输入数量（原生单位）
        #[arg(long, default_value_t = 0.01)]
        amount: f64,
        #[arg(long, default_value_t = 100)]
        slippage_bps: u32,
        /// 发起钱包地址（taker）
        #[arg(long)]
        taker: String,
    },
    /// 完整 swap：build → 组装 v0 → 签名。默认 dry-run（不广播），--send 才广播
    Swap {
        #[arg(long, default_value = "SOL")]
        in_token: String,
        #[arg(long, default_value = "USDC")]
        out_token: String,
        /// 输入数量（原生单位，默认 0.01 极小金额）
        #[arg(long, default_value_t = 0.01)]
        amount: f64,
        #[arg(long, default_value_t = 100)]
        slippage_bps: u32,
        /// 密钥文件路径（默认 ~/.config/solana/id.json）
        #[arg(long)]
        keypair: Option<PathBuf>,
        /// 广播交易到主网（默认 dry-run 不广播）
        #[arg(long)]
        send: bool,
    },
    /// 打印所有支持的代币对（后续扩展）
    #[allow(dead_code)]
    Pairs,
    /// DEX 价差监控：Raydium 直读 vs Jupiter 多金额采样
    Spread,
}

fn mint_of(token: &str) -> Result<(&'static str, u8)> {
    match token.to_uppercase().as_str() {
        "SOL" => Ok((jupiter::SOL_MINT, 9)),
        "USDC" => Ok((jupiter::USDC_MINT, 6)),
        other => anyhow::bail!("暂不支持代币 {other}，仅 SOL/USDC"),
    }
}

fn resolve_proxy(cli_proxy: &Option<String>) -> Option<String> {
    if let Some(p) = cli_proxy {
        return Some(p.clone());
    }
    std::env::var("HTTPS_PROXY").ok().filter(|s| !s.is_empty())
}

async fn run_quote(client: &jupiter::JupiterClient, in_token: &str, out_token: &str, amount: f64, slippage: u32) -> Result<()> {
    let (in_mint, in_dec) = mint_of(in_token)?;
    let (out_mint, out_dec) = mint_of(out_token)?;
    let raw_amount = (amount * 10f64.powi(in_dec as i32)) as u64;

    let q = client.quote(in_mint, out_mint, raw_amount, slippage).await?;

    let in_amt = jupiter::fmt_amount(&q.in_amount, in_dec);
    let out_amt = jupiter::fmt_amount(&q.out_amount, out_dec);
    let price = if out_token.to_uppercase() == "USDC" {
        out_amt / in_amt
    } else {
        in_amt / out_amt
    };
    let min_out = q
        .other_amount_threshold
        .as_deref()
        .map(|s| jupiter::fmt_amount(s, out_dec))
        .unwrap_or(0.0);
    let hops = jupiter::route_labels(&q).join(" → ");

    println!("  📥 输入:   {in_amt:.6} {in_token}");
    println!("  📤 输出:   {out_amt:.6} {out_token}");
    println!("  💰 价格:   1 {in_token} ≈ ${price:.4}");
    println!("  📊 滑点:   {} bps", q.slippage_bps);
    println!("  ⚠️  最少收:  {min_out:.6} {out_token}");
    println!("  📈 价格影响: {}", q.price_impact_pct.as_deref().unwrap_or("-"));
    println!("  🛣️  路由:   {}", if hops.is_empty() { "-" } else { &hops });
    Ok(())
}

async fn run_build(client: &jupiter::JupiterClient, in_token: &str, out_token: &str, amount: f64, slippage: u32, taker: &str) -> Result<()> {
    let (in_mint, in_dec) = mint_of(in_token)?;
    let (out_mint, _) = mint_of(out_token)?;
    let raw_amount = (amount * 10f64.powi(in_dec as i32)) as u64;

    let b = client.build(in_mint, out_mint, raw_amount, taker, slippage).await?;

    let route: Vec<String> = b.route_plan.iter().map(|r| r.swap_info.label.clone()).collect();
    println!("  🛣️  路由:   {}", route.join(" → "));
    println!("  📦 swap 指令: programId={}", &b.swap_instruction.program_id[..16.min(b.swap_instruction.program_id.len())]);
    println!("  📦 setup 指令: {} 个", b.setup_instructions.len());
    println!("  📦 computeBudget 指令: {} 个", b.compute_budget_instructions.len());
    println!("  📦 cleanup 指令: {}", if b.cleanup_instruction.is_some() { "有" } else { "无" });
    println!("  📋 lookup table: {} 张", b.alts.len());
    for (addr, addrs) in &b.alts {
        println!("     - {addr}  ({} 地址)", addrs.len());
    }
    // 指令 data 长度（base64 解出来的字节数，用于估算交易大小）
    use base64::Engine;
    let swap_data_len = base64::engine::general_purpose::STANDARD
        .decode(&b.swap_instruction.data)
        .map(|d| d.len())
        .unwrap_or(0);
    println!("  📐 swap 指令数据: {swap_data_len} bytes (base64 decoded)");
    println!("  🔢 金额: {amount} {in_token} → {out_token} (slippage {slippage} bps)");
    Ok(())
}

async fn run_swap(
    client: &jupiter::JupiterClient,
    proxy: &Option<String>,
    in_token: &str,
    out_token: &str,
    amount: f64,
    slippage: u32,
    keypair_path: &PathBuf,
    send: bool,
) -> Result<()> {
    let (in_mint, in_dec) = mint_of(in_token)?;
    let (out_mint, _) = mint_of(out_token)?;
    let raw_amount = (amount * 10f64.powi(in_dec as i32)) as u64;

    // 1. 密钥（只本地读取签名，不打印）
    let keypair = tx::load_keypair(keypair_path)?;
    let payer = keypair.pubkey();
    println!("  👛 钱包:   {payer}");

    // 2. build
    let b = client
        .build(in_mint, out_mint, raw_amount, &payer.to_string(), slippage)
        .await?;
    let route: Vec<String> = b.route_plan.iter().map(|r| r.swap_info.label.clone()).collect();
    println!("  🛣️  路由:   {}", route.join(" → "));
    println!("  📋 lookup table: {} 张", b.alts.len());

    // 3. blockhash + 组装 v0 + 签名
    let rpc = tx::rpc_url_from_env()?;
    let blockhash = tx::fetch_blockhash(proxy.as_deref(), &rpc).await?;
    let message = tx::assemble_v0(&b, &payer, blockhash)?;
    let signed = tx::sign_message(message, &keypair)?;
    let size = tx::serialize_tx(&signed)?.len();
    println!("  📄 v0 交易: {size} bytes，已签名（blockhash {blockhash}）");

    if !send {
        println!("  ⏸️  dry-run：未广播（主网 0 花费）");
        println!("     想真发：solana-rs swap --send （会消耗真实 SOL + Gas）");
        return Ok(());
    }

    // 4. 广播
    println!("  🚀 广播 {amount} {in_token} → {out_token} ...");
    let sig = tx::send_tx(proxy.as_deref(), &rpc, &signed).await?;
    println!("  ✅ tx: {sig}");
    println!("  🔗 Solscan: https://solscan.io/tx/{sig}");
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let proxy = resolve_proxy(&cli.proxy);
    let client = jupiter::JupiterClient::new(proxy.as_deref())?;

    match cli.command {
        Commands::Quote { in_token, out_token, amount, slippage_bps } => {
            println!("{}", "=".repeat(56));
            println!("  Jupiter Quote: {in_token} → {out_token} ({amount})");
            println!("{}", "=".repeat(56));
            run_quote(&client, &in_token, &out_token, amount, slippage_bps).await?;
            println!("{}", "=".repeat(56));
        }
        Commands::Build { in_token, out_token, amount, slippage_bps, taker } => {
            println!("{}", "=".repeat(56));
            println!("  Jupiter Build: {in_token} → {out_token} ({amount})");
            println!("{}", "=".repeat(56));
            run_build(&client, &in_token, &out_token, amount, slippage_bps, &taker).await?;
            println!("{}", "=".repeat(56));
        }
        Commands::Swap { in_token, out_token, amount, slippage_bps, keypair, send } => {
            let kp = keypair.unwrap_or_else(|| {
                PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".into()))
                    .join(".config/solana/id.json")
            });
            println!("{}", "=".repeat(56));
            println!("  Swap {in_token} → {out_token} ({amount}) [{}]", if send { "SEND" } else { "dry-run" });
            println!("{}", "=".repeat(56));
            run_swap(&client, &proxy, &in_token, &out_token, amount, slippage_bps, &kp, send).await?;
            println!("{}", "=".repeat(56));
        }
        Commands::Pairs => {
            println!("SOL/USDC 双向可用（后续扩展代币表）");
        }
        Commands::Spread => {
            spread::run(proxy.as_deref()).await?;
        }
    }
    Ok(())
}
