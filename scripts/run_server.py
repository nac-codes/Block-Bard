#!/usr/bin/env python3
import os
import socket
import json
from flask import Flask, jsonify, send_from_directory

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
    chain = fetch_chain_from_peer(peers[0])
    return jsonify(chain)

if __name__ == '__main__':
    # Run on port 5000
    app.run(host='0.0.0.0', port=60000)
