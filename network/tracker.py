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
            threading.Thread(target=self.handle_peer, args=(conn, addr), daemon=True).start()

    def handle_peer(self, conn, addr):
        try:
            data = conn.recv(1024).decode().strip()
            if data.startswith("JOIN"):
                _, peer_addr = data.split(maxsplit=1)
                self.peers.add(peer_addr)
                print(f"[+] Registered peer: {peer_addr}")
            # Send back the full list, one per line
            resp = "\n".join(self.peers) + "\n"
            conn.sendall(resp.encode())
        except Exception as e:
            print("Error handling peer:", e)
        finally:
            conn.close()