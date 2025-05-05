# network/tracker.py
import socket
import threading

class Tracker:
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.peers = set()

    def start(self):
        """
        start the tracker server to accept peer registry requests
        runs indefinitely, spawning a new thread for each incoming connection

        it binds to self.host:self.port, listens for TCP connections,
        and uses handle_peer() to process JOIN/LEAVE/GETPEERS commands
        in separate daemon threads

        arguments:
        None

        return:
        None
        """
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind((self.host, self.port))
        srv.listen()
        print(f"Tracker listening on {self.host}:{self.port}")
        while True:
            conn, _ = srv.accept()
            # handle each request in its own thread
            threading.Thread(target=self.handle_peer, args=(conn,), daemon=True).start()

    def handle_peer(self, conn):
        """
        Commands:
          GETPEERS           - returns the current peer list, one per line
          JOIN <peer_addr>   - adds peer_addr to the registry
          LEAVE <peer_addr>  - removes peer_addr from the registry
        """
        try:
            data = conn.recv(1024).decode().strip()
            if not data:
                return

            parts = data.split(maxsplit=1)
            cmd = parts[0].upper()

            # Return the full list of peers
            if cmd == "GETPEERS":
                resp = "\n".join(self.peers) + "\n"
                conn.sendall(resp.encode())

            # Register a new peer
            elif cmd == "JOIN" and len(parts) == 2:
                peer_addr = parts[1]
                self.peers.add(peer_addr)
                print(f"[+] Registered peer: {peer_addr}")

            # Unregister a departing peer
            elif cmd == "LEAVE" and len(parts) == 2:
                peer_addr = parts[1]
                if peer_addr in self.peers:
                    self.peers.remove(peer_addr)
                    print(f"[-] Unregistered peer: {peer_addr}")

        finally:
            conn.close()