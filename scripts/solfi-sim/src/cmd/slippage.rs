use crate::cmd::simulate;
use crate::swap::SwapDirection;

/// 完整环滑点验证：USDC → 买 SOL → 卖回 USDC，算环净收益（bps）。
///
/// 对应 Python 版 `scripts/solana_dex_slippage_verify.py`（Day 5 真实滑点验证）。
/// 口径：投入 USDC，在单一市场买 SOL，再在同一市场卖回 USDC，看收回多少。
/// 净收益 = (卖出收回的 USDC - 投入 USDC) / 投入 USDC，单位 bps。
/// 负值 = 摩擦成本（手续费+滑点）> 价差，完整环无套利空间。
pub fn verify_slippage(usdc_amount_in: f64) -> eyre::Result<()> {
    println!("\n=== 完整环滑点验证：{} USDC 投入 ===", usdc_amount_in);
    println!("流程：USDC → 买 SOL（各池）→ 卖回 USDC（同池）\n");

    // 腿 1：USDC → SOL（买入）
    let buy_results = simulate(SwapDirection::UsdcToSol, Some(usdc_amount_in), None, true, false)?;
    let sol_by_market: std::collections::HashMap<String, f64> = buy_results
        .into_iter()
        .filter_map(|r| r.out_amount.map(|sol| (r.market, sol)))
        .collect();

    if sol_by_market.is_empty() {
        println!("未能买到 SOL（任何池）——无法完成环");
        return Ok(());
    }

    let mut rows = Vec::new();
    for (market, sol_out) in sol_by_market {
        if sol_out <= 0.0 {
            continue;
        }
        // 腿 2：SOL → USDC（卖出同池）
        if let Ok(sell_results) = simulate(SwapDirection::SolToUsdc, Some(sol_out), None, true, false)
        {
            if let Some(sell_result) = sell_results.into_iter().find(|r| r.market == market) {
                if let Some(usdc_out) = sell_result.out_amount {
                    let net_bps = (usdc_out - usdc_amount_in) / usdc_amount_in * 10_000.0;
                    let buy_price = usdc_amount_in / sol_out;
                    let sell_price = usdc_out / sol_out;
                    rows.push((market, buy_price, sell_price, usdc_out, net_bps));
                }
            }
        }
    }

    if rows.is_empty() {
        println!("任何池都无法完成完整环");
        return Ok(());
    }

    rows.sort_by(|a, b| a.4.partial_cmp(&b.4).unwrap());
    println!(
        "{:<24}{:>12}{:>12}{:>14}{:>12}",
        "市场", "买价(USDC/SOL)", "卖价(USDC/SOL)", "收回USDC", "净收益bps"
    );
    for (market, buy_p, sell_p, usdc_out, net_bps) in &rows {
        println!(
            "{:<24}{:>12.6}{:>12.6}{:>14.4}{:>12.2}",
            market, buy_p, sell_p, usdc_out, net_bps
        );
    }

    let best = rows.last().unwrap();
    println!(
        "\n结论：最优环 {:<24} 净收益 {:.2} bps",
        best.0, best.4
    );
    if best.4 > 0.0 {
        println!("⚠️ 存在正收益环——需复核池子状态与手续费口径");
    } else {
        println!("完整环恒负：主流池摩擦成本（手续费+滑点）> 价差，无套利空间（与 D5 结论一致）");
    }
    Ok(())
}
