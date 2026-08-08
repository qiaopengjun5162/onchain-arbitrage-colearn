use crate::constants::SOLFI_MARKETS;
use crate::types::{AccountWithAddress, FetchMetadata};
use crate::utils::u64_at_offset;
use solana_pubkey::Pubkey;

const CUTOFF_OFFSET: usize = 488;
const GEN_OFFSET: usize = 464;

fn mm_metadata(market: &Pubkey) -> eyre::Result<(u64, u64)> {
    let acct = AccountWithAddress::read_account(format!("data/account_{market}.json").into())?;
    Ok((
        u64_at_offset(acct.account.data.as_slice(), CUTOFF_OFFSET)?,
        u64_at_offset(acct.account.data.as_slice(), GEN_OFFSET)?,
    ))
}

pub fn display_cutoffs() {
    if let Some(metadata) = FetchMetadata::read() {
        println!("== {metadata} ==");
    }
    for market in SOLFI_MARKETS {
        if let Ok((cutoff, generated)) = mm_metadata(market) {
            println!("{market} cutoff slot={cutoff}, generated slot={generated}");
        }
    }
}
