use crate::blockchain::Block;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::time::sleep;

pub async fn mine_block(
    mut block: Block,
    cancel_flag: Arc<AtomicBool>,
    timeout_seconds: u64,
) -> Option<Block> {
    let start_time = std::time::Instant::now();
    let timeout = Duration::from_secs(timeout_seconds);
    
    let target = "0".repeat(block.difficulty as usize);
    
    while !block.hash.starts_with(&target) {
        // Check if mining should be cancelled
        if cancel_flag.load(Ordering::Relaxed) {
            return None;
        }
        
        // Check if we've exceeded the timeout
        if start_time.elapsed() > timeout {
            return None;
        }
        
        block.nonce += 1;
        block.hash = block.calculate_hash();
        
        // Yield to allow other tasks to run
        if block.nonce % 1000 == 0 {
            sleep(Duration::from_millis(1)).await;
        }
    }
    
    println!("Block mined! Nonce: {}, Hash: {}", block.nonce, block.hash);
    Some(block)
} 