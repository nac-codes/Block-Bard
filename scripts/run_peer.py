#!/usr/bin/env python3
import socket
import sys
import threading
import json
import time
import atexit

from blockchain.blockchain import Blockchain
from blockchain.block import Block

def fetch_peers(tracker_host, tracker_port, self_id):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((tracker_host, tracker_port))
        s.sendall("GETPEERS\n".encode())
        data = s.recv(4096).decode().strip()
    return [p for p in data.splitlines() if p != self_id]

def fetch_chain_from_peer(host, port):
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

        # GETCHAIN → reply on same connection
        if raw == "GETCHAIN":
            payload = json.dumps([blk.to_dict() for blk in bc.chain])
            conn.sendall(f"CHAIN {payload}\n".encode())
            conn.close()
            continue

        # BLOCK broadcast
        if raw.startswith("BLOCK "):
            blk = json.loads(raw[len("BLOCK "):])
            idx = blk["index"]
            latest = bc.get_latest_block()

            if idx == latest.index + 1 and blk["previous_hash"] == latest.hash:
                bc.chain.append(Block(**blk))
                print(f"[Listener] Appended block {idx}")
            else:
                # out-of-order: sync longest chain
                print(f"[Listener] Out-of-order block {idx}; syncing…")
                peers = fetch_peers(tracker_host, tracker_port, self_id)
                best = bc.chain
                for p in peers:
                    h, ps = p.split(':')
                    cl = fetch_chain_from_peer(h, int(ps))
                    if cl and len(cl) > len(best):
                        best = [Block(**d) for d in cl]
                if len(best) > len(bc.chain):
                    bc.chain = best
                    print(f"[Listener] Synced; new length={len(bc.chain)}")
                else:
                    print("[Listener] No longer chain found.")
            conn.close()

def broadcast_block(blk_dict, tracker_host, tracker_port, self_id):
    peers = fetch_peers(tracker_host, tracker_port, self_id)
    msg = "BLOCK " + json.dumps(blk_dict) + "\n"
    for p in peers:
        if p == self_id:
            continue
        host, ps = p.split(':')
        port = int(ps)
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

    tracker_host, tracker_port, my_port = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    self_id = f"{socket.gethostname()}:{my_port}"

    # Register on join
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((tracker_host, tracker_port))
        s.sendall(f"JOIN {self_id}\n".encode())

    # On exit, notify tracker
    def unregister():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((tracker_host, tracker_port))
            s.sendall(f"LEAVE {self_id}\n".encode())
    atexit.register(unregister)

    # Start listener thread
    bc = Blockchain(difficulty=2)
    threading.Thread(
        target=listen_for_messages,
        args=(int(my_port), bc, tracker_host, tracker_port, self_id),
        daemon=True
    ).start()
    time.sleep(0.5)

    # Initial sync
    peers = fetch_peers(tracker_host, tracker_port, self_id)
    best = bc.chain
    for p in peers:
        h, ps = p.split(':')
        cl = fetch_chain_from_peer(h, int(ps))
        if cl and len(cl) > len(best):
            best = [Block(**d) for d in cl]
    if len(best) > len(bc.chain):
        bc.chain = best
        print(f"[Startup] Synced chain length={len(bc.chain)}")

    # Interactive shell
    print("\n===== Story Shell =====")
    print("Type any text to add a verse, 'show' to display story, or 'exit' to quit.\n")

    try:
        while True:
            line = input(">> ")
            cmd = line.strip().lower()
            if cmd in ("exit", "quit"):
                break
            if cmd == "show":
                for b in bc.chain:
                    auth = b.to_dict().get("author", "system")
                    print(f"#{b.index} ({auth}): {b.data}")
                print()
                continue

            # Mine & broadcast
            new_blk = bc.add_block({"content": line, "author": self_id})
            print(f"[Mined] #{new_blk.index} hash={new_blk.hash}")
            broadcast_block(new_blk.to_dict(), tracker_host, tracker_port, self_id)
            print(f"[Chain] length={len(bc.chain)}, latest={bc.get_latest_block().index}\n")

    except KeyboardInterrupt:
        pass

    print("Goodbye.")
