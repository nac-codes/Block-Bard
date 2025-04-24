use crate::blockchain::block::{Block, BlockData};
use crate::crypto::hash::Hash;
use std::collections::HashMap;
use thiserror::Error;
use serde::{Serialize, Deserialize};

#[derive(Debug, Error)]
pub enum BlockchainError {
    #[error("Invalid block: {0}")]
    InvalidBlock(String),
    
    #[error("Block with index {0} already exists")]
    BlockExists(u64),
    
    #[error("Previous block hash doesn't match")]
    HashMismatch,
    
    #[error("Block index out of sequence. Expected {0}, got {1}")]
    IndexOutOfSequence(u64, u64),
    
    #[error("Branch not found: {0}")]
    BranchNotFound(String),
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Blockchain {
    pub blocks: Vec<Block>,
    pub branches: HashMap<String, Vec<u64>>,
    pub current_difficulty: u64,
    pub difficulty_adjustment_interval: u64,
    pub target_block_time_seconds: u64,
}

impl Blockchain {
    pub fn new() -> Self {
        let genesis = Block::genesis();
        let mut branches = HashMap::new();
        branches.insert("main".to_string(), vec![0]);
        
        Blockchain {
            blocks: vec![genesis],
            branches,
            current_difficulty: 1,
            difficulty_adjustment_interval: 10,
            target_block_time_seconds: 30,
        }
    }
    
    pub fn add_block(&mut self, block: Block) -> Result<(), BlockchainError> {
        let last_block = self.blocks.last().unwrap();
        
        // Validate block
        if block.index != last_block.index + 1 {
            return Err(BlockchainError::IndexOutOfSequence(last_block.index + 1, block.index));
        }
        
        if block.previous_hash != last_block.hash {
            return Err(BlockchainError::HashMismatch);
        }
        
        if !block.is_valid() {
            return Err(BlockchainError::InvalidBlock("Block hash is invalid".to_string()));
        }
        
        // Update branch tracking
        if let Some(branch_blocks) = self.branches.get_mut(&block.data.branch_id) {
            branch_blocks.push(block.index);
        } else if let Some(_) = &block.data.branch_metadata {
            // This is a new branch
            self.branches.insert(block.data.branch_id.clone(), vec![block.index]);
        } else {
            return Err(BlockchainError::BranchNotFound(block.data.branch_id.clone()));
        }
        
        self.blocks.push(block);
        
        // Adjust difficulty if needed
        if self.blocks.len() as u64 % self.difficulty_adjustment_interval == 0 {
            self.adjust_difficulty();
        }
        
        Ok(())
    }
    
    pub fn create_block(&self, content: String, author: String, branch_id: String) -> Block {
        let last_block = self.blocks.last().unwrap();
        let index = last_block.index + 1;
        
        let data = BlockData {
            content,
            author,
            branch_id,
            branch_metadata: None,
        };
        
        Block::new(index, last_block.hash.clone(), data, self.current_difficulty)
    }
    
    pub fn create_branch_block(
        &self,
        content: String,
        author: String,
        branch_name: String,
        branch_description: String,
        parent_block_index: u64,
    ) -> Result<Block, BlockchainError> {
        if parent_block_index >= self.blocks.len() as u64 {
            return Err(BlockchainError::InvalidBlock(format!("Parent block index {} doesn't exist", parent_block_index)));
        }
        
        let last_block = self.blocks.last().unwrap();
        let index = last_block.index + 1;
        
        let branch_id = format!("branch_{}", branch_name.to_lowercase().replace(" ", "_"));
        
        let branch_metadata = Some(crate::blockchain::block::BranchMetadata {
            name: branch_name,
            description: branch_description,
            parent_block_index,
        });
        
        let data = BlockData {
            content,
            author,
            branch_id,
            branch_metadata,
        };
        
        // Branch blocks have a higher difficulty
        let branch_difficulty = self.current_difficulty + 1;
        
        Ok(Block::new(index, last_block.hash.clone(), data, branch_difficulty))
    }
    
    fn adjust_difficulty(&mut self) {
        if self.blocks.len() < 2 {
            return;
        }
        
        let blocks_count = self.difficulty_adjustment_interval as usize;
        let start_index = self.blocks.len() - blocks_count;
        
        let start_block = &self.blocks[start_index];
        let end_block = self.blocks.last().unwrap();
        
        let start_time = start_block.timestamp;
        let end_time = end_block.timestamp;
        
        let duration = (end_time - start_time).num_seconds() as u64;
        let expected_duration = self.target_block_time_seconds * blocks_count as u64;
        
        if duration < expected_duration / 2 {
            self.current_difficulty += 1;
        } else if duration > expected_duration * 2 {
            if self.current_difficulty > 1 {
                self.current_difficulty -= 1;
            }
        }
        
        println!("Difficulty adjusted to: {}", self.current_difficulty);
    }
    
    pub fn get_blocks_by_branch(&self, branch_id: &str) -> Vec<&Block> {
        match self.branches.get(branch_id) {
            Some(indices) => {
                indices.iter()
                    .map(|&index| &self.blocks[index as usize])
                    .collect()
            },
            None => Vec::new(),
        }
    }
    
    pub fn get_block_by_index(&self, index: u64) -> Option<&Block> {
        if index < self.blocks.len() as u64 {
            Some(&self.blocks[index as usize])
        } else {
            None
        }
    }
    
    pub fn get_latest_block(&self) -> &Block {
        self.blocks.last().unwrap()
    }
    
    pub fn is_valid_chain(&self) -> bool {
        for i in 1..self.blocks.len() {
            let current_block = &self.blocks[i];
            let previous_block = &self.blocks[i - 1];
            
            if current_block.previous_hash != previous_block.hash {
                return false;
            }
            
            if !current_block.is_valid() {
                return false;
            }
            
            if current_block.index != previous_block.index + 1 {
                return false;
            }
        }
        
        true
    }
    
    pub fn rebuild_branches(&mut self) {
        // Clear existing branches
        self.branches.clear();
        
        // Recreate branches from blocks
        for block in &self.blocks {
            let branch_id = block.data.branch_id.clone();
            let indices = self.branches.entry(branch_id).or_insert_with(Vec::new);
            indices.push(block.index);
        }
    }
} 