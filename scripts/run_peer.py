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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((tracker_host, tracker_port))
        s.sendall("GETPEERS\n".encode())
        data = s.recv(4096).decode().strip()
    return [p for p in data.splitlines() if p != self_id]

def fetch_chain_from_peer(host, port):
    """
    fetch blockchain data from a single peer
    blocking until a CHAIN response is received or an error occurs

    it opens a TCP connection to the given host:port, sends GETCHAIN,
    decodes the response, and returns the parsed chain if valid

    arguments:
    host -- peer's hostname or IP address
    port -- peer's TCP port number

    return:
    list of block dictionaries on success, or None on failure
    """
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
    """
    listen for chain and block messages on given port
    blocking until each message is processed

    it binds to the specified port, accepts TCP connections in a loop,
    replies to GETCHAIN requests with the full blockchain, processes
    incoming BLOCK messages by appending valid next blocks or, if out-of-order,
    syncing to the longest chain available from peers

    arguments:
    port           -- TCP port to listen on for incoming peer connections
    bc             -- blockchain instance with attributes chain and get_latest_block()
    tracker_host   -- tracker's hostname or IP address for peer discovery
    tracker_port   -- tracker's port number for peer discovery
    self_id        -- this node's identifier to exclude from peer list

    return:
    None
    """
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
    """
    broadcast a new block to all peers except self
    blocking until each send attempt completes

    it retrieves the current peer list via fetch_peers(), constructs a
    BLOCK message by JSON-serializing blk_dict, skips this node's own ID,
    and sends the message to each remaining peer, logging success or error

    arguments:
    blk_dict      -- dictionary containing the block data to broadcast
    tracker_host  -- the tracker's hostname or IP address for peer discovery
    tracker_port  -- the tracker's port number for peer discovery
    self_id       -- this node's identifier to exclude from broadcasting

    return:
    None
    """
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
            print(f"[Broadcast] - {p}")
        except Exception as e:
            print(f"[Broadcast] x {p}: {e}")

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
