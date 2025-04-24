use crate::blockchain::Blockchain;
use std::fs::{self, File};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StorageError {
    #[error("Failed to read blockchain: {0}")]
    ReadError(#[from] io::Error),
    
    #[error("Failed to serialize blockchain: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("Directory doesn't exist: {0}")]
    DirectoryNotFound(PathBuf),
}

#[derive(Debug, Clone)]
pub struct ChainStorage {
    data_dir: PathBuf,
}

impl ChainStorage {
    pub fn new<P: AsRef<Path>>(data_dir: P) -> Result<Self, StorageError> {
        let data_dir = data_dir.as_ref().to_path_buf();
        
        if !data_dir.exists() {
            fs::create_dir_all(&data_dir)?;
        }
        
        Ok(ChainStorage { data_dir })
    }
    
    pub fn save_blockchain(&self, blockchain: &Blockchain) -> Result<(), StorageError> {
        let file_path = self.data_dir.join("blockchain.json");
        let serialized = serde_json::to_string_pretty(blockchain)?;
        
        let mut file = File::create(file_path)?;
        file.write_all(serialized.as_bytes())?;
        
        Ok(())
    }
    
    pub fn load_blockchain(&self) -> Result<Blockchain, StorageError> {
        let file_path = self.data_dir.join("blockchain.json");
        
        if !file_path.exists() {
            // If no blockchain file exists, create a new one
            return Ok(Blockchain::new());
        }
        
        let mut file = File::open(file_path)?;
        let mut contents = String::new();
        file.read_to_string(&mut contents)?;
        
        let blockchain = serde_json::from_str(&contents)?;
        
        Ok(blockchain)
    }
} 