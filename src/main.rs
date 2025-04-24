use blockbard::{
    Blockchain, ChainStorage, Peer,
};
use std::env;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::signal;
use tokio::time::sleep;
use tracing::{error, info, Level};
use tracing_subscriber::FmtSubscriber;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize logging
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    // Parse command-line arguments
    let args: Vec<String> = env::args().collect();
    
    let (node_port, tracker_addr) = parse_args(&args)?;
    
    // Create data directory
    let data_dir = match env::var("NODE_DATA_DIR") {
        Ok(dir) => PathBuf::from(dir),
        Err(_) => PathBuf::from("blockbard_data"),
    };
    let storage = ChainStorage::new(&data_dir)?;
    
    // Initialize or load blockchain
    let blockchain = match storage.load_blockchain() {
        Ok(chain) => {
            info!("Loaded existing blockchain with {} blocks", chain.blocks.len());
            chain
        }
        Err(e) => {
            error!("Failed to load blockchain: {}", e);
            info!("Creating new blockchain");
            Blockchain::new()
        }
    };
    
    // Set up the node address
    let node_addr: SocketAddr = format!("0.0.0.0:{}", node_port).parse()?;
    
    // Set up the tracker address if provided
    let tracker = tracker_addr.map(|addr| addr.parse().unwrap());
    
    // Create and start the peer
    let peer = Peer::new(node_addr, blockchain, tracker);
    peer.start().await?;
    
    // Save the blockchain periodically
    let blockchain_for_saving = peer.blockchain.clone();
    let storage_for_saving = storage.clone();
    let cancel_flag = Arc::new(AtomicBool::new(false));
    let cancel_flag_clone = cancel_flag.clone();
    
    tokio::spawn(async move {
        while !cancel_flag_clone.load(Ordering::Relaxed) {
            sleep(Duration::from_secs(30)).await;
            
            let chain = {
                let guard = blockchain_for_saving.lock().await;
                guard.clone()
            };
            match storage_for_saving.save_blockchain(&chain) {
                Ok(_) => info!("Blockchain saved successfully"),
                Err(e) => error!("Failed to save blockchain: {}", e),
            }
        }
    });
    
    // Set up mining
    let mining_blockchain = peer.blockchain.clone();
    let peer_for_mining_clone = peer.clone();
    let cancel_mining = Arc::new(AtomicBool::new(false));
    let cancel_mining_clone = cancel_mining.clone();
    
    tokio::spawn(async move {
        while !cancel_mining_clone.load(Ordering::Relaxed) {
            // Create a new block
            let content = format!(
                "This is block #{} on BlockBard, mined by node {}",
                mining_blockchain.lock().await.blocks.len(),
                node_port
            );
            
            let author = format!("Node-{}", node_port);
            let branch_id = "main".to_string();
            
            let block = {
                let chain = mining_blockchain.lock().await;
                chain.create_block(content, author, branch_id)
            };
            
            // Mine the block
            info!("Mining block #{}...", block.index);
            let mined_block = blockbard::utils::mine_block(
                block,
                Arc::new(AtomicBool::new(false)),
                60,
            ).await;
            
            if let Some(mined_block) = mined_block {
                info!("Successfully mined block #{}", mined_block.index);
                
                // Add the block to our chain
                let mut chain = mining_blockchain.lock().await;
                match chain.add_block(mined_block.clone()) {
                    Ok(_) => {
                        info!("Block added to the chain");
                        
                        // Broadcast the block to peers
                        if let Err(e) = peer_for_mining_clone.broadcast_block(mined_block).await {
                            error!("Failed to broadcast block: {}", e);
                        }
                    }
                    Err(e) => {
                        error!("Failed to add block to chain: {}", e);
                    }
                }
            } else {
                info!("Mining interrupted or timed out");
            }
            
            sleep(Duration::from_secs(5)).await;
        }
    });
    
    // Wait for Ctrl+C
    let storage_for_shutdown = storage.clone();
    let blockchain_for_shutdown = peer.blockchain.clone();

    match signal::ctrl_c().await {
        Ok(()) => {
            info!("Shutdown signal received, shutting down...");
            cancel_flag.store(true, Ordering::Relaxed);
            cancel_mining.store(true, Ordering::Relaxed);
            
            // Save the blockchain one last time
            let chain = {
                let guard = blockchain_for_shutdown.lock().await;
                guard.clone()
            };
            if let Err(e) = storage_for_shutdown.save_blockchain(&chain) {
                error!("Failed to save blockchain during shutdown: {}", e);
            }
            
            sleep(Duration::from_secs(1)).await;
        }
        Err(e) => error!("Failed to listen for shutdown signal: {}", e),
    }
    
    Ok(())
}

fn parse_args(args: &[String]) -> Result<(u16, Option<String>), String> {
    if args.len() < 2 {
        return Err("Usage: blockbard <port> [tracker_addr]".to_string());
    }
    
    let port = args[1].parse::<u16>().map_err(|e| format!("Invalid port: {}", e))?;
    
    let tracker = if args.len() > 2 {
        Some(args[2].clone())
    } else {
        None
    };
    
    Ok((port, tracker))
}

#[cfg(test)]
mod tests {
    use blockbard::Blockchain;
    
    #[test]
    fn test_blockchain_creation() {
        let blockchain = Blockchain::new();
        assert_eq!(blockchain.blocks.len(), 1);
        assert_eq!(blockchain.blocks[0].index, 0);
        assert_eq!(blockchain.current_difficulty, 1);
    }
} 