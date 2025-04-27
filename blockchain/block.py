# blockchain/block.py
import hashlib
import time

class Block:
    def __init__(self, index, previous_hash, data, timestamp=None, nonce=0, hash=None):
        self.index = index
        # Preserve provided timestamp or use current time
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        if hash:
            # Use the hash from the dict when syncing
            self.hash = hash
        else:
            # Otherwise compute it fresh (for new blocks)
            self.hash = self.calculate_hash()

    def calculate_hash(self):
        payload = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }
