use crate::constants::{SOLFI_MARKETS, SOLFI_PROGRAM, USDC, WSOL};
use crate::swap::{SwapDirection, create_swap_ix};
use crate::types::{AccountWithAddress, FetchMetadata};
use crate::utils::token_balance;
use csv::WriterBuilder;
use eyre::eyre;
use litesvm::LiteSVM;
use solana_account::Account;
use solana_keypair::Keypair;
use solana_pubkey::Pubkey;
use solana_sdk::native_token::sol_to_lamports;
use solana_sdk::program_pack::Pack;
use solana_sdk::rent::Rent;
use solana_sdk::rent_collector::RENT_EXEMPT_RENT_EPOCH;
use solana_signer::Signer;
use solana_system_interface::instruction::transfer;
use solana_transaction::Transaction;
use spl_associated_token_account::get_associated_token_address;
use spl_associated_token_account::instruction::create_associated_token_account_idempotent;
use spl_token::instruction::sync_native;
use spl_token::state::{Account as TokenAccount, AccountState};
use std::io::stdout;

const SOLFI_PROGRAM_PATH: &str = "data/solfi.so";
const DEFAULT_SWAP_AMOUNT_SOL: f64 = 10.0;
const DEFAULT_SWAP_AMOUNT_USDC: f64 = 1000.0;
const SOL_DECIMALS: i32 = 9;
const USDC_DECIMALS: i32 = 6;

fn mk_ata_account(mint: &Pubkey, user: &Pubkey, amount: u64) -> Account {
    let ata = TokenAccount {
        mint: *mint,
        owner: *user,
        amount,
        state: AccountState::Initialized,
        ..Default::default()
    };
    let mut data = vec![0u8; TokenAccount::LEN];
    ata.pack_into_slice(&mut data);
    Account {
        lamports: Rent::default().minimum_balance(data.len()),
        data,
        owner: spl_token::id(),
        executable: false,
        rent_epoch: RENT_EXEMPT_RENT_EPOCH,
    }
}

pub fn simulate(
    direction: SwapDirection,
    amount: Option<f64>,
    slot: Option<u64>,
    ignore_errors: bool,
    prn: bool,
) -> eyre::Result<Vec<SwapResult>> {
    let user_keypair = Keypair::new();
    let user = user_keypair.pubkey();
    let mut svm =
        LiteSVM::new().with_sysvars().with_precompiles().with_sigverify(true).with_spl_programs();

    for acct in AccountWithAddress::read_all()? {
        svm.set_account(acct.address, acct.account)?;
    }
    svm.add_program_from_file(SOLFI_PROGRAM, SOLFI_PROGRAM_PATH)?;
    if let Some(slot) = slot.or(FetchMetadata::read().map(|m| m.slot())) {
        svm.warp_to_slot(slot);
    }

    let (to_mint, from_decimals, to_decimals, in_amount_ui) = match direction {
        SwapDirection::SolToUsdc => {
            (&USDC, SOL_DECIMALS, USDC_DECIMALS, amount.unwrap_or(DEFAULT_SWAP_AMOUNT_SOL))
        }
        SwapDirection::UsdcToSol => {
            (&WSOL, USDC_DECIMALS, SOL_DECIMALS, amount.unwrap_or(DEFAULT_SWAP_AMOUNT_USDC))
        }
    };

    let amount_in_atomic = (in_amount_ui * 10f64.powi(from_decimals)) as u64;
    let total_amount_needed = amount_in_atomic * SOLFI_MARKETS.len() as u64;

    let fee_lamports = sol_to_lamports(1.0);
    match direction {
        SwapDirection::SolToUsdc => {
            let airdrop_amount = total_amount_needed + fee_lamports;
            svm.airdrop(&user, airdrop_amount)
                .map_err(|e| eyre!("failed to airdrop SOL: {}", e.err))?;
        }
        SwapDirection::UsdcToSol => {
            svm.airdrop(&user, fee_lamports)
                .map_err(|e| eyre!("failed to airdrop SOL: {}", e.err))?;
            let usdc_ata = get_associated_token_address(&user, &USDC);
            let usdc_account = mk_ata_account(&USDC, &user, total_amount_needed);
            svm.set_account(usdc_ata, usdc_account)?;
        }
    }

    let wsol_ata = get_associated_token_address(&user, &WSOL);
    let mut wtr = WriterBuilder::new().has_headers(false).from_writer(stdout());
    let mut results = vec![];

    for market in SOLFI_MARKETS {
        let to_ata = get_associated_token_address(&user, to_mint);
        let balance_before = token_balance(&svm, &to_ata);

        let mut instructions = vec![
            create_associated_token_account_idempotent(&user, &user, &WSOL, &spl_token::id()),
            create_associated_token_account_idempotent(&user, &user, &USDC, &spl_token::id()),
        ];

        if direction == SwapDirection::SolToUsdc {
            instructions.extend([
                transfer(&user, &wsol_ata, amount_in_atomic),
                sync_native(&spl_token::id(), &wsol_ata)?,
            ]);
        }

        instructions.push(create_swap_ix(direction, market, &user, &WSOL, &USDC, amount_in_atomic));

        let tx = Transaction::new_with_payer(&instructions, Some(&user));
        let signed_tx = Transaction::new(&[&user_keypair], tx.message, svm.latest_blockhash());

        match svm.send_transaction(signed_tx) {
            Ok(_) => {
                let balance_after = token_balance(&svm, &to_ata);
                let out_amount_atomic = balance_after - balance_before;
                let out_amount_ui = out_amount_atomic as f64 / 10f64.powi(to_decimals);
                let swap_result = SwapResult {
                    market: market.to_string(),
                    in_amount: in_amount_ui,
                    out_amount: Some(out_amount_ui),
                    error: None,
                };
                if prn {
                    wtr.serialize(&swap_result)?;
                }
                results.push(swap_result);
            }
            Err(err) => {
                if !ignore_errors {
                    let swap_result = SwapResult {
                        market: market.to_string(),
                        in_amount: in_amount_ui,
                        out_amount: None,
                        error: Some(err.err.to_string()),
                    };
                    if prn {
                        wtr.serialize(&swap_result)?;
                    }
                    results.push(swap_result);
                }
            }
        }
        wtr.flush()?;
    }

    Ok(results)
}

#[derive(serde::Serialize)]
pub struct SwapResult {
    pub market: String,
    pub in_amount: f64,
    pub out_amount: Option<f64>,
    pub error: Option<String>,
}
