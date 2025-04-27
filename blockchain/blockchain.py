from blockchain.block import Block

class Blockchain:
    def __init__(self, difficulty=2):
        self.chain = [ self._create_genesis_block() ]
        self.difficulty = difficulty

    def _create_genesis_block(self):
        # Genesis has no author
        return Block(index=0, previous_hash="0", data="Genesis Block")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, payload):
        """
        payload can be:
        - a string → treated as data (no author)
        - a dict with keys 'data' or 'content', and optional 'author'
        """
        if isinstance(payload, dict):
            # demo usage: payload={'content': "...", 'author': "peer_id"}
            data = payload.get("content", payload.get("data"))
            author = payload.get("author")
        else:
            data = payload
            author = None

        prev = self.get_latest_block()
        new_block = Block(
            index=prev.index + 1,
            previous_hash=prev.hash,
            data=data,
            author=author
        )
        # Proof‐of‐Work
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
            # Link integrity
            if curr.previous_hash != prev.hash:
                return False
            # Hash correctness
            if curr.hash != curr.calculate_hash():
                return False
            # PoW check
            if not curr.hash.startswith("0" * self.difficulty):
                return False
        return True

    def add_block_from_dict(self, blk_dict):
        """
        Validate & append a received block‐dict.
        Special‐case block#1 on an empty chain to adopt remote genesis.
        """
        # Reconstruct with optional author
        blk = Block(
            index=blk_dict["index"],
            previous_hash=blk_dict["previous_hash"],
            data=blk_dict["data"],
            author=blk_dict.get("author"),
            timestamp=blk_dict["timestamp"],
            nonce=blk_dict["nonce"],
            hash=blk_dict["hash"],
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
        Check integrity, hashes, and PoW of a given list of Blocks.
        """
        for i in range(1, len(chain)):
            curr = chain[i]
            prev = chain[i-1]
            if curr.previous_hash != prev.hash:
                return False
            if curr.hash != curr.calculate_hash():
                return False
            if not curr.hash.startswith("0" * self.difficulty):
                return False
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
            if len(candidate) > len(max_chain) and self.is_valid_chain(candidate):
                max_chain = candidate
        if len(max_chain) > len(self.chain):
            self.chain = max_chain
            return True
        return False