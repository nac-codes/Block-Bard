#!/usr/bin/env python3
import socket
import sys
import threading
import json
import time

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

        # === FIXED GETCHAIN ===
        if raw == "GETCHAIN":
            payload = json.dumps([blk.to_dict() for blk in bc.chain])
            conn.sendall(f"CHAIN {payload}\n".encode())
            conn.close()
            continue

        # BLOCK messages
        if raw.startswith("BLOCK "):
            blk = json.loads(raw[len("BLOCK "):])
            latest = bc.get_latest_block()
            if blk["index"] == latest.index + 1 and blk["previous_hash"] == latest.hash:
                bc.chain.append(Block(**blk))
                print(f"[Listener] Appended block #{blk['index']}")
            else:
                # -- same sync logic as before --
                print(f"[Listener] Out-of-order block {blk['index']}; syncing…")
                peers = fetch_peers(tracker_host, tracker_port, self_id)
                best = bc.chain
                for p in peers:
                    host, ps = p.split(':')
                    try:
                        with socket.socket() as s3:
                            s3.connect((host, int(ps)))
                            s3.sendall(b"GETCHAIN\n")
                            data = s3.recv(65536).decode().strip()
                        if data.startswith("CHAIN "):
                            cl = json.loads(data[len("CHAIN "):])
                            if len(cl) > len(best):
                                best = [Block(**d) for d in cl]
                    except:
                        continue
                if len(best) > len(bc.chain):
                    bc.chain = best
                    print(f"[Listener] Synced to length {len(bc.chain)}")
            conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: run_node.py <tracker_host> <tracker_port> <my_port>")
        sys.exit(1)

    tracker_host, tracker_port, my_port = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    self_id = f"{socket.gethostname()}:{my_port}"

    # 1) Register
    with socket.socket() as s:
        s.connect((tracker_host, tracker_port))
        s.sendall(f"JOIN {self_id}\n".encode())

    # 2) Start blockchain and listener
    bc = Blockchain(difficulty=2)
    threading.Thread(
        target=listen_for_blocks,
        args=(my_port, bc, tracker_host, tracker_port, self_id),
        daemon=True
    ).start()
    time.sleep(1)

    # 3) Sync at startup (same as before)
    peers = fetch_peers(tracker_host, tracker_port, self_id)
    best = bc.chain
    for p in peers:
        host, ps = p.split(':')
        try:
            with socket.socket() as s2:
                s2.connect((host, int(ps)))
                s2.sendall(b"GETCHAIN\n")
                data = s2.recv(65536).decode().strip()
            if data.startswith("CHAIN "):
                cl = json.loads(data[len("CHAIN "):])
                if len(cl) > len(best):
                    best = [Block(**d) for d in cl]
        except:
            continue
    if len(best) > len(bc.chain):
        bc.chain = best
        print(f"[Startup] Synced to length {len(bc.chain)}")

    # 4) Configure your AI agent
    prefs = AgentPreferences(
        writing_style="poetic",
        themes=["adventure", "friendship"],
        characters=["Alice", "The Dragon"]
    )
    st = StoryTeller(prefs)

    # 5) Launch the mining agent
    miner = MiningAgent(
        bc=bc,
        storyteller=st,
        broadcast_fn=lambda blk: broadcast_fn(tracker_host, tracker_port, self_id, blk),
        mine_interval=5.0
    )
    miner.start()

    # 6) Keep the main thread alive
    miner.join()
