#!/usr/bin/env python3
import os
import socket
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import hashlib

# Configuration
TRACKER_HOST = '127.0.0.1'
TRACKER_PORT = 8000
PEER_FETCH_TIMEOUT = 2  # seconds

# Paths
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, '../web/react-app/build'))
REACT_INDEX = os.path.join(STATIC_DIR, 'index.html')

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)  # Enable CORS for all routes

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
            
            # Read data in chunks to handle large blockchains
            chunks = []
            while True:
                chunk = s.recv(8192)  # 8KB chunks
                if not chunk:
                    break
                chunks.append(chunk)
                
                # Check if we've reached the end of the data (assuming \n ends the message)
                if chunk.endswith(b'\n'):
                    break
            
            # Combine all chunks and process
            full_data = b''.join(chunks).decode().strip()
            if full_data.startswith("CHAIN "):
                try:
                    return json.loads(full_data[len("CHAIN "):])
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from peer {peer}: {e}")
                    print(f"Received data length: {len(full_data)} bytes")
    except Exception as e:
        print(f"Error fetching chain from {peer}: {e}")
    return []

def find_position_data(position_hash, all_blocks):
    """Try to find position data in blocks with matching position hash."""
    for block in all_blocks:
        if block.get('position_hash') == position_hash:
            try:
                # Try to parse JSON data for position information
                data = json.loads(block.get('data', '{}'))
                if 'storyPosition' in data:
                    return data['storyPosition']
            except json.JSONDecodeError:
                pass
    return None

@app.route('/chain')
def chain():
    # Get pagination parameters
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=0, type=int)  # 0 means all
    
    peers = fetch_peers()
    if not peers:
        return jsonify([])
        
    # Pick first peer to fetch the chain
    chain_data = fetch_chain_from_peer(peers[0])
    
    # Apply pagination if requested
    if per_page > 0 and len(chain_data) > 0:
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Ensure we don't go out of bounds
        start_idx = min(start_idx, len(chain_data) - 1)
        end_idx = min(end_idx, len(chain_data))
        
        chain_data = chain_data[start_idx:end_idx]
        
    return jsonify(chain_data)

# Serve React App for any other routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    else:
        return send_from_directory(STATIC_DIR, 'index.html')

if __name__ == '__main__':
    # Run on port 60000
    app.run(host='0.0.0.0', port=60000, debug=True)
