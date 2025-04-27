#!/usr/bin/env python3
import socket
import sys
import threading
import json
import time

from blockchain.blockchain import Blockchain
from blockchain.block import Block

def fetch_peers(tracker_host, tracker_port, self_id):
    """Ask tracker for the current peer list (excluding self)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((tracker_host, tracker_port))
        s.sendall("GETPEERS\n".encode())
        data = s.recv(4096).decode().strip()
    return [p for p in data.splitlines() if p != self_id]

def fetch_chain_from_peer(host, port):
    """Get entire chain from one peer, as list of block-dicts."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall("GETCHAIN\n".encode())
            resp = s.recv(65536).decode().strip()
        if resp.startswith("CHAIN "):
            return json.loads(resp[len("CHAIN "):])
    except:
        pass
    return None

def listen_for_messages(port, bc, tracker_host, tracker_port, self_id):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(('', port))
    srv.listen()
    print(f"[Listener] Listening on port {port}…")

    while True:
        conn, _ = srv.accept()
        raw = conn.recv(8192).decode().strip()

        # Respond to GETCHAIN
        if raw == "GETCHAIN":
            payload = json.dumps([blk.to_dict() for blk in bc.chain])
            conn.sendall(f"CHAIN {payload}\n".encode())
            conn.close()
            continue

        # Incoming block
        if raw.startswith("BLOCK "):
            blk = json.loads(raw[len("BLOCK "):])
            idx = blk["index"]
            latest = bc.get_latest_block()

            # 1) Proper next block?
            if idx == latest.index + 1 and blk["previous_hash"] == latest.hash:
                bc.chain.append(Block(**blk))
                print(f"[Listener] Appended block {idx}")
                conn.close()
                continue

            # 2) Otherwise, full sync
            print(f"[Listener] Out-of-order block {idx}; syncing longest chain…")
            peers = fetch_peers(tracker_host, tracker_port, self_id)

            best_chain = bc.chain
            for p in peers:
                h, ps = p.split(':')
                cl = fetch_chain_from_peer(h, int(ps))
                if cl and len(cl) > len(best_chain):
                    best_chain = [Block(**d) for d in cl]

            if len(best_chain) > len(bc.chain):
                bc.chain = best_chain
                print(f"[Listener] Synced to chain length {len(bc.chain)}")
            else:
                print("[Listener] No longer chain found; keeping current")

        conn.close()

def broadcast_block(blk_dict, tracker_host, tracker_port, self_id):
    """Fetch latest peers and send BLOCK to each (excluding self)."""
    peers = fetch_peers(tracker_host, tracker_port, self_id)
    msg = "BLOCK " + json.dumps(blk_dict) + "\n"
    for p in peers:
        host, ps = p.split(':')
        port = int(ps)
        if p == self_id:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                s.sendall(msg.encode())
            print(f"[Broadcast] → {p}")
        except Exception as e:
            print(f"[Broadcast] ✗ {p}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: run_peer.py <tracker_host> <tracker_port> <my_port>")
        sys.exit(1)

    tracker_host, tracker_port, my_port = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    self_id = f"{socket.gethostname()}:{my_port}"

    # 1) JOIN tracker
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((tracker_host, tracker_port))
        s.sendall(f"JOIN {self_id}\n".encode())

    # 2) Start listener
    bc = Blockchain(difficulty=2)
    threading.Thread(
        target=listen_for_messages,
        args=(my_port, bc, tracker_host, tracker_port, self_id),
        daemon=True
    ).start()
    time.sleep(0.5)  # give the listener a moment

    # 3) Initial sync to longest chain
    peers = fetch_peers(tracker_host, tracker_port, self_id)
    best = bc.chain
    for p in peers:
        h, ps = p.split(':')
        cl = fetch_chain_from_peer(h, int(ps))
        if cl and len(cl) > len(best):
            best = [Block(**d) for d in cl]
    if len(best) > len(bc.chain):
        bc.chain = best
        print(f"[Startup] Synced chain length = {len(bc.chain)}")

    # 4) Interactive mining shell
    print("\nType text to mine a block, or 'exit' to quit.")
    try:
        while True:
            data = input(">> ")
            if data.lower() in ("exit", "quit"):
                break
            new_blk = bc.add_block(data)
            print(f"[Mined] #{new_blk.index} hash={new_blk.hash}")
            broadcast_block(new_blk.to_dict(), tracker_host, tracker_port, self_id)
            print(f"[Chain] length={len(bc.chain)}, latest={bc.get_latest_block().index}\n")
    except KeyboardInterrupt:
        pass

    print("Goodbye.")
