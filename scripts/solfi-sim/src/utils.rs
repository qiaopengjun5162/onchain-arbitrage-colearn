use litesvm::LiteSVM;
use solana_pubkey::Pubkey;
use solana_sdk::program_pack::Pack;
use spl_token::state::Account as AccountState;

pub fn token_balance(svm: &LiteSVM, pubkey: &Pubkey) -> u64 {
    let account = svm.get_account(pubkey).unwrap_or_default();
    let state = AccountState::unpack(&account.data).ok().unwrap_or_default();
    state.amount
}

pub fn u64_at_offset(data: &[u8], offset: usize) -> eyre::Result<u64> {
    let bytes = &data[offset..offset + 8];
    Ok(u64::from_le_bytes(bytes.try_into()?))
}
