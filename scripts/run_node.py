#!/usr/bin/env python3
import socket
import sys
import threading
import json
import time
import argparse
import logging
import atexit

from blockchain.blockchain import Blockchain
from blockchain.block import Block
from agent.storyteller import StoryTeller
from agent.mining_agent import MiningAgent

def fetch_peers(tracker_host, tracker_port, self_id):
    """
    fetch list of peers from tracker server
    blocking until the full peer list is received

    it sends a GETPEERS command to the tracker, decodes the response lines,
    and filters out this node's own identifier

    arguments:
    tracker_host -- the tracker's hostname or IP address
    tracker_port -- the tracker's port number
    self_id      -- this peer's identifier to exclude from the returned list

    return:
    list of peer identifiers (strings) excluding self_id
    """
    with socket.socket() as s:
        s.connect((tracker_host, tracker_port))
        s.sendall(b"GETPEERS\n")
        data = s.recv(4096).decode().splitlines()
    return [p for p in data if p != self_id]

def broadcast_fn(tracker_host, tracker_port, self_id, blk_dict):
    """
    broadcast block data to all peers
    blocking until each send attempt completes

    it fetches the peer list via fetch_peers, serializes blk_dict as a JSON
    payload prefixed with "BLOCK ", then iterates through each peer,
    sending the message and logging success or failure

    arguments:
    tracker_host -- the tracker's hostname or IP address
    tracker_port -- the tracker's port number
    self_id      -- this peer's identifier to exclude from broadcast
    blk_dict     -- dictionary containing the block data to send

    return:
    None
    """
    peers = fetch_peers(tracker_host, tracker_port, self_id)
    msg = "BLOCK " + json.dumps(blk_dict) + "\n"
    for p in peers:
        host, port_s = p.split(':')
        try:
            with socket.socket() as s:
                s.connect((host, int(port_s)))
                s.sendall(msg.encode())
            print(f"[Broadcast] -> {p}")
        except Exception as e:
            print(f"[Broadcast] x {p}: {e}")

def listen_for_blocks(port, bc, tracker_host, tracker_port, self_id):
    """
    listen for incoming block and chain requests on given port
    runs indefinitely, handling GETCHAIN and BLOCK commands

    it binds to the specified port, accepts connections in a loop,
    responds to GETCHAIN by sending the full chain, processes BLOCK
    messages—appending valid next blocks, rejecting duplicates,
    and syncing out-of-order blocks by fetching the longest valid chain
    from peers

    arguments:
    port           -- TCP port to listen on for peer connections
    bc             -- blockchain instance with attributes chain, get_latest_block(), add_block_from_dict(), is_valid_chain()
    tracker_host   -- the tracker's hostname or IP address for peer discovery
    tracker_port   -- the tracker's port number for peer discovery
    self_id        -- this node's identifier to exclude from peer list

    return:
    None
    """
    srv = socket.socket()
    srv.bind(('', port))
    srv.listen()
    print(f"[Listener] Listening on port {port}…")
    while True:
        conn, addr = srv.accept()
        try:
            raw = conn.recv(8192).decode().strip()

            # Reply on same connection to GETCHAIN
            if raw == "GETCHAIN":
                # For large blockchains, serialize and send in smaller chunks
                # to avoid timeouts and memory issues
                try:
                    # First, prepare the data
                    chain_data = [blk.to_dict() for blk in bc.chain]
                    json_data = json.dumps(chain_data)
                    
                    # Log the size for debugging
                    data_size = len(json_data.encode())
                    print(f"[Listener] Sending chain with {len(chain_data)} blocks ({data_size/1024:.1f}KB) to {addr[0]}:{addr[1]}")
                    
                    # Send in a single response for small chains (under 1MB)
                    if data_size < 1024 * 1024:  # 1MB
                        conn.sendall(f"CHAIN {json_data}\n".encode())
                    else:
                        # For larger chains, split the JSON array into chunks
                        # This is a workaround for large chains - sending prefix first
                        conn.sendall(b"CHAIN ")
                        
                        # Send data in small chunks
                        chunk_size = 65536  # 64KB chunks
                        bytes_data = json_data.encode()
                        for i in range(0, len(bytes_data), chunk_size):
                            chunk = bytes_data[i:i+chunk_size]
                            conn.sendall(chunk)
                            
                            # Add small delay to prevent buffer overflows
                            if i % (1024 * 1024) == 0 and i > 0:  # Every 1MB
                                print(f"[Listener] Sent {i/1024:.1f}KB so far...")
                                time.sleep(0.1)  # Small delay every MB
                                
                        # Make sure to terminate the response
                        conn.sendall(b"\n")
                    
                    print(f"[Listener] Finished sending chain data")
                except Exception as e:
                    print(f"[Listener] Error sending chain: {e}")
                    # Send a simple response in case of error
                    try:
                        conn.sendall(b"CHAIN []\n")
                    except:
                        pass
                conn.close()
                continue

            # Incoming block
            if raw.startswith("BLOCK "):
                blk = json.loads(raw[len("BLOCK "):])
                latest = bc.get_latest_block()
                
                # Check for position hash uniqueness
                if "position_hash" in blk and any(b.position_hash == blk["position_hash"] for b in bc.chain):
                    print(f"[Listener] Rejecting block with duplicate position hash")
                    conn.close()
                    continue
                    
                if blk["index"] == latest.index + 1 and blk["previous_hash"] == latest.hash:
                    # Try to add the block
                    if bc.add_block_from_dict(blk):
                        print(f"[Listener] Appended block #{blk['index']}")
                else:
                    # Out‐of‐order → sync longest chain
                    print(f"[Listener] Out-of-order block {blk['index']}; syncing…")
                    peers = fetch_peers(tracker_host, tracker_port, self_id)
                    best_chain = None
                    best_length = len(bc.chain)
                    
                    for p in peers:
                        host, ps = p.split(':')
                        try:
                            with socket.socket() as s3:
                                s3.connect((host, int(ps)))
                                s3.sendall(b"GETCHAIN\n")
                                
                                # Read with better chunking
                                chunks = []
                                while True:
                                    data = s3.recv(65536)
                                    if not data:
                                        break
                                    chunks.append(data)
                                
                                full_data = b''.join(chunks)
                                if full_data.startswith(b"CHAIN "):
                                    chain_json = full_data[6:].decode().strip()
                                    chain_data = json.loads(chain_json)
                                    candidate = [Block(**d) for d in chain_data]
                                    
                                    # Check if this is a valid chain with no duplicate position hashes
                                    if len(candidate) > best_length and bc.is_valid_chain(candidate):
                                        best_chain = candidate
                                        best_length = len(candidate)
                        except Exception as e:
                            print(f"[Listener] Error syncing with {p}: {e}")
                            continue
                            
                    if best_chain and len(best_chain) > len(bc.chain):
                        bc.chain = best_chain
                        print(f"[Listener] Synced to length {len(bc.chain)}")
        except Exception as e:
            print(f"[Listener] Error handling connection: {e}")
        finally:
            try:
                conn.close()
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description="Run a Block-Bard node")
    parser.add_argument("--tracker-host", default="127.0.0.1", help="Tracker host (default: 127.0.0.1)")
    parser.add_argument("--tracker-port", type=int, default=8000, help="Tracker port (default: 8000)")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--schema", default="bible", help="Schema to use (bible or path to JSON file)")
    parser.add_argument("--mine-interval", type=float, default=5.0, help="Mining interval in seconds (default: 5.0)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       help="Set the logging level")
    parser.add_argument("--api-key", help="OpenAI API key (defaults to OPENAI_API_KEY environment variable)")
    parser.add_argument("--system-prompt", 
                       help="System prompt for AI personality (filepath or direct text)")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"node_{args.port}.log")
        ]
    )
    logger = logging.getLogger("node")
    
    tracker_host, tracker_port, my_port = args.tracker_host, args.tracker_port, args.port
    self_id = f"{socket.gethostname()}:{my_port}"
    logger.info(f"Starting node with ID: {self_id}")

    # 1) Register with tracker
    with socket.socket() as s:
        s.connect((tracker_host, tracker_port))
        s.sendall(f"JOIN {self_id}\n".encode())
    logger.info(f"Registered with tracker at {tracker_host}:{tracker_port}")

    # 1b) Unregister on clean exit
    def unregister():
        with socket.socket() as s:
            s.connect((tracker_host, tracker_port))
            s.sendall(f"LEAVE {self_id}\n".encode())
    atexit.register(unregister)

    # 2) Start blockchain and listener
    bc = Blockchain(difficulty=2)
    threading.Thread(
        target=listen_for_blocks,
        args=(int(my_port), bc, tracker_host, tracker_port, self_id),
        daemon=True
    ).start()
    time.sleep(1)
    logger.info(f"Listener started on port {my_port}")

    # 3) Initial sync to longest chain
    peers = fetch_peers(tracker_host, tracker_port, self_id)
    best_chain = None
    best_length = len(bc.chain)

    for p in peers:
        host, ps = p.split(':')
        try:
            with socket.socket() as s2:
                s2.connect((host, int(ps)))
                s2.sendall(b"GETCHAIN\n")
                data = s2.recv(65536).decode().strip()
            if data.startswith("CHAIN "):
                chain_data = json.loads(data[len("CHAIN "):])
                candidate = [Block(**d) for d in chain_data]
                
                # Check if this is a valid chain with no duplicate position hashes
                if len(candidate) > best_length and bc.is_valid_chain(candidate):
                    best_chain = candidate
                    best_length = len(candidate)
        except Exception as e:
            logger.warning(f"Error syncing with {p}: {e}")
            continue

    if best_chain and len(best_chain) > len(bc.chain):
        bc.chain = best_chain
        logger.info(f"Synced to chain length {len(bc.chain)}")
    else:
        logger.info("No longer chain found, using genesis block")

    # 4) Configure AI agent
    st = StoryTeller(
        schema_name_or_path=args.schema, 
        api_key=args.api_key,
        system_prompt=args.system_prompt
    )
    logger.info(f"Configured StoryTeller with schema: {args.schema}")
    if args.system_prompt:
        logger.info(f"Using custom system prompt: {args.system_prompt}")

    # 5) Launch the mining agent
    miner = MiningAgent(
        bc=bc,
        storyteller=st,
        broadcast_fn=lambda blk: broadcast_fn(tracker_host, tracker_port, self_id, blk),
        agent_name=self_id,
        mine_interval=args.mine_interval,
        story_schema=args.schema
    )
    logger.info(f"Starting mining agent with interval {args.mine_interval}s")
    miner.start()

    # 6) Keep the main thread alive
    try:
        miner.join()
    except KeyboardInterrupt:
        logger.info("Shutting down node")
        sys.exit(0)

if __name__ == "__main__":
    main()
