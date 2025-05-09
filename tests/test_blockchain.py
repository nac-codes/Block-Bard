import unittest
from blockchain.blockchain import Blockchain
from blockchain.block import Block
from unittest.mock import patch

class TestBlockchain(unittest.TestCase):
    def test_valid_chain(self):
        bc = Blockchain(difficulty=1)
        def fake_mine(block):
            block.hash = '0' * bc.difficulty + 'abc'
        bc._mine_block = fake_mine
        bc.add_block("block A")
        bc.add_block("block B")
        self.assertTrue(bc.is_valid())

    def test_tamper_data(self):
        bc = Blockchain(difficulty=1)
        blk = bc.add_block("block A")
        # Tamper with data
        blk.data = "evil"
        self.assertFalse(bc.is_valid())

    def test_tamper_pow(self):
        bc = Blockchain(difficulty=2)
        blk = bc.add_block("block A")
        # Break PoW by resetting nonce/hash
        blk.nonce = 0
        blk.hash = blk.calculate_hash()
        self.assertFalse(bc.is_valid())

    def test_add_block_from_dict_accept(self):
        # Peer B starts fresh, then accepts a valid block from Peer A
        bc = Blockchain(difficulty=1)
        # Simulate A’s chain of length 2
        a_chain = Blockchain(difficulty=1)
        blk_a = a_chain.add_block("block A")
        blk_b = a_chain.add_block("block B")
        # B pulls A’s first block
        self.assertTrue(bc.add_block_from_dict(blk_a.to_dict()))
        # B pulls A’s second block
        self.assertTrue(bc.add_block_from_dict(blk_b.to_dict()))
        self.assertTrue(bc.is_valid())
        self.assertEqual(len(bc.chain), 3)  # genesis + A + B

    def test_add_block_from_dict_reject(self):
        bc = Blockchain(difficulty=1)
        # Make a fake block dict
        fake = {
            "index": 1,
            "timestamp": 1234567890.0,
            "data": "fake",
            "previous_hash": "WRONG", # the previous hash here is not valid, so should fail
            "nonce": 0,
            "hash": "0000"  # even if it meets PoW
        }
        self.assertFalse(bc.add_block_from_dict(fake))
        self.assertEqual(len(bc.chain), 1)  # only genesis

    def test_dynamic_difficulty_adjusts(self): 
        bc = Blockchain(difficulty=1)
        initial_difficulty = bc.difficulty

        # Add multiple blocks to allow time-based adjustment
        for i in range(5):
            bc.add_block(f"block {i}")

        # Check that difficulty has changed at least once
        self.assertTrue(bc.difficulty >= 1)
        self.assertNotEqual(initial_difficulty, bc.difficulty)

    def test_difficulty_increases_and_decreases(self):
        bc = Blockchain(difficulty=2)

        # Simulate fast mining
        with patch("time.time", side_effect=[0, 1]):  # 1 second elapsed
            bc.add_block("fast block")
            self.assertEqual(bc.difficulty, 3)

        # Simulate slow mining
        with patch("time.time", side_effect=[0, 12]):  # 12 seconds elapsed
            bc.add_block("slow block")
            self.assertEqual(bc.difficulty, 2)


if __name__ == "__main__":
    unittest.main()