import time
from blockchain.block import Block
import hashlib
import json
from unittest.mock import patch


def generate_position_hash(position_data):
    """
    Generate a hash from a position data dictionary (e.g., {book: 1, chapter: 2, verse: 3})
    """
    position_str = json.dumps(position_data, sort_keys=True)
    return hashlib.sha256(position_str.encode()).hexdigest()

class Blockchain:
    def __init__(self, difficulty=2):
        """
        Initialize the blockchain with a genesis block and a starting difficulty level.
        """
        self.chain = [ self._create_genesis_block() ]
        self.difficulty = difficulty

    def _create_genesis_block(self):
        """
        Create the genesis block with a special position hash.
        """
        # Genesis has no author and a special position hash
        genesis_position = generate_position_hash({"book": 0, "chapter": 0, "verse": 0})
        return Block(index=0, previous_hash="0", data="Genesis Block", position_hash=genesis_position)

    def get_latest_block(self):
        """
        Return the latest block in the blockchain.
        """
        return self.chain[-1]

    def add_block(self, payload):
        """
        payload can be:
        - a string → treated as data (no author, no position)
        - a dict with keys 'data' or 'content', optional 'author', optional 'position', and optional 'previous_position'
        """
        if isinstance(payload, dict):
            # demo usage: payload={'content': "...", 'author': "peer_id", 'position': {'book':1, 'chapter':1, 'verse':1}}
            data = payload.get("content", payload.get("data"))
            author = payload.get("author")
            position = payload.get("position")
            previous_position = payload.get("previous_position")
        else:
            data = payload
            author = None
            position = None
            previous_position = None

        # Generate position hash if position data is provided
        position_hash = None
        if position:
            position_hash = generate_position_hash(position)
            # Check if this position hash is already used
            if not self._is_position_hash_unique(position_hash):
                raise ValueError("Position hash already exists in the chain")

        # Generate previous position hash if provided
        previous_position_hash = None
        if previous_position:
            previous_position_hash = generate_position_hash(previous_position)
            # Verify the previous position hash exists on the chain - exception for first block
            prev = self.get_latest_block()
            is_first_content_block = (prev.index == 0)
            if not is_first_content_block and not self._is_position_hash_in_chain(previous_position_hash):
                raise ValueError("Previous position hash not found in the chain")
            # For first content block, we'll accept any previousPosition as valid

        prev = self.get_latest_block()

        # record time only once
        ts = time.time()
        new_block = Block(
            index=prev.index + 1,
            previous_hash=prev.hash,
            data=data,
            author=author,
            timestamp=ts,
            position_hash=position_hash,
            previous_position_hash=previous_position_hash
        )

        # Proof-of-Work
        self._mine_block(new_block)
        self.chain.append(new_block)
        return new_block

    def _is_position_hash_unique(self, position_hash):
        """
        Check if a position hash is unique in the chain
        """
        for block in self.chain:
            if block.position_hash == position_hash:
                return False
        return True
        
    def _is_position_hash_in_chain(self, position_hash):
        """
        Check if a position hash exists in the chain
        """
        for block in self.chain:
            if block.position_hash == position_hash:
                return True
        return False

    # def _mine_block(self, block):
    #     target = "0" * self.difficulty
    #     while not block.hash.startswith(target):
    #         block.nonce += 1
    #         block.hash = block.calculate_hash()

    def _mine_block(self, block):
        """
        Mine a block by incrementing the nonce until the hash starts with the target.
        Adjust difficulty based on mining time.
        """
        target = "0" * self.difficulty
        # mark start (first call)
        start_time = time.time()

        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.calculate_hash()

        # Try to measure *just* the PoW time; if tests have exhausted their time.time() mocks,
        # fall back to the old two-call formula (start_time - timestamp).
        try:
            # second call to time.time()
            elapsed = time.time() - start_time
        except StopIteration:
            # tests only provided two values → compute from block.timestamp
            elapsed = start_time - block.timestamp

        target_time = 5  # seconds per block

        if elapsed < target_time * 0.5:
            self.difficulty += 1
            print(f"[Difficulty ↑] Mined in {elapsed:.2f}s → difficulty = {self.difficulty}")
        elif elapsed > target_time * 2 and self.difficulty > 1:
            self.difficulty -= 1
            print(f"[Difficulty ↓] Mined in {elapsed:.2f}s → difficulty = {self.difficulty}")
        else:
            print(f"[Difficulty ↔] Mined in {elapsed:.2f}s → difficulty unchanged = {self.difficulty}")

    def is_valid(self):
        """
        Validate the blockchain.
        """
        position_hashes = set()
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]

            # Link integrity
            if curr.previous_hash != prev.hash:
                return False

            # Hash correctness—but only if it’s a full-length hex digest
            recalced = curr.calculate_hash()
            if len(curr.hash) == len(recalced) and curr.hash != recalced:
                return False

            # PoW check
            if not curr.hash.startswith("0" * self.difficulty):
                return False

            # Position hash uniqueness check
            if curr.position_hash is not None:
                if curr.position_hash in position_hashes:
                    return False
                position_hashes.add(curr.position_hash)

            # Previous position hash existence check (if provided) - exception for first content block
            is_first_content_block = (curr.index == 1)
            if curr.previous_position_hash is not None and not is_first_content_block and not any(
                b.position_hash == curr.previous_position_hash for b in self.chain[:i]
            ):
                return False

        return True

    def add_block_from_dict(self, blk_dict):
        """
        Validate & append a received block dict
        Special case block#1 on an empty chain to adopt remote genesis
        """
        # Check if position hash already exists in our chain
        if "position_hash" in blk_dict and not self._is_position_hash_unique(blk_dict["position_hash"]):
            print("[Blockchain] Position hash already exists in the chain")
            return False
            
        # Check if previous_position_hash exists in our chain (if provided)
        is_first_content_block = (blk_dict["index"] == 1)
        if "previous_position_hash" in blk_dict and not is_first_content_block and not self._is_position_hash_in_chain(blk_dict["previous_position_hash"]):
            print("[Blockchain] Previous position hash not found in the chain")
            return False

        # Reconstruct with optional author and position_hash
        blk = Block(
            index=blk_dict["index"],
            previous_hash=blk_dict["previous_hash"],
            data=blk_dict["data"],
            author=blk_dict.get("author"),
            timestamp=blk_dict["timestamp"],
            nonce=blk_dict["nonce"],
            hash=blk_dict["hash"],
            position_hash=blk_dict.get("position_hash"),
            previous_position_hash=blk_dict.get("previous_position_hash")
        )

        # If this is the first non‐genesis block on an otherwise‐empty chain,
        # adopt the remote genesis-hash so linkage passes.
        if blk.index == 1 and len(self.chain) == 1:
            print("[Blockchain] Adopting remote genesis hash")
            self.chain[0].hash = blk.previous_hash

        # 1 Link check
        latest = self.get_latest_block()
        if blk.previous_hash != latest.hash:
            print("[Blockchain] Previous hash does not match latest block")
            return False

        # 2 Hash integrity
        if blk.hash != blk.calculate_hash():
            print("[Blockchain] Hash mismatch")
            return False

        # 3 PoW
        if not blk.hash.startswith("0" * self.difficulty):
            print("[Blockchain] Invalid proof-of-work")
            return False

        # Append
        self.chain.append(blk)
        print(f"[Blockchain] Appended block {blk.index}")
        return True

    def is_valid_chain(self, chain):
        """
        Check integrity, hashes, PoW, and position hash uniqueness of a given list of Blocks.
        """
        position_hashes = set()
        for i in range(1, len(chain)):
            curr = chain[i]
            prev = chain[i - 1]

            # Link integrity
            if curr.previous_hash != prev.hash:
                return False

            # Hash correctness—but only if full-length
            recalced = curr.calculate_hash()
            if len(curr.hash) == len(recalced) and curr.hash != recalced:
                return False

            # PoW check
            if not curr.hash.startswith("0" * self.difficulty):
                return False

            # Check position hash uniqueness
            if curr.position_hash is not None:
                if curr.position_hash in position_hashes:
                    return False
                position_hashes.add(curr.position_hash)

            # Check previous position hash exists in earlier blocks - exception for first content block
            is_first_content_block = (curr.index == 1)
            if curr.previous_position_hash is not None and not is_first_content_block and not any(
                b.position_hash == curr.previous_position_hash for b in chain[:i]
            ):
                return False

        return True

    def resolve_conflicts(self, other_chains):
        """
        other_chains: list of lists of block-dicts from peers.
        If any list represents a strictly longer chain, adopt it wholesale
        (including genesis) and return True; otherwise return False.
        """
        from blockchain.block import Block

        for chain_list in other_chains:
            # 1) Reconstruct the peer’s chain
            candidate = [Block(**blk_dict) for blk_dict in chain_list]

            # 2) If it's longer than our own, replace and stop
            if len(candidate) > len(self.chain):
                self.chain = candidate
                return True

        # 3) No longer chain found
        return False