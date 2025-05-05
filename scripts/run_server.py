#!/usr/bin/env python3
import os
import socket
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import hashlib
import time

# Configuration
TRACKER_HOST = '127.0.0.1'
TRACKER_PORT = 8000
PEER_FETCH_TIMEOUT = 10  # Increased from 2 to 10 seconds
PEER_CONNECT_TIMEOUT = 3  # Added separate connection timeout

# Paths
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, '../web/react-app/build'))
REACT_INDEX = os.path.join(STATIC_DIR, 'index.html')

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)  # Enable CORS for all routes

def fetch_peers():
    """
    ask the tracker for the current peer list
    blocking until peer list is received or a timeout/error occurs

    it connects to the tracker using TRACKER_HOST and TRACKER_PORT,
    sends GETPEERS, reads the response lines, resolves hostnames to IPs,
    and returns a list of "ip:port" strings (falling back to hostname on resolution failure)

    arguments:
    None

    return:
    list of peer address strings in "ip:port" format, or empty list on error
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(PEER_CONNECT_TIMEOUT)
            s.connect((TRACKER_HOST, TRACKER_PORT))
            s.sendall(b"GETPEERS\n")
            data = s.recv(4096).decode().strip()
        # Convert hostnames to IP addresses
        peers = []
        for peer in data.splitlines():
            host, port = peer.split(':')
            try:
                # Try to resolve hostname to IP
                ip = socket.gethostbyname(host)
                peers.append(f"{ip}:{port}")
            except socket.gaierror:
                # If resolution fails, use the original hostname
                peers.append(peer)
        return peers
    except Exception as e:
        print(f"Error fetching peers: {e}")
        return []

def fetch_chain_from_peer(peer):
    """
    fetch blockchain data from a single peer
    blocking until the full chain is received or an error/timeout occurs

    it parses the peer address, connects over TCP with timeouts,
    sends GETCHAIN, verifies the "CHAIN " prefix, streams the JSON payload
    in chunks (with size and timeout safety checks), and returns the parsed list

    arguments:
    peer -- address string in "host:port" format of the peer to query

    return:
    list of block dictionaries on success, or empty list on failure
    """
    host, port_s = peer.split(':')
    port = int(port_s)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Set socket options for better reliability
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            # Set buffer sizes
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)  # 1MB receive buffer
            
            print(f"Connecting to {host}:{port}")
            s.settimeout(PEER_CONNECT_TIMEOUT)  # Use shorter timeout for connection
            s.connect((host, port))
            
            print(f"Connected to {host}:{port}, sending GETCHAIN")
            s.sendall(b"GETCHAIN\n")
            
            # After connection, set longer timeout for data receipt
            s.settimeout(PEER_FETCH_TIMEOUT)
            
            # Read the response in chunks
            chunks = []
            start_time = time.time()
            total_bytes = 0
            
            # First, try to read the initial "CHAIN " prefix
            prefix = b""
            while len(prefix) < 6:  # "CHAIN " is 6 bytes
                chunk = s.recv(6 - len(prefix))
                if not chunk:
                    print(f"Connection closed by {peer} while reading prefix")
                    return []
                prefix += chunk
            
            if prefix != b"CHAIN ":
                print(f"Invalid response prefix from {peer}: {prefix}")
                return []
            
            print(f"Got CHAIN prefix from {peer}, reading data...")
            
            # Now read the actual chain data
            while True:
                try:
                    chunk = s.recv(65536)  # 64KB chunks
                    if not chunk:
                        print(f"Connection closed by {peer}, total received: {total_bytes} bytes")
                        break
                    
                    chunks.append(chunk)
                    total_bytes += len(chunk)
                    
                    # Print progress for large chains
                    if total_bytes > 1024*1024:  # 1MB
                        print(f"Received {total_bytes/1024/1024:.2f}MB from {peer}")
                    
                    # Safety check for too much data (100MB limit)
                    if total_bytes > 100 * 1024 * 1024:
                        print(f"Response too large from {peer}: {total_bytes/1024/1024:.2f}MB")
                        break
                        
                    # Safety check for timeout
                    if time.time() - start_time > PEER_FETCH_TIMEOUT:
                        print(f"Timeout receiving data from {peer}")
                        break
                
                except socket.timeout:
                    # Timeout occurred, but we might have received enough data
                    print(f"Socket timeout receiving data from {peer}, but received {total_bytes} bytes")
                    break
                except Exception as e:
                    print(f"Error receiving data from {peer}: {e}")
                    break
            
            # Process the data only if we received something
            if chunks:
                full_data = b''.join(chunks)
                
                # Print some debug info
                print(f"Received {len(full_data)/1024:.2f}KB from {peer} in {time.time()-start_time:.2f}s")
                
                # Try to decode and parse the JSON
                try:
                    chain_json = full_data.decode().strip()
                    chain_data = json.loads(chain_json)
                    print(f"Successfully parsed chain data with {len(chain_data)} blocks")
                    return chain_data
                except UnicodeDecodeError as e:
                    print(f"Error decoding response from {peer}: {e}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from {peer}: {e}")
                    print(f"First 100 chars: {full_data[:100]}")
    
    except ConnectionRefusedError:
        print(f"Connection refused by {peer}")
    except socket.timeout:
        print(f"Timeout connecting to {peer}")
    except Exception as e:
        print(f"Error fetching chain from {peer}: {e}")
    
    return []

def find_position_data(position_hash, all_blocks):
    """
    find position data in blocks matching a given position hash
    blocking until a matching block with valid JSON data is found

    it iterates through all_blocks, compares each block's 'position_hash',
    attempts to parse its 'data' field as JSON, and returns the 'storyPosition'
    value if present

    arguments:
    position_hash -- hash string identifying the target position
    all_blocks    -- iterable of block dictionaries, each with keys 'position_hash' and 'data'

    return:
    the storyPosition value if found and parsed successfully, otherwise None
    """
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
    """
    retrieve and return the blockchain with optional pagination
    blocking until a valid chain is fetched from a peer or none available

    it discovers peers via fetch_peers(), attempts to GETCHAIN from each until
    successful, then applies page/per_page query parameters to slice the result

    arguments:
    None (uses query params):
      - page     -- 1-based page number (default=1)
      - per_page -- number of blocks per page (default=0 for all)

    return:
    JSON list of block dictionaries (possibly paginated), or empty list if fetch fails
    """
    # Get pagination parameters
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=0, type=int)  # 0 means all
    
    peers = fetch_peers()
    if not peers:
        print("No peers found to fetch chain from")
        return jsonify([])
    
    print(f"Found {len(peers)} peers: {peers}")
    
    # Try multiple peers until we get a valid chain
    chain_data = []
    for peer in peers:
        print(f"Trying to fetch chain from {peer}")
        peer_chain = fetch_chain_from_peer(peer)
        
        if peer_chain and len(peer_chain) > 0:
            print(f"Successfully fetched chain with {len(peer_chain)} blocks from {peer}")
            chain_data = peer_chain
            break
        else:
            print(f"Failed to fetch chain from {peer}")
    
    # Apply pagination if requested
    if per_page > 0 and len(chain_data) > 0:
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Ensure we don't go out of bounds
        start_idx = min(start_idx, len(chain_data) - 1)
        end_idx = min(end_idx, len(chain_data))
        
        chain_data = chain_data[start_idx:end_idx]
    
    print(f"Returning {len(chain_data)} blocks")
    return jsonify(chain_data)

# Serve React App for any other routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """
    serve static files with SPA fallback
    blocking until the requested file is sent or index.html fallback

    it checks if the given path exists under STATIC_DIR and returns it;
    otherwise, it returns the default index.html for single-page apps

    arguments:
    path -- requested file path relative to STATIC_DIR

    return:
    Flask response: the file from STATIC_DIR or index.html on fallback
    """
    if path != "" and os.path.exists(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    else:
        return send_from_directory(STATIC_DIR, 'index.html')

if __name__ == '__main__':
    # Run on port 60000
    app.run(host='0.0.0.0', port=60000, debug=True)
