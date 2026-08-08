use crate::swap::SwapDirection;
use clap::{Parser, Subcommand};

#[derive(Debug, Subcommand)]
pub enum Command {
    /// Fetch the solfi wsol/usdc pool accounts and related data
    FetchAccounts,

    /// Print slot cutoff and other metadata from fetched solfi pool data
    Cutoffs,

    /// Simulate spreads
    Spreads {
        /// Amount of USDC to base spreads off of
        starting_usdc: f64,
    },

    /// Simulate a swap in all the solfi wsol/usdc pools
    Simulate {
        /// Amount of SOL or USDC to swap. Input mint depends on --direction
        #[arg(short, long)]
        amount: Option<f64>,

        /// The direction of the swap
        #[arg(short, long, default_value_t = SwapDirection::SolToUsdc)]
        direction: SwapDirection,

        /// Slot to simulate at (default: uses metadata.json)
        #[arg(short, long)]
        slot: Option<u64>,

        /// Don't print simulation errors
        #[arg(long)]
        ignore_errors: bool,
    },
}

#[derive(Debug, Parser)]
#[clap(name = "app", version)]
pub struct App {
    #[clap(subcommand)]
    pub command: Command,
}
