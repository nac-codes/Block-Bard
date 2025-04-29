import hashlib
import time
import json

class Block:
    def __init__(self,
                 index,
                 previous_hash,
                 data,
                 author=None,
                 timestamp=None,
                 nonce=0,
                 hash=None,
                 position_hash=None):
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.data = data            # original "payload" for tests
        self.author = author        # optional, for demo
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.position_hash = position_hash

        # Use provided hash (from network sync or tests), else compute
        if hash:
            self.hash = hash
        else:
            self.hash = self.calculate_hash()

    def calculate_hash(self):
        # If author is set, include it in the PoW payload
        if self.author is not None:
            payload = (
                f"{self.index}"
                f"{self.timestamp}"
                f"{self.data}"
                f"{self.author}"
                f"{self.previous_hash}"
                f"{self.nonce}"
                f"{self.position_hash}"
            )
        else:
            # test‐compatible payload (no author)
            payload = (
                f"{self.index}"
                f"{self.timestamp}"
                f"{self.data}"
                f"{self.previous_hash}"
                f"{self.nonce}"
                f"{self.position_hash}"
            )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self):
        # Always include 'data' for your tests.
        d = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }
        # Only include author and position_hash if set
        if self.author is not None:
            d["author"] = self.author
        if self.position_hash is not None:
            d["position_hash"] = self.position_hash
        return d
