use crate::crypto::hash::{calculate_hash, Hash};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Block {
    pub index: u64,
    pub timestamp: DateTime<Utc>,
    pub previous_hash: Hash,
    pub hash: Hash,
    pub data: BlockData,
    pub nonce: u64,
    pub difficulty: u64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BlockData {
    pub content: String,
    pub author: String,
    pub branch_id: String,
    pub branch_metadata: Option<BranchMetadata>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BranchMetadata {
    pub name: String,
    pub description: String,
    pub parent_block_index: u64,
}

impl Block {
    pub fn new(
        index: u64,
        previous_hash: Hash,
        data: BlockData,
        difficulty: u64,
    ) -> Self {
        let timestamp = Utc::now();
        let nonce = 0;
        let hash = "0".repeat(64); // Placeholder, will be set during mining
        
        let mut block = Block {
            index,
            timestamp,
            previous_hash,
            hash,
            data,
            nonce,
            difficulty,
        };
        
        block.hash = block.calculate_hash();
        block
    }
    
    pub fn genesis() -> Self {
        let data = BlockData {
            content: "Once upon a time in the land of BlockBard, a new story began...".to_string(),
            author: "Genesis".to_string(),
            branch_id: "main".to_string(),
            branch_metadata: None,
        };
        
        // Use a fixed timestamp for the genesis block to ensure consistency across nodes
        let timestamp = DateTime::parse_from_rfc3339("2023-01-01T00:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        
        let mut block = Block {
            index: 0,
            timestamp,
            previous_hash: "0".repeat(64),
            hash: "0".repeat(64),
            data,
            nonce: 0,
            difficulty: 1, // Start with an easy difficulty
        };
        
        // Calculate the hash with the fixed parameters
        block.hash = block.calculate_hash();
        
        // For the genesis block, we ensure it's valid without requiring mining
        block
    }
    
    pub fn calculate_hash(&self) -> Hash {
        let serialized = serde_json::json!({
            "index": self.index,
            "timestamp": self.timestamp.to_rfc3339(),
            "previous_hash": self.previous_hash,
            "data": self.data,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
        });
        
        calculate_hash(&serialized.to_string())
    }
    
    pub fn mine(&mut self) {
        let target = "0".repeat(self.difficulty as usize);
        
        while !self.hash.starts_with(&target) {
            self.nonce += 1;
            self.hash = self.calculate_hash();
        }
        
        println!("Block mined! Nonce: {}, Hash: {}", self.nonce, self.hash);
    }
    
    pub fn is_valid(&self) -> bool {
        // Genesis block has special validation
        if self.index == 0 {
            return self.hash == self.calculate_hash();
        }
        
        let target = "0".repeat(self.difficulty as usize);
        let calculated_hash = self.calculate_hash();
        
        calculated_hash == self.hash && self.hash.starts_with(&target)
    }
}

impl fmt::Display for Block {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Block #{} [{}]\nContent: {}\nAuthor: {}\nBranch: {}\nHash: {}\nPrev: {}",
            self.index,
            self.timestamp,
            self.data.content,
            self.data.author,
            self.data.branch_id,
            self.hash,
            self.previous_hash
        )
    }
} 