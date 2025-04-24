use super::*;
use crate::blockchain::{Block, BlockData, Blockchain};

#[test]
fn test_genesis_block() {
    let blockchain = Blockchain::new();
    
    assert_eq!(blockchain.blocks.len(), 1);
    assert_eq!(blockchain.blocks[0].index, 0);
    assert_eq!(blockchain.blocks[0].data.branch_id, "main");
    assert!(blockchain.blocks[0].data.branch_metadata.is_none());
    assert!(blockchain.blocks[0].is_valid());
}

#[test]
fn test_add_block() {
    let mut blockchain = Blockchain::new();
    let last_block = blockchain.blocks.last().unwrap();
    
    let data = BlockData {
        content: "Test content".to_string(),
        author: "Test author".to_string(),
        branch_id: "main".to_string(),
        branch_metadata: None,
    };
    
    let mut block = Block::new(
        last_block.index + 1,
        last_block.hash.clone(),
        data,
        blockchain.current_difficulty,
    );
    
    // Mine the block
    block.mine();
    
    // Add the block
    let result = blockchain.add_block(block);
    assert!(result.is_ok());
    
    // Check that the block was added
    assert_eq!(blockchain.blocks.len(), 2);
    assert_eq!(blockchain.blocks[1].index, 1);
    assert_eq!(blockchain.blocks[1].data.content, "Test content");
    assert!(blockchain.blocks[1].is_valid());
}

#[test]
fn test_invalid_block() {
    let mut blockchain = Blockchain::new();
    let last_block = blockchain.blocks.last().unwrap();
    
    let data = BlockData {
        content: "Test content".to_string(),
        author: "Test author".to_string(),
        branch_id: "main".to_string(),
        branch_metadata: None,
    };
    
    // Create a block with an invalid index
    let mut block = Block::new(
        last_block.index + 2, // Should be +1
        last_block.hash.clone(),
        data,
        blockchain.current_difficulty,
    );
    
    // Mine the block
    block.mine();
    
    // Try to add the block
    let result = blockchain.add_block(block);
    assert!(result.is_err());
    
    // Check that the block was not added
    assert_eq!(blockchain.blocks.len(), 1);
}

#[test]
fn test_chain_validity() {
    let mut blockchain = Blockchain::new();
    
    // Add 3 blocks
    for i in 0..3 {
        let last_block = blockchain.blocks.last().unwrap();
        
        let data = BlockData {
            content: format!("Block #{}", i + 1),
            author: "Test author".to_string(),
            branch_id: "main".to_string(),
            branch_metadata: None,
        };
        
        let mut block = Block::new(
            last_block.index + 1,
            last_block.hash.clone(),
            data,
            blockchain.current_difficulty,
        );
        
        // Mine the block
        block.mine();
        
        // Add the block
        blockchain.add_block(block).unwrap();
    }
    
    // Check chain validity
    assert!(blockchain.is_valid_chain());
    
    // Tamper with a block
    blockchain.blocks[1].data.content = "Tampered content".to_string();
    
    // Chain should no longer be valid
    assert!(!blockchain.is_valid_chain());
}

#[test]
fn test_create_branch() {
    let mut blockchain = Blockchain::new();
    
    // Add a regular block first
    let last_block = blockchain.blocks.last().unwrap();
    
    let data = BlockData {
        content: "Block #1".to_string(),
        author: "Test author".to_string(),
        branch_id: "main".to_string(),
        branch_metadata: None,
    };
    
    let mut block = Block::new(
        last_block.index + 1,
        last_block.hash.clone(),
        data,
        blockchain.current_difficulty,
    );
    
    block.mine();
    blockchain.add_block(block).unwrap();
    
    // Create a branch block
    let branch_block = blockchain.create_branch_block(
        "First block in branch".to_string(),
        "Branch author".to_string(),
        "Fantasy".to_string(),
        "A fantasy-themed branch".to_string(),
        0, // Parent is genesis block
    ).unwrap();
    
    // Mine and add the branch block
    let mut mined_branch_block = branch_block;
    mined_branch_block.mine();
    blockchain.add_block(mined_branch_block).unwrap();
    
    // Check that the branch was created
    assert_eq!(blockchain.blocks.len(), 3);
    assert_eq!(blockchain.branches.len(), 2); // "main" and the new branch
    
    // Get blocks from the branch
    let branch_id = "branch_fantasy";
    let branch_blocks = blockchain.get_blocks_by_branch(branch_id);
    
    assert_eq!(branch_blocks.len(), 1);
    assert_eq!(branch_blocks[0].data.content, "First block in branch");
    assert!(branch_blocks[0].data.branch_metadata.is_some());
} 