use serde::{Deserialize, Serialize};
use solana_account::Account;
use solana_pubkey::Pubkey;
use std::fs;
use std::fs::File;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

#[derive(Serialize, Deserialize)]
pub struct AccountWithAddress {
    pub address: Pubkey,
    pub account: Account,
}

impl AccountWithAddress {
    fn get_filename(&self) -> String {
        format!("account_{}.json", self.address)
    }

    pub fn save_to_file(&self) -> eyre::Result<()> {
        let filename = self.get_filename();
        let serialized = serde_json::to_string(self)?;
        let data_dir = Path::new("data");
        if !data_dir.exists() {
            fs::create_dir(data_dir)?;
        }
        let file_path = data_dir.join(filename);
        let mut file = File::create(file_path)?;
        file.write_all(serialized.as_bytes())?;

        Ok(())
    }

    pub fn read_account(path: PathBuf) -> eyre::Result<AccountWithAddress> {
        let mut file = File::open(&path)?;
        let mut contents = String::new();
        file.read_to_string(&mut contents)?;

        let account_with_address: Self = serde_json::from_str(&contents)?;
        Ok(account_with_address)
    }

    pub fn read_all() -> eyre::Result<Vec<Self>> {
        let data_dir = Path::new("data");
        if !data_dir.exists() {
            return Ok(vec![]);
        }

        let mut accounts = Vec::new();

        for entry in fs::read_dir(data_dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.is_file()
                && path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .is_some_and(|name| name.starts_with("account_") && name.ends_with(".json"))
            {
                accounts.push(Self::read_account(path)?);
            }
        }

        Ok(accounts)
    }
}
