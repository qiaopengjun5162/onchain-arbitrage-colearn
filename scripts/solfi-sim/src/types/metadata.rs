use serde::{Deserialize, Serialize};
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::PathBuf;

const FILE_PATH: &str = "data/metadata.json";

#[derive(Serialize, Deserialize)]
pub struct FetchMetadata {
    slot: Option<u64>,

    // backward-compatability
    slot_lower: u64,
    slot_upper: u64,
}

impl FetchMetadata {
    pub fn new(slot: u64) -> Self {
        Self { slot: Some(slot), slot_lower: slot, slot_upper: slot }
    }

    pub fn read() -> Option<Self> {
        let path = PathBuf::from(FILE_PATH);
        if !path.exists() {
            return None;
        }
        let content = fs::read_to_string(&path).ok()?;
        let metadata = serde_json::from_str(&content).ok()?;
        Some(metadata)
    }

    pub fn slot(&self) -> u64 {
        self.slot.unwrap_or(self.slot_lower)
    }

    pub fn save_to_file(&self) -> eyre::Result<()> {
        let path = PathBuf::from(FILE_PATH);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(&path, serde_json::to_string(self)?)?;
        Ok(())
    }
}

impl Display for FetchMetadata {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        if self.slot_lower == self.slot_upper {
            write!(f, "fetched at slot {}", self.slot_lower)
        } else {
            write!(f, "fetched between slots {} and {}", self.slot_lower, self.slot_upper)
        }
    }
}
