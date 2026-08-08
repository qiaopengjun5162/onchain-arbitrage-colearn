use solana_pubkey::{Pubkey, pubkey};

pub const DEFAULT_RPC_URL: &str = "https://api.mainnet-beta.solana.com";

pub const SOLFI_PROGRAM: Pubkey = pubkey!("SoLFiHG9TfgtdUXUjWAxi3LtvYuFyDLVhBWxdMZxyCe");
pub const WSOL: Pubkey = pubkey!("So11111111111111111111111111111111111111112");
pub const USDC: Pubkey = pubkey!("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v");

pub const SOLFI_MARKETS: &[Pubkey] = &[
    pubkey!("5guD4Uz462GT4Y4gEuqyGsHZ59JGxFN4a3rF6KWguMcJ"),
    pubkey!("DH4xmaWDnTzKXehVaPSNy9tMKJxnYL5Mo5U3oTHFtNYJ"),
    pubkey!("AHhiY6GAKfBkvseQDQbBC7qp3fTRNpyZccuEdYSdPFEf"),
    pubkey!("CAPhoEse9xEH95XmdnJjYrZdNCA8xfUWdy3aWymHa1Vj"),
];
