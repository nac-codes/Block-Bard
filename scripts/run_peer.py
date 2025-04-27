#!/usr/bin/env python3
import socket
import sys
import threading
import json
import time

from blockchain.blockchain import Blockchain
from blockchain.block import Block

def listen_for_messages(port, bc):
    """Handle incoming GETCHAIN and BLOCK requests."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(('', port))
    srv.listen()
    print(f"[Listener] Waiting for messages on port {port}…")
    while True:
        conn, addr = srv.accept()
        raw = conn.recv(8192).decode().strip()
        # 1) Reply to chain requests
        if raw == "GETCHAIN":
            chain_data = [blk.to_dict() for blk in bc.chain]
            resp = "CHAIN " + json.dumps(chain_data) + "\n"
            conn.sendall(resp.encode())
        # 2) Process incoming blocks
        elif raw.startswith("BLOCK "):
            payload = raw[len("BLOCK "):]
            blk_dict = json.loads(payload)
            print(f"[Listener] Received block {blk_dict['index']}")
            added = bc.add_block_from_dict(blk_dict)
            if not added:
                print(f"[Listener] Rejected block {blk_dict['index']}")
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: run_peer.py <tracker_host> <tracker_port> <my_port>")
        sys.exit(1)

    tracker_host, tracker_port, my_port = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    peer_id = f"{socket.gethostname()}:{my_port}"

    # 1) Register with tracker
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((tracker_host, tracker_port))
        s.sendall(f"JOIN {peer_id}\n".encode())
        resp = s.recv(4096).decode().strip()
    peers = [p for p in resp.splitlines() if p != peer_id]
    print(f"[Bootstrap] Known peers: {peers}")

    # 2) Initialize blockchain & start listener
    bc = Blockchain(difficulty=2)
    threading.Thread(target=listen_for_messages, args=(my_port, bc), daemon=True).start()

    # 3) Sync chain if there is at least one peer
    if peers:
        first = peers[0]
        host, port = first.split(':')
        port = int(port)
        print(f"[Sync] Requesting chain from {first}…")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall("GETCHAIN\n".encode())
            data = s.recv(65536).decode().strip()
        if data.startswith("CHAIN "):
            chain_list = json.loads(data[len("CHAIN "):])
            # Rebuild local chain
            bc.chain = []
            for i, blk_dict in enumerate(chain_list):
                if i == 0:
                    # Genesis: bypass PoW check
                    bc.chain.append(Block(**blk_dict))
                else:
                    bc.add_block_from_dict(blk_dict)
            print(f"[Sync] Synced chain; length = {len(bc.chain)}")

    # 4) Give others time to start listening
    time.sleep(2)

    # 5) Mine a new block and broadcast it
    new_blk = bc.add_block(f"Data from {peer_id}")
    msg = "BLOCK " + json.dumps(new_blk.to_dict()) + "\n"
    for p in peers:
        host, port = p.split(':')
        port = int(port)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                s.sendall(msg.encode())
            print(f"[Broadcast] Sent block {new_blk.index} to {p}")
        except Exception as e:
            print(f"[Broadcast] Failed to {p}: {e}")

    # 6) Show your updated chain state
    print(f"[Chain] length = {len(bc.chain)}, latest index = {bc.get_latest_block().index}")

    # 7) Keep running to receive future blocks
    while True:
        time.sleep(1)
