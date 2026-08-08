//! Solana DEX 价差监控（Rust 版）—— D4 主线的 Rust 双实现
//!
//! 双数据源（与 Python 版 solana_dex_spread_monitor.py 对齐）：
//! 1. Helius RPC 直读 Raydium SOL-USDC 池 vault 余额（恒定乘积定价 + 模拟 1 SOL swap）
//! 2. Jupiter Swap API 多金额采样（0.1/1/10/100 SOL）→ 观察不同 AMM 路由选择
//!
//! 原理（notes/solana/datasource-direct-pool-reading.md）：
//! 直接读链上池子优于聚合器报价——池子状态是自己可验证的事实，聚合器是"市场共识价"。

use anyhow::{Context, Result};
use reqwest::Client;
use serde_json::{json, Value};

/// Raydium SOL-USDC 池 vault（D1 已验证）
const SOL_VAULT: &str = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz";
const USDC_VAULT: &str = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz";

const JUPITER_QUOTE: &str = "https://api.jup.ag/swap/v1/quote";
const SOL_MINT: &str = "So11111111111111111111111111111111111111112";
const USDC_MINT: &str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";

/// 采样金额（SOL）：不同量级触发不同 AMM
const SAMPLES_SOL: [f64; 4] = [0.1, 1.0, 10.0, 100.0];

/// 构建带代理的 HTTP 客户端
fn http_client(proxy: Option<&str>) -> Result<Client> {
    let mut builder = Client::builder();
    if let Some(p) = proxy {
        builder = builder.proxy(reqwest::Proxy::all(p).context("无效代理地址")?);
    }
    Ok(builder.build().context("构建 HTTP 客户端失败")?)
}

/// 获取 Helius RPC URL（从 HELIUS_API_KEY 或 HELIUS_RPC_URL 环境变量）
fn helius_rpc() -> Option<String> {
    if let Ok(url) = std::env::var("HELIUS_RPC_URL") {
        return Some(url);
    }
    std::env::var("HELIUS_API_KEY")
        .ok()
        .map(|k| format!("https://mainnet.helius-rpc.com/?api-key={k}"))
}

/// RPC 调用（通用 JSON-RPC）
async fn rpc_call(client: &Client, rpc: &str, method: &str, params: Value) -> Result<Value> {
    let resp = client
        .post(rpc)
        .json(&json!({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}))
        .send()
        .await
        .context("RPC 请求失败")?;
    let v: Value = resp.json().await.context("RPC 响应解析失败")?;
    v.get("result")
        .cloned()
        .context(format!("RPC 错误: {}", v))
}

/// 读 token 账户余额（uiAmount）
async fn token_balance(client: &Client, rpc: &str, account: &str) -> Result<f64> {
    let v = rpc_call(client, rpc, "getTokenAccountBalance", json!([account])).await?;
    v.pointer("/value/uiAmount")
        .and_then(|x| x.as_f64())
        .context("解析余额失败")
}

/// 直读 Raydium SOL-USDC 池：vault 余额 → 价格 + 模拟 1 SOL swap
async fn read_raydium_pool(client: &Client, rpc: &str) -> Result<(f64, f64, f64, f64)> {
    let sol = token_balance(client, rpc, SOL_VAULT).await?;
    let usdc = token_balance(client, rpc, USDC_VAULT).await?;
    if sol <= 0.0 || usdc <= 0.0 {
        anyhow::bail!("池子余额异常: sol={sol} usdc={usdc}");
    }
    let price = usdc / sol;
    // 恒定乘积模拟 1 SOL swap（0.3% 手续费池）
    let k = sol * usdc;
    let new_sol = sol + 1.0;
    let new_usdc = k / new_sol;
    let out = (usdc - new_usdc) * 0.997;
    Ok((sol, usdc, price, out))
}

/// Jupiter 多金额采样：记录每次路由选的 AMM 和价格
async fn jupiter_sample(client: &Client) -> Result<Vec<(f64, String, f64)>> {
    let mut rows = Vec::new();
    for amt in SAMPLES_SOL {
        let url = format!(
            "{JUPITER_QUOTE}?inputMint={SOL_MINT}&outputMint={USDC_MINT}&amount={}",
            (amt * 1e9) as u64
        );
        let resp = client
            .get(&url)
            .header("User-Agent", "hermes-d4-rs")
            .send()
            .await
            .context("Jupiter quote 请求失败")?;
        let v: Value = resp.json().await.context("Jupiter quote 解析失败")?;
        if let Some(plan) = v.get("routePlan").and_then(|p| p.as_array()) {
            for step in plan {
                if let Some(si) = step.get("swapInfo") {
                    let out: f64 = si.get("outAmount").and_then(|x| x.as_str())
                        .and_then(|s| s.parse().ok()).unwrap_or(0.0) / 1e6;
                    let inp: f64 = si.get("inAmount").and_then(|x| x.as_str())
                        .and_then(|s| s.parse().ok()).unwrap_or(0.0) / 1e9;
                    let label = si.get("label").and_then(|x| x.as_str()).unwrap_or("?").to_string();
                    let price = if inp > 0.0 { out / inp } else { 0.0 };
                    rows.push((amt, label, price));
                }
            }
        }
    }
    Ok(rows)
}

/// 打印格式化的价差报告
pub async fn run(proxy: Option<&str>) -> Result<()> {
    let client = http_client(proxy)?;
    let rpc = helius_rpc().context("未找到 HELIUS_API_KEY / HELIUS_RPC_URL 环境变量")?;

    println!("=== Solana DEX 价差监控（Rust）===");
    println!("{}", "-".repeat(60));

    // 1. Raydium 直读
    match read_raydium_pool(&client, &rpc).await {
        Ok((sol, usdc, price, out)) => {
            println!("[直读] Raydium SOL-USDC");
            println!("  vault: {sol:.2} SOL / {usdc:.2} USDC");
            println!("  价格: 1 SOL = ${price:.4}");
            println!("  模拟 1 SOL swap 输出: {out:.4} USDC");
            println!();
        }
        Err(e) => {
            println!("[直读] Raydium 读取失败: {e:#}");
        }
    }

    // 2. Jupiter 采样
    println!("[采样] Jupiter 多金额路由选择");
    match jupiter_sample(&client).await {
        Ok(rows) => {
            println!("  {:<12}{:<20}{}", "金额(SOL)", "AMM", "价格(USDC/SOL)");
            for (amt, label, price) in &rows {
                println!("  {:<12}{:<20}{:.4}", amt, label, price);
            }
            // 3. 价差检测：第一条采样（0.1 SOL 最优路由）vs Raydium 直读
            if let (Ok((_, _, r_price, _)), Some((_, _, j_price))) =
                (read_raydium_pool(&client, &rpc).await, rows.first())
            {
                let spread_bps = (j_price - r_price) / r_price * 10000.0;
                println!();
                println!("  价差: Raydium={r_price:.4} vs Jupiter={j_price:.4} = {spread_bps:.1} bps");
                if spread_bps.abs() >= 30.0 {
                    println!("  ⚠️ 价差 ≥30bps，值得关注");
                }
            }
        }
        Err(e) => println!("[采样] Jupiter 失败: {e:#}"),
    }

    Ok(())
}
