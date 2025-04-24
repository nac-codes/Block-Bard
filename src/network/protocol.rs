use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MessageType {
    NewBlock,
    GetBlocks,
    Blocks,
    NewPeer,
    GetPeers,
    Peers,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub message_type: MessageType,
    pub data: String,
} 