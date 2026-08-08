mod args;
mod cmd;
mod constants;
mod swap;
mod types;
mod utils;

use crate::args::{App, Command};
use crate::cmd::{calculate_spread, display_cutoffs, fetch_and_persist_accounts, simulate};
use crate::constants::DEFAULT_RPC_URL;
use clap::Parser;
use dotenv::dotenv;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;
use tracing_subscriber::{EnvFilter, fmt};

#[tokio::main]
async fn main() -> eyre::Result<()> {
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .init();

    let cmd = App::parse().command;

    match cmd {
        Command::FetchAccounts => {
            let rpc_url = {
                let _ = dotenv().ok();
                std::env::var("RPC_URL").ok().filter(|url| !url.trim().is_empty()).unwrap_or_else(
                    || {
                        tracing::warn!("No RPC_URL found in env. Using {}", DEFAULT_RPC_URL);
                        DEFAULT_RPC_URL.to_string()
                    },
                )
            };
            fetch_and_persist_accounts(rpc_url).await?
        }
        Command::Cutoffs => display_cutoffs(),
        Command::Spreads { starting_usdc } => calculate_spread(starting_usdc)?,
        Command::Simulate { amount, direction, slot, ignore_errors } => {
            simulate(direction, amount, slot, ignore_errors, true)?;
        }
    }

    Ok(())
}
