# network/tracker.py
import socket
import threading

class Tracker:
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.peers = set()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        print(f"Tracker listening on {self.host}:{self.port}")
        while True:
            conn, addr = self.sock.accept()
            threading.Thread(target=self.handle_peer, args=(conn,), daemon=True).start()

    def handle_peer(self, conn):
        data = conn.recv(1024).decode().strip()
        # If a peer wants the current list
        if data == "GETPEERS":
            resp = "\n".join(self.peers) + "\n"
            conn.sendall(resp.encode())
            conn.close()
            return

        # Otherwise we expect a JOIN message
        if data.startswith("JOIN"):
            _, peer_addr = data.split(maxsplit=1)
            self.peers.add(peer_addr)
            print(f"[+] Registered peer: {peer_addr}")
        # no other commands
        conn.close()
