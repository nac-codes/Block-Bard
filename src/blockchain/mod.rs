pub mod block;
pub mod blockchain;

#[cfg(test)]
mod tests;

pub use block::{Block, BlockData, BranchMetadata};
pub use blockchain::{Blockchain, BlockchainError}; 