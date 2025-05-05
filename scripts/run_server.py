#!/usr/bin/env python3
import os
import socket
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import hashlib
import time
import concurrent.futures

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
# Configure CORS with exposed headers to ensure pagination headers are accessible
CORS(app, expose_headers=[
    'X-Total-Blocks', 
    'X-Page', 
    'X-Per-Page', 
    'X-Total-Pages'
])

def fetch_peers():
    """Ask the tracker for current peer list."""
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
    """GETCHAIN from one peer, return list of block‐dicts."""
    host, port_s = peer.split(':')
    port = int(port_s)
    
    # Increase timeouts for more reliable data transfer
    PEER_FETCH_TIMEOUT = 20  # Increase from 10 to 20 seconds
    MAX_RETRIES = 3
    
    for retry in range(MAX_RETRIES):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Set socket options for better reliability
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                # Set buffer sizes
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)  # 1MB receive buffer
                
                print(f"Connecting to {host}:{port} (attempt {retry+1}/{MAX_RETRIES})")
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
                
                # Read the first chunk to get the header
                initial_chunk = s.recv(1024)
                if not initial_chunk:
                    print(f"Connection closed by {peer} without data")
                    continue
                
                # Check for the CHAIN prefix
                if not initial_chunk.startswith(b"CHAIN "):
                    print(f"Invalid response prefix from {peer}: {initial_chunk[:20]}")
                    continue
                
                # Add the initial chunk minus the prefix to our chunks list
                chunks.append(initial_chunk[6:])
                total_bytes = len(initial_chunk) - 6
                
                print(f"Got CHAIN prefix from {peer}, reading data...")
                
                # Now read the actual chain data in a loop
                while True:
                    try:
                        chunk = s.recv(65536)  # 64KB chunks
                        if not chunk:
                            print(f"Connection closed by {peer}, total received: {total_bytes} bytes")
                            break
                        
                        chunks.append(chunk)
                        total_bytes += len(chunk)
                        
                        # Print progress for large chains
                        if total_bytes > 1024*1024 and total_bytes % (1024*1024) < 65536:
                            print(f"Received {total_bytes/1024/1024:.2f}MB from {peer}")
                    
                    except socket.timeout:
                        # If we get a timeout but have received some data, consider it complete
                        if total_bytes > 0:
                            print(f"Socket timeout with {total_bytes} bytes received, processing data")
                            break
                        else:
                            print(f"Socket timeout receiving data from {peer} with no data received")
                            break
                    except Exception as e:
                        print(f"Error receiving data from {peer}: {e}")
                        break
                
                # Process the data only if we received something
                if chunks:
                    full_data = b''.join(chunks)
                    
                    # Print debug info
                    print(f"Received {len(full_data)/1024:.2f}KB from {peer} in {time.time()-start_time:.2f}s")
                    
                    # Try to decode and parse the JSON
                    try:
                        chain_json = full_data.decode().strip()
                        chain_data = json.loads(chain_json)
                        print(f"Successfully parsed chain data with {len(chain_data)} blocks")
                        return chain_data
                    except UnicodeDecodeError as e:
                        print(f"Error decoding response from {peer}: {e}")
                        print(f"First 100 bytes: {full_data[:100]}")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON from {peer} ({e})")
                        # Try to salvage what we can - look for complete JSON
                        if len(chain_json) > 0:
                            try:
                                # Look for closing bracket of JSON array
                                last_bracket = chain_json.rfind(']')
                                if last_bracket > 0:
                                    truncated_json = chain_json[:last_bracket+1]
                                    chain_data = json.loads(truncated_json)
                                    print(f"Salvaged partial chain data with {len(chain_data)} blocks")
                                    return chain_data
                            except Exception:
                                pass
                        print(f"Could not salvage JSON data")
        
        except ConnectionRefusedError:
            print(f"Connection refused by {peer}")
        except socket.timeout:
            print(f"Timeout connecting to {peer}")
        except Exception as e:
            print(f"Error fetching chain from {peer}: {e}")
        
        print(f"Retry {retry+1}/{MAX_RETRIES} failed for {peer}")
    
    print(f"All retries failed for {peer}")
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
        print("No peers found to fetch chain from")
        return jsonify([])
    
    print(f"Found {len(peers)} peers: {peers}")
    
    # Limit to 3 peers to try for performance
    if len(peers) > 3:
        # Sort peers by hostname so the selection is deterministic
        peers.sort()
        peers = peers[:3]
        print(f"Limited to 3 peers: {peers}")
    
    # Try all peers in parallel and use the first valid result
    chain_data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(peers)) as executor:
        # Submit all peer fetch tasks
        future_to_peer = {executor.submit(fetch_chain_from_peer, peer): peer for peer in peers}
        
        # Wait for first successful result or all to complete
        for future in concurrent.futures.as_completed(future_to_peer):
            peer = future_to_peer[future]
            try:
                result = future.result()
                if result and len(result) > 0:
                    print(f"Successfully fetched chain with {len(result)} blocks from {peer}")
                    chain_data = result
                    break  # Use first successful result
                else:
                    print(f"Failed to fetch chain from {peer}")
            except Exception as e:
                print(f"Exception fetching from {peer}: {e}")
    
    if not chain_data:
        print("Could not fetch blockchain from any peer")
        return jsonify([]), 503  # Service Unavailable
    
    # Apply pagination if requested
    if per_page > 0 and len(chain_data) > 0:
        # If requesting a specific page, calculate indices
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Ensure we don't go out of bounds
        start_idx = min(start_idx, len(chain_data) - 1) if len(chain_data) > 0 else 0
        end_idx = min(end_idx, len(chain_data))
        
        # Add chain length as response header
        resp = jsonify(chain_data[start_idx:end_idx])
        resp.headers['X-Total-Blocks'] = str(len(chain_data))
        resp.headers['X-Page'] = str(page)
        resp.headers['X-Per-Page'] = str(per_page)
        resp.headers['X-Total-Pages'] = str((len(chain_data) + per_page - 1) // per_page)
        
        # Debug header information
        print(f"Setting pagination headers: X-Total-Blocks={len(chain_data)}, X-Total-Pages={(len(chain_data) + per_page - 1) // per_page}")
        print(f"Returning {end_idx - start_idx} blocks (page {page} of {(len(chain_data) + per_page - 1) // per_page})")
        return resp
    
    # For non-paginated requests, set headers on the response directly
    resp = jsonify(chain_data)
    if len(chain_data) > 0:
        resp.headers['X-Total-Blocks'] = str(len(chain_data))
        resp.headers['X-Page'] = '1'
        resp.headers['X-Per-Page'] = str(len(chain_data))
        resp.headers['X-Total-Pages'] = '1'
        print(f"Setting headers for full response: X-Total-Blocks={len(chain_data)}")
    
    print(f"Returning complete chain with {len(chain_data)} blocks")
    return resp

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
