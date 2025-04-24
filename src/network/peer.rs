use crate::blockchain::{Block, Blockchain, BlockchainError};
use crate::network::protocol::{Message, MessageType};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use thiserror::Error;
use tokio::net::TcpStream;
use tokio::sync::mpsc;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use std::net::SocketAddr;
use tokio::sync::Mutex;
use std::sync::Arc;
use tracing::{debug, error, info, warn};
use std::collections::HashMap;

#[derive(Debug, Error)]
pub enum NetworkError {
    #[error("Failed to connect to peer: {0}")]
    ConnectionError(#[from] std::io::Error),
    
    #[error("Failed to serialize message: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("Failed to parse address: {0}")]
    AddressParseError(#[from] std::net::AddrParseError),
    
    #[error("Message too large")]
    MessageTooLarge,
    
    #[error("Peer already exists: {0}")]
    PeerAlreadyExists(String),
    
    #[error("Peer not found: {0}")]
    PeerNotFound(String),
    
    #[error("Failed to broadcast message")]
    BroadcastError,
}

#[derive(Debug, Clone, Serialize, Deserialize, Hash, Eq, PartialEq)]
pub struct PeerInfo {
    pub address: String,
    pub is_tracker: bool,
}

#[derive(Clone)]
pub struct Peer {
    pub node_address: SocketAddr,
    pub blockchain: Arc<Mutex<Blockchain>>,
    pub known_peers: Arc<Mutex<HashSet<PeerInfo>>>,
    pub tracker_address: Option<SocketAddr>,
}

impl Peer {
    pub fn new(
        node_address: SocketAddr,
        blockchain: Blockchain,
        tracker_address: Option<SocketAddr>,
    ) -> Self {
        Peer {
            node_address,
            blockchain: Arc::new(Mutex::new(blockchain)),
            known_peers: Arc::new(Mutex::new(HashSet::new())),
            tracker_address,
        }
    }
    
    pub async fn start(&self) -> Result<(), NetworkError> {
        // Start the server to listen for incoming connections
        self.start_server().await?;
        
        // If we have a tracker, connect to it first
        if let Some(tracker) = self.tracker_address {
            info!("Connecting to tracker: {}", tracker);
            
            let tracker_info = PeerInfo {
                address: tracker.to_string(),
                is_tracker: true,
            };
            
            self.connect_to_peer(tracker_info).await?;
            
            // Request peer list from tracker
            self.request_peers().await?;
            
            // Give some time for connections to establish and synchronize
            info!("Waiting for initial blockchain synchronization...");
            tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
        }
        
        Ok(())
    }
    
    async fn start_server(&self) -> Result<(), NetworkError> {
        let server = tokio::net::TcpListener::bind(self.node_address).await?;
        info!("Node listening on {}", self.node_address);
        
        let blockchain = self.blockchain.clone();
        let known_peers = self.known_peers.clone();
        
        tokio::spawn(async move {
            loop {
                match server.accept().await {
                    Ok((socket, addr)) => {
                        info!("New connection from: {}", addr);
                        let peer_blockchain = blockchain.clone();
                        let peer_known_peers = known_peers.clone();
                        
                        tokio::spawn(async move {
                            if let Err(e) = handle_connection(socket, peer_blockchain, peer_known_peers).await {
                                error!("Error handling connection: {}", e);
                            }
                        });
                    }
                    Err(e) => {
                        error!("Error accepting connection: {}", e);
                    }
                }
            }
        });
        
        Ok(())
    }
    
    pub async fn connect_to_peer(&self, peer: PeerInfo) -> Result<(), NetworkError> {
        let addr = peer.address.parse::<SocketAddr>()?;
        
        if addr == self.node_address {
            debug!("Skipping connection to self");
            return Ok(());
        }
        
        {
            let mut peers = self.known_peers.lock().await;
            if peers.contains(&peer) {
                debug!("Already connected to peer {}", peer.address);
                return Ok(());
            }
            peers.insert(peer.clone());
        }
        
        let mut socket = TcpStream::connect(addr).await?;
        info!("Connected to peer: {}", addr);
        
        // Send our node info
        let host_ip = if self.node_address.ip().is_unspecified() {
            // When running in production with 0.0.0.0, we need to provide the actual IP
            // This is a placeholder for the actual external IP detection logic
            if let Some(env_ip) = std::env::var("BLOCKBARD_PUBLIC_IP").ok() {
                env_ip
            } else {
                // Default to the IP of the peer we're connecting to if external IP is unknown
                // This works for LANs but not across the internet
                format!("{}", addr.ip())
            }
        } else {
            format!("{}", self.node_address.ip())
        };

        let self_info = PeerInfo {
            address: format!("{}:{}", host_ip, self.node_address.port()),
            is_tracker: false,
        };
        
        let message = Message {
            message_type: MessageType::NewPeer,
            data: serde_json::to_string(&self_info)?,
        };
        
        send_message(&mut socket, &message).await?;
        
        // Request blockchain from the peer to ensure synchronization
        self.request_blocks(addr).await?;
        
        // Start listening for messages from this peer
        let blockchain = self.blockchain.clone();
        let known_peers = self.known_peers.clone();
        
        tokio::spawn(async move {
            if let Err(e) = handle_connection(socket, blockchain, known_peers).await {
                error!("Error handling connection: {}", e);
            }
        });
        
        Ok(())
    }
    
    pub async fn broadcast_block(&self, block: Block) -> Result<(), NetworkError> {
        let serialized = serde_json::to_string(&block)?;
        
        let message = Message {
            message_type: MessageType::NewBlock,
            data: serialized,
        };
        
        let peers = self.known_peers.lock().await.clone();
        
        for peer in peers.iter() {
            let addr = peer.address.parse::<SocketAddr>()?;
            
            if addr == self.node_address {
                continue;
            }
            
            match TcpStream::connect(addr).await {
                Ok(mut socket) => {
                    if let Err(e) = send_message(&mut socket, &message).await {
                        warn!("Failed to send block to {}: {}", addr, e);
                    } else {
                        // Add a small delay to ensure the message is sent before closing
                        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                        debug!("Successfully sent block #{} to {}", block.index, addr);
                    }
                }
                Err(e) => {
                    warn!("Failed to connect to {}: {}", addr, e);
                }
            }
        }
        
        Ok(())
    }
    
    async fn request_peers(&self) -> Result<(), NetworkError> {
        if let Some(tracker) = self.tracker_address {
            let mut socket = TcpStream::connect(tracker).await?;
            
            let message = Message {
                message_type: MessageType::GetPeers,
                data: String::new(),
            };
            
            send_message(&mut socket, &message).await?;
            
            Ok(())
        } else {
            Ok(())
        }
    }
    
    async fn request_blocks(&self, peer_addr: SocketAddr) -> Result<(), NetworkError> {
        info!("Requesting blockchain from peer: {}", peer_addr);
        
        // Create a new connection to request blocks
        let mut socket = TcpStream::connect(peer_addr).await?;
        
        let message = Message {
            message_type: MessageType::GetBlocks,
            data: String::new(),
        };
        
        // Send request for blocks
        send_message(&mut socket, &message).await?;
        
        // Create a dedicated handler for this connection
        let blockchain = self.blockchain.clone();
        let known_peers = self.known_peers.clone();
        
        tokio::spawn(async move {
            if let Err(e) = handle_connection(socket, blockchain, known_peers).await {
                if let NetworkError::ConnectionError(err) = &e {
                    if err.kind() == std::io::ErrorKind::UnexpectedEof {
                        debug!("Connection closed after requesting blocks");
                        return;
                    }
                }
                error!("Error handling connection while requesting blocks: {}", e);
            }
        });
        
        Ok(())
    }
}

async fn handle_connection(
    mut socket: TcpStream,
    blockchain: Arc<Mutex<Blockchain>>,
    known_peers: Arc<Mutex<HashSet<PeerInfo>>>,
) -> Result<(), NetworkError> {
    let peer_addr = socket.peer_addr()?;
    info!("Handling connection from {}", peer_addr);
    
    let (reader, mut writer) = socket.split();
    let mut reader = tokio::io::BufReader::new(reader);
    
    loop {
        // Handle EOF (peer disconnected) gracefully
        let message = match receive_message(&mut reader).await {
            Ok(msg) => msg,
            Err(NetworkError::ConnectionError(e)) if e.kind() == std::io::ErrorKind::UnexpectedEof => {
                info!("Peer {} disconnected", peer_addr);
                return Ok(());
            },
            Err(e) => return Err(e),
        };
        
        match message.message_type {
            MessageType::NewBlock => {
                let block: Block = serde_json::from_str(&message.data)?;
                info!("Received new block: #{} from {}", block.index, peer_addr);
                
                let mut chain = blockchain.lock().await;
                match chain.add_block(block.clone()) {
                    Ok(_) => {
                        info!("Block #{} added to chain", block.index);
                    }
                    Err(e) => {
                        warn!("Failed to add block #{}: {}", block.index, e);
                    }
                }
            }
            MessageType::GetBlocks => {
                info!("Received request for blocks from {}", peer_addr);
                
                let chain = blockchain.lock().await;
                let serialized = serde_json::to_string(&chain.blocks)?;
                
                let response = Message {
                    message_type: MessageType::Blocks,
                    data: serialized,
                };
                
                writer.write_all(&serialize_message(&response)?).await?;
                writer.flush().await?;
            }
            MessageType::Blocks => {
                info!("Received blocks from {}", peer_addr);
                
                let blocks: Vec<Block> = serde_json::from_str(&message.data)?;
                
                // Only process if we received blocks
                if blocks.is_empty() {
                    debug!("Received empty blockchain, ignoring");
                    return Ok(());
                }
                
                let mut chain = blockchain.lock().await;
                
                // Only consider chains longer than our own
                if blocks.len() > chain.blocks.len() {
                    info!("Received chain with {} blocks (our chain has {})", blocks.len(), chain.blocks.len());
                    
                    // Verify the received chain
                    let mut is_valid = true;
                    
                    // Verify chain integrity
                    for i in 1..blocks.len() {
                        let current = &blocks[i];
                        let previous = &blocks[i - 1];
                        
                        if current.previous_hash != previous.hash || !current.is_valid() {
                            is_valid = false;
                            warn!("Invalid block at index {} in received chain", i);
                            break;
                        }
                    }
                    
                    if is_valid {
                        info!("Replacing local chain with received chain (length: {})", blocks.len());
                        *chain = Blockchain {
                            blocks,
                            branches: HashMap::new(), // Will rebuild branches
                            current_difficulty: chain.current_difficulty,
                            difficulty_adjustment_interval: chain.difficulty_adjustment_interval,
                            target_block_time_seconds: chain.target_block_time_seconds,
                        };
                        
                        // Update branches
                        chain.rebuild_branches();
                        
                        info!("Blockchain updated with {} blocks from peer", chain.blocks.len());
                    } else {
                        warn!("Received invalid blockchain from {}", peer_addr);
                    }
                } else {
                    debug!("Received chain is not longer than local chain, ignoring");
                }
            }
            MessageType::NewPeer => {
                let peer_info: PeerInfo = serde_json::from_str(&message.data)?;
                info!("New peer joined: {}", peer_info.address);
                
                let mut peers = known_peers.lock().await;
                peers.insert(peer_info);
            }
            MessageType::GetPeers => {
                info!("Received request for peers from {}", peer_addr);
                
                let peers = known_peers.lock().await;
                let response = Message {
                    message_type: MessageType::Peers,
                    data: serde_json::to_string(&*peers)?,
                };
                
                writer.write_all(&serialize_message(&response)?).await?;
                writer.flush().await?;
            }
            MessageType::Peers => {
                let peer_list: HashSet<PeerInfo> = serde_json::from_str(&message.data)?;
                info!("Received {} peers from {}", peer_list.len(), peer_addr);
                
                let mut peers = known_peers.lock().await;
                for peer in peer_list {
                    peers.insert(peer);
                }
            }
        }
    }
}

async fn send_message(socket: &mut TcpStream, message: &Message) -> Result<(), NetworkError> {
    let serialized = serialize_message(message)?;
    socket.write_all(&serialized).await?;
    socket.flush().await?;
    
    Ok(())
}

async fn receive_message(reader: &mut tokio::io::BufReader<tokio::net::tcp::ReadHalf<'_>>) -> Result<Message, NetworkError> {
    let mut len_buf = [0u8; 4];
    match reader.read_exact(&mut len_buf).await {
        Ok(_) => {},
        Err(e) => return Err(NetworkError::ConnectionError(e)),
    }
    
    let len = u32::from_be_bytes(len_buf) as usize;
    if len > 10_000_000 { // 10MB limit
        return Err(NetworkError::MessageTooLarge);
    }
    
    let mut buf = vec![0u8; len];
    match reader.read_exact(&mut buf).await {
        Ok(_) => {},
        Err(e) => return Err(NetworkError::ConnectionError(e)),
    }
    
    let message: Message = serde_json::from_slice(&buf)?;
    
    Ok(message)
}

fn serialize_message(message: &Message) -> Result<Vec<u8>, NetworkError> {
    let serialized = serde_json::to_vec(message)?;
    let len = (serialized.len() as u32).to_be_bytes();
    
    let mut result = Vec::with_capacity(4 + serialized.len());
    result.extend_from_slice(&len);
    result.extend_from_slice(&serialized);
    
    Ok(result)
} 