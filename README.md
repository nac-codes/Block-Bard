# BlockBard

BlockBard is a blockchain-based collaborative storytelling platform where a story grows organically through mining-based contributions, with multiple narrative branches forming a rich storytelling tree.

## Features

- Blockchain-based immutable story history
- Mining-based contribution system
- Branching narrative system for alternative storylines
- P2P network architecture for decentralization
- Story segmentation with blocks containing exactly one story contribution

## Getting Started

### Prerequisites

- Rust (install via [rustup](https://rustup.rs/))

### Installation

1. Clone the repository
2. Build the project with Cargo

```bash
cargo build --release
```

### Running a Node

To run a node, specify a port number:

```bash
./target/release/blockbard 8000
```

To connect to an existing node (acting as a tracker), specify the tracker address:

```bash
./target/release/blockbard 8001 127.0.0.1:8000
```

## Project Structure

- `blockchain/`: Core blockchain data structures and logic
- `network/`: P2P networking implementation
- `crypto/`: Cryptographic utilities
- `storage/`: Blockchain persistence
- `utils/`: Utility functions

## Testing

Run the tests with:

```bash
cargo test
```

## Usage

1. Start a tracker node (the first node in the network)
2. Start additional nodes that connect to the tracker
3. Nodes will automatically mine blocks and share them across the network
4. Each block contains a contribution to the story

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by collaborative storytelling platforms
- Built with Rust for performance and safety

# Running Nodes on Different Machines

To run BlockBard nodes on different machines across a network:

1. **On the first machine (tracker node):**
   ```
   # Start the tracker node (binding to all interfaces)
   ./blockbard 8000
   ```

2. **Find the IP address of the tracker node:**
   ```
   # On Linux/macOS
   ip addr show
   
   # On Windows
   ipconfig
   ```

3. **On other machines, connect to the tracker:**
   ```
   # Replace TRACKER_IP with the actual IP address of the tracker node
   # Set the BLOCKBARD_PUBLIC_IP to the machine's own external IP
   BLOCKBARD_PUBLIC_IP=YOUR_MACHINE_IP ./blockbard 8000 TRACKER_IP:8000
   ```

4. **Network Configuration:**
   - Ensure ports are open in firewalls (default: 8000)
   - For internet-facing nodes, configure port forwarding in your router
   - For cloud VMs, set appropriate security group rules

## Handling NAT and Firewalls

If your nodes are behind NAT or firewalls:

1. Ensure the tracker node is accessible (port forwarding/public IP)
2. Set the `BLOCKBARD_PUBLIC_IP` environment variable to your public IP
3. Configure port forwarding on your router to direct traffic to your node

For cloud environments, you may need to:
- Allow TCP traffic on your chosen port in security groups/firewall rules
- Use the public IP of the instance for `BLOCKBARD_PUBLIC_IP` 