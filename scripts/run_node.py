#!/usr/bin/env python3
import socket
import sys
import threading
import json
import time
import argparse
import logging
import os

from blockchain.blockchain import Blockchain
from blockchain.block import Block
from agent.preferences import AgentPreferences
from agent.storyteller import StoryTeller
from agent.mining_agent import MiningAgent

def fetch_peers(tracker_host, tracker_port, self_id):
    with socket.socket() as s:
        s.connect((tracker_host, tracker_port))
        s.sendall(b"GETPEERS\n")
        data = s.recv(4096).decode().splitlines()
    return [p for p in data if p != self_id]

def broadcast_fn(tracker_host, tracker_port, self_id, blk_dict):
    peers = fetch_peers(tracker_host, tracker_port, self_id)
    msg = "BLOCK " + json.dumps(blk_dict) + "\n"
    for p in peers:
        host, port_s = p.split(':')
        try:
            with socket.socket() as s:
                s.connect((host, int(port_s)))
                s.sendall(msg.encode())
            print(f"[Broadcast] → {p}")
        except Exception as e:
            print(f"[Broadcast] ✗ {p}: {e}")

def listen_for_blocks(port, bc, tracker_host, tracker_port, self_id):
    srv = socket.socket()
    srv.bind(('', port))
    srv.listen()
    print(f"[Listener] Listening on port {port}…")
    while True:
        conn, _ = srv.accept()
        raw = conn.recv(8192).decode().strip()

        # Reply on same connection to GETCHAIN
        if raw == "GETCHAIN":
            payload = json.dumps([blk.to_dict() for blk in bc.chain])
            conn.sendall(f"CHAIN {payload}\n".encode())
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
                            data = s3.recv(65536).decode().strip()
                        if data.startswith("CHAIN "):
                            chain_data = json.loads(data[len("CHAIN "):])
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
            conn.close()

def main():
    parser = argparse.ArgumentParser(description="Run a Block-Bard node")
    parser.add_argument("--tracker-host", default="127.0.0.1", help="Tracker host (default: 127.0.0.1)")
    parser.add_argument("--tracker-port", type=int, default=8000, help="Tracker port (default: 8000)")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--schema", default="bible", help="Story schema to use (bible, novel, or path to JSON file)")
    parser.add_argument("--writing-style", default="poetic", help="Writing style (poetic, technical, casual, etc.)")
    parser.add_argument("--themes", default="adventure,friendship", help="Themes (comma-separated)")
    parser.add_argument("--characters", default="Alice,The Dragon", help="Characters (comma-separated)")
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

    # 4) Configure your AI agent
    prefs = AgentPreferences(
        writing_style=args.writing_style,
        themes=args.themes.split(','),
        characters=args.characters.split(',')
    )
    st = StoryTeller(
        prefs, 
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
