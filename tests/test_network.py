# tests/test_network.py

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
        time.sleep(0.1)  # let it bind

    def test_peer_registration_and_discovery(self):
        # 1) JOIN three peers
        peers = [f'peer{i}.local:5000{i}' for i in range(3)]
        for p in peers:
            with socket.socket() as s:
                s.connect(('127.0.0.1', self.tracker_port))
                s.sendall(f'JOIN {p}\n'.encode())

        # 2) GETPEERS should return all three
        with socket.socket() as s:
            s.connect(('127.0.0.1', self.tracker_port))
            s.sendall(b'GETPEERS\n')
            data = s.recv(1024).decode().splitlines()
        self.assertCountEqual(data, peers)

        # 3) LEAVE one peer
        to_remove = peers[1]
        with socket.socket() as s:
            s.connect(('127.0.0.1', self.tracker_port))
            s.sendall(f'LEAVE {to_remove}\n'.encode())

        # 4) GETPEERS again should return the other two
        with socket.socket() as s:
            s.connect(('127.0.0.1', self.tracker_port))
            s.sendall(b'GETPEERS\n')
            data2 = s.recv(1024).decode().splitlines()
        expected = [peers[0], peers[2]]
        self.assertCountEqual(data2, expected)

if __name__ == '__main__':
    unittest.main()
