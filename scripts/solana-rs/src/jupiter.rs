//! Jupiter Swap API 客户端（Rust 版）
//!
//! 对应 Python 版 `scripts/jupiter_swap_d3.py` 的 quote 部分。
//! 用 2026-08-07 实测的新 API：`api.jup.ag/swap/v1`（Metis 路由引擎），
//! 旧版 quote-api.jup.ag v6/v7 已下线/被墙。
//!
//! 参考：https://station.jup.ag/docs/api/swap-api

use anyhow::{Context, Result};
use serde::Deserialize;
use std::collections::HashMap;

pub const SOL_MINT: &str = "So11111111111111111111111111111111111111112";
pub const USDC_MINT: &str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const BASE_V1: &str = "https://api.jup.ag/swap/v1";
const BASE_V2: &str = "https://api.jup.ag/swap/v2";

/// /quote 响应的核心字段（只取研究需要的部分）
#[derive(Debug, Deserialize)]
#[allow(dead_code)] // 部分字段留给后续 swap/build 模块使用
pub struct Quote {
    #[serde(rename = "inputMint")]
    pub input_mint: String,
    #[serde(rename = "outputMint")]
    pub output_mint: String,
    #[serde(rename = "inAmount")]
    pub in_amount: String,
    #[serde(rename = "outAmount")]
    pub out_amount: String,
    #[serde(rename = "otherAmountThreshold")]
    pub other_amount_threshold: Option<String>,
    #[serde(rename = "swapMode")]
    pub swap_mode: String,
    #[serde(rename = "slippageBps")]
    pub slippage_bps: u32,
    #[serde(rename = "priceImpactPct")]
    pub price_impact_pct: Option<String>,
    #[serde(rename = "routePlan")]
    pub route_plan: Option<Vec<RoutePlan>>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct RoutePlan {
    /// 路由占比（可能带小数，如 88.86）
    pub percent: f64,
    #[serde(rename = "swapInfo")]
    pub swap_info: SwapInfo,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct SwapInfo {
    pub label: String,
    #[serde(rename = "inputMint")]
    pub input_mint: String,
    #[serde(rename = "outputMint")]
    pub output_mint: String,
}

/// /swap/v2/build 的指令描述（programId + accounts + base64 data）
#[derive(Debug, Deserialize, Clone)]
pub struct IxDto {
    #[serde(rename = "programId")]
    pub program_id: String,
    pub accounts: Vec<AccountMetaDto>,
    /// base64 编码的指令数据
    pub data: String,
}

#[derive(Debug, Deserialize, Clone)]
pub struct AccountMetaDto {
    pub pubkey: String,
    #[serde(rename = "isSigner")]
    pub is_signer: bool,
    #[serde(rename = "isWritable")]
    pub is_writable: bool,
}

/// /swap/v2/build 响应（Router 路径，raw instructions）
#[derive(Debug, Deserialize)]
pub struct Build {
    #[serde(rename = "swapInstruction")]
    pub swap_instruction: IxDto,
    #[serde(rename = "setupInstructions")]
    pub setup_instructions: Vec<IxDto>,
    #[serde(rename = "computeBudgetInstructions")]
    pub compute_budget_instructions: Vec<IxDto>,
    #[serde(rename = "cleanupInstruction")]
    pub cleanup_instruction: Option<IxDto>,
    /// ALT 地址 → 该表包含的地址列表（组装 v0 交易直接用，无需再查 RPC）
    #[serde(rename = "addressesByLookupTableAddress")]
    pub alts: HashMap<String, Vec<String>>,
    #[serde(rename = "routePlan")]
    pub route_plan: Vec<RoutePlan>,
}

pub struct JupiterClient {
    http: reqwest::Client,
}

impl JupiterClient {
    /// 创建客户端；proxy 为空则直连（如本机无 Clash 或已全局代理）
    pub fn new(proxy: Option<&str>) -> Result<Self> {
        let mut builder = reqwest::Client::builder().user_agent("solana-rs/0.1");
        if let Some(p) = proxy {
            builder = builder.proxy(
                reqwest::Proxy::all(p).with_context(|| format!("非法代理地址: {p}"))?,
            );
        }
        Ok(Self {
            http: builder.build()?,
        })
    }

    /// 获取报价。amount 是原始单位（SOL=1e9 lamports, USDC=1e6）。
    pub async fn quote(
        &self,
        input_mint: &str,
        output_mint: &str,
        amount: u64,
        slippage_bps: u32,
    ) -> Result<Quote> {
        let url = format!("{BASE_V1}/quote");
        let resp = self
            .http
            .get(&url)
            .query(&[
                ("inputMint", input_mint),
                ("outputMint", output_mint),
                ("amount", &amount.to_string()),
                ("slippageBps", &slippage_bps.to_string()),
                ("swapMode", "ExactIn"),
            ])
            .send()
            .await
            .with_context(|| format!("Jupiter quote 请求失败: {url}"))?;

        let status = resp.status();
        let body = resp.text().await?;
        if !status.is_success() {
            anyhow::bail!("Jupiter quote HTTP {status}: {}", body.chars().take(300).collect::<String>());
        }
        let quote: Quote = serde_json::from_str(&body)
            .with_context(|| "解析 quote 响应失败（可能结构变了）")?;
        Ok(quote)
    }

    /// 构造 swap 交易指令（Router 路径）。taker 是发起钱包地址。
    /// 返回 swap + setup + computeBudget 指令 + ALT 表，可直接组装 v0 交易。
    pub async fn build(
        &self,
        input_mint: &str,
        output_mint: &str,
        amount: u64,
        taker: &str,
        slippage_bps: u32,
    ) -> Result<Build> {
        let url = format!("{BASE_V2}/build");
        let resp = self
            .http
            .get(&url)
            .query(&[
                ("inputMint", input_mint),
                ("outputMint", output_mint),
                ("amount", &amount.to_string()),
                ("taker", taker),
                ("slippageBps", &slippage_bps.to_string()),
            ])
            .send()
            .await
            .with_context(|| format!("Jupiter build 请求失败: {url}"))?;

        let status = resp.status();
        let body = resp.text().await?;
        if !status.is_success() {
            anyhow::bail!(
                "Jupiter build HTTP {status}: {}",
                body.chars().take(300).collect::<String>()
            );
        }
        let build: Build = serde_json::from_str(&body)
            .with_context(|| "解析 build 响应失败（可能结构变了）")?;
        Ok(build)
    }
}

/// 原始单位 → 人类可读（decimals: SOL=9, USDC=6）
pub fn fmt_amount(raw: &str, decimals: u8) -> f64 {
    let v: u64 = raw.parse().unwrap_or(0);
    v as f64 / 10f64.powi(decimals as i32)
}

/// 路由标签列表，如 ["PancakeSwap", "Meteora DLMM"]
pub fn route_labels(quote: &Quote) -> Vec<String> {
    quote
        .route_plan
        .as_ref()
        .map(|p| p.iter().map(|r| r.swap_info.label.clone()).collect())
        .unwrap_or_default()
}
