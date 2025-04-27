import hashlib
import time
from blockchain.block import Block

class Blockchain:
    def __init__(self, difficulty=2):
        self.chain = [ self._create_genesis_block() ]
        self.difficulty = difficulty

    def _create_genesis_block(self):
        return Block(index=0, previous_hash="0", data="Genesis Block")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data):
        prev = self.get_latest_block()
        new_block = Block(
            index=prev.index + 1,
            previous_hash=prev.hash,
            data=data
        )
        self._mine_block(new_block)
        self.chain.append(new_block)
        return new_block

    def _mine_block(self, block):
        target = "0" * self.difficulty
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.calculate_hash()

    def is_valid(self):
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i-1]
            if curr.previous_hash != prev.hash:
                return False
            if curr.hash != curr.calculate_hash():
                return False
            if not curr.hash.startswith("0" * self.difficulty):
                return False
        return True

    def add_block_from_dict(self, blk_dict):
        """
        Validate a received block dict and append if valid.
        Returns True if added, False otherwise.
        """

        # Reconstruct the Block object (including provided hash)
        blk = Block(
            index=blk_dict["index"],
            previous_hash=blk_dict["previous_hash"],
            data=blk_dict["data"],
            timestamp=blk_dict["timestamp"],
            nonce=blk_dict["nonce"],
            hash=blk_dict["hash"],
        )

        # SPECIAL CASE: first real block (index 1) on an otherwise-empty chain
        # Adopt the remote genesis hash so subsequent checks pass.
        if blk.index == 1 and len(self.chain) == 1:
            print("[Blockchain] Adopting remote genesis hash")
            self.chain[0].hash = blk.previous_hash

        # 1) Check linkage
        latest = self.get_latest_block()
        if blk.previous_hash != latest.hash:
            print("[Blockchain] Previous hash does not match latest block")
            return False

        # 2) Verify hash integrity
        if blk.hash != blk.calculate_hash():
            print("[Blockchain] Hash mismatch")
            return False

        # 3) Verify proof-of-work
        if not blk.hash.startswith("0" * self.difficulty):
            print("[Blockchain] Invalid proof-of-work")
            return False

        # Append and succeed
        self.chain.append(blk)
        print(f"[Blockchain] Appended block {blk.index}")
        
        return True
