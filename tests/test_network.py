import unittest
import threading
import time
import socket

from network.tracker import Tracker

class TestP2PNetwork(unittest.TestCase):
    def setUp(self):
        # start tracker on localhost:10000
        self.tracker_port = 10000
        self.tracker = Tracker(host='127.0.0.1', port=self.tracker_port)
        self.thread = threading.Thread(target=self.tracker.start, daemon=True)
        self.thread.start()
        # give it a moment to bind
        time.sleep(0.1)

    def test_peer_registration_and_discovery(self):
        # Define three fake peers
        peers = [f'peer{i}.local:5000{i}' for i in range(3)]
        # Each one sends a JOIN
        for p in peers:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', self.tracker_port))
                s.sendall(f'JOIN {p}\n'.encode())
        # Now ask for GETPEERS
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', self.tracker_port))
            s.sendall(b'GETPEERS\n')
            data = s.recv(1024).decode().splitlines()
        # The tracker should report exactly those peers
        self.assertCountEqual(data, peers)

if __name__ == '__main__':
    unittest.main()