use crate::cmd::{display_cutoffs, simulate};
use crate::swap::SwapDirection;
use std::collections::HashMap;

#[derive(serde::Serialize, Debug)]
struct SpreadAnalysis {
    market: String,
    buy_price_sol_in_usdc: f64,
    sell_price_sol_in_usdc: f64,
    spread_in_usdc: f64,
    spread_bps: f64,
}

/// Calculates the bid-ask spread for each market individually by simulating a full round-trip within that market.
pub fn calculate_spread(usdc_amount_in: f64) -> eyre::Result<()> {
    display_cutoffs();
    println!(
        "\nCalculating spreads based on a round trip starting with {usdc_amount_in:.2} USDC...\n",
    );

    let buy_side_results =
        simulate(SwapDirection::UsdcToSol, Some(usdc_amount_in), None, true, false)?;

    let sol_outputs_by_market: HashMap<String, f64> = buy_side_results
        .into_iter()
        .filter_map(|r| r.out_amount.map(|sol_out| (r.market, sol_out)))
        .collect();

    if sol_outputs_by_market.is_empty() {
        println!("Could not simulate buying SOL on any market. Unable to calculate spread.");
        return Ok(());
    }

    let mut final_analysis = Vec::new();

    for (market, sol_out) in sol_outputs_by_market {
        if sol_out <= 0.0 {
            continue;
        }

        if let Ok(sell_results) =
            simulate(SwapDirection::SolToUsdc, Some(sol_out), None, true, false)
        {
            if let Some(sell_result) = sell_results.into_iter().find(|r| r.market == market) {
                if let Some(usdc_out_final) = sell_result.out_amount {
                    let buy_price = usdc_amount_in / sol_out; // Effective price to buy SOL
                    let sell_price = usdc_out_final / sol_out; // Effective price to sell SOL

                    if buy_price > 0.0 && sell_price > 0.0 {
                        let spread_in_usdc = buy_price - sell_price;
                        let mid_price = (buy_price + sell_price) / 2.0;
                        let spread_bps = (spread_in_usdc / mid_price) * 10_000.0;

                        final_analysis.push(SpreadAnalysis {
                            market: market.clone(),
                            buy_price_sol_in_usdc: buy_price,
                            sell_price_sol_in_usdc: sell_price,
                            spread_in_usdc,
                            spread_bps,
                        });
                    }
                }
            }
        }
    }

    if final_analysis.is_empty() {
        println!("Could not complete a round-trip simulation on any market.");
    } else {
        final_analysis.sort_by(|a, b| a.spread_bps.partial_cmp(&b.spread_bps).unwrap());

        for analysis in final_analysis {
            println!("--- Market: {} ---", analysis.market);
            println!("  Buy SOL at:  ${:<10.4} (Ask)", analysis.buy_price_sol_in_usdc);
            println!("  Sell SOL at: ${:<10.4} (Bid)", analysis.sell_price_sol_in_usdc);
            println!("  Spread:      ${:<10.6}", analysis.spread_in_usdc);
            println!("  Spread:      {:<10.2} bps\n", analysis.spread_bps);
        }
    }

    Ok(())
}
