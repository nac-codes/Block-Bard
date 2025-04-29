#!/usr/bin/env python3
import os
import socket
import json
from flask import Flask, jsonify, send_from_directory
import hashlib

# Configuration
TRACKER_HOST = '127.0.0.1'
TRACKER_PORT = 8000
PEER_FETCH_TIMEOUT = 2  # seconds

# Paths
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, '../web/static'))

app = Flask(__name__, static_folder=STATIC_DIR)

def fetch_peers():
    """Ask the tracker for current peer list."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(PEER_FETCH_TIMEOUT)
            s.connect((TRACKER_HOST, TRACKER_PORT))
            s.sendall(b"GETPEERS\n")
            data = s.recv(4096).decode().strip()
        return [p for p in data.splitlines()]
    except Exception:
        return []

def fetch_chain_from_peer(peer):
    """GETCHAIN from one peer, return list of block‐dicts."""
    host, port_s = peer.split(':')
    port = int(port_s)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(PEER_FETCH_TIMEOUT)
            s.connect((host, port))
            s.sendall(b"GETCHAIN\n")
            resp = s.recv(65536).decode().strip()
        if resp.startswith("CHAIN "):
            return json.loads(resp[len("CHAIN "):])
    except Exception:
        pass
    return []

def find_position_data(position_hash, all_blocks):
    """Try to find position data in blocks with matching position hash."""
    for block in all_blocks:
        if block.get('position_hash') == position_hash:
            # Reverse-lookup position data
            for verse in range(1, 100):
                test_data = {"book": 1, "chapter": 1, "verse": verse}
                test_json = json.dumps(test_data, sort_keys=True)
                test_hash = hashlib.sha256(test_json.encode()).hexdigest()
                if test_hash == position_hash:
                    return test_data
    return None

@app.route('/')
def index():
    # Serve the static HTML
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/chain')
def chain():
    peers = fetch_peers()
    if not peers:
        return jsonify([])
    # Pick first peer to fetch the chain
    chain_data = fetch_chain_from_peer(peers[0])
    
    # Try to find position data for each block
    for block in chain_data:
        if 'position_hash' in block:
            position = find_position_data(block['position_hash'], chain_data)
            if position:
                block.update(position)
    
    return jsonify(chain_data)

if __name__ == '__main__':
    # Run on port 5000
    app.run(host='0.0.0.0', port=60000)
