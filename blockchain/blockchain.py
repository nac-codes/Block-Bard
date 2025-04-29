from blockchain.block import Block
import hashlib
import json

def generate_position_hash(position_data):
    """
    Generate a hash from a position data dictionary (e.g., {book: 1, chapter: 2, verse: 3})
    """
    position_str = json.dumps(position_data, sort_keys=True)
    return hashlib.sha256(position_str.encode()).hexdigest()

class Blockchain:
    def __init__(self, difficulty=2):
        self.chain = [ self._create_genesis_block() ]
        self.difficulty = difficulty

    def _create_genesis_block(self):
        # Genesis has no author and a special position hash
        genesis_position = generate_position_hash({"book": 0, "chapter": 0, "verse": 0})
        return Block(index=0, previous_hash="0", data="Genesis Block", position_hash=genesis_position)

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, payload):
        """
        payload can be:
        - a string → treated as data (no author, no position)
        - a dict with keys 'data' or 'content', optional 'author', and optional 'position'
        """
        if isinstance(payload, dict):
            # demo usage: payload={'content': "...", 'author': "peer_id", 'position': {'book':1, 'chapter':1, 'verse':1}}
            data = payload.get("content", payload.get("data"))
            author = payload.get("author")
            position = payload.get("position")
        else:
            data = payload
            author = None
            position = None

        # Generate position hash if position data is provided
        position_hash = None
        if position:
            position_hash = generate_position_hash(position)
            # Check if this position hash is already used
            if not self._is_position_hash_unique(position_hash):
                raise ValueError("Position hash already exists in the chain")

        prev = self.get_latest_block()
        new_block = Block(
            index=prev.index + 1,
            previous_hash=prev.hash,
            data=data,
            author=author,
            position_hash=position_hash
        )
        # Proof‐of‐Work
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

    def _mine_block(self, block):
        target = "0" * self.difficulty
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.calculate_hash()

    def is_valid(self):
        position_hashes = set()
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i-1]
            # Link integrity
            if curr.previous_hash != prev.hash:
                return False
            # Hash correctness
            if curr.hash != curr.calculate_hash():
                return False
            # PoW check
            if not curr.hash.startswith("0" * self.difficulty):
                return False
            # Position hash uniqueness check
            if curr.position_hash is not None:
                if curr.position_hash in position_hashes:
                    return False
                position_hashes.add(curr.position_hash)
        return True

    def add_block_from_dict(self, blk_dict):
        """
        Validate & append a received block‐dict.
        Special‐case block#1 on an empty chain to adopt remote genesis.
        """
        # Check if position hash already exists in our chain
        if "position_hash" in blk_dict and not self._is_position_hash_unique(blk_dict["position_hash"]):
            print("[Blockchain] Position hash already exists in the chain")
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
            position_hash=blk_dict.get("position_hash")
        )

        # If this is the first non‐genesis block on an otherwise‐empty chain,
        # adopt the remote genesis-hash so linkage passes.
        if blk.index == 1 and len(self.chain) == 1:
            print("[Blockchain] Adopting remote genesis hash")
            self.chain[0].hash = blk.previous_hash

        # 1) Link check
        latest = self.get_latest_block()
        if blk.previous_hash != latest.hash:
            print("[Blockchain] Previous hash does not match latest block")
            return False

        # 2) Hash integrity
        if blk.hash != blk.calculate_hash():
            print("[Blockchain] Hash mismatch")
            return False

        # 3) PoW
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
            prev = chain[i-1]
            if curr.previous_hash != prev.hash:
                return False
            if curr.hash != curr.calculate_hash():
                return False
            if not curr.hash.startswith("0" * self.difficulty):
                return False
            # Check position hash uniqueness
            if curr.position_hash is not None:
                if curr.position_hash in position_hashes:
                    return False
                position_hashes.add(curr.position_hash)
        return True

    def resolve_conflicts(self, other_chains):
        """
        other_chains: list of lists of block‐dicts from peers.
        If any is a valid chain longer than ours, adopt it.
        Returns True if replaced.
        """
        max_chain = self.chain
        for chain_list in other_chains:
            # Reconstruct Block objects
            candidate = [Block(**d) for d in chain_list]
            # Verify chain validity including position hash uniqueness
            if len(candidate) > len(max_chain) and self.is_valid_chain(candidate):
                max_chain = candidate
        if len(max_chain) > len(self.chain):
            self.chain = max_chain
            return True
        return False