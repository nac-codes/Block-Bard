import unittest
from blockchain.blockchain import Blockchain
from blockchain.block import Block

class TestForkResolution(unittest.TestCase):
    def test_competing_miners(self):
        # Both nodes start fresh
        a = Blockchain(difficulty=1)
        b = Blockchain(difficulty=1)

        # Both mine block #1 differently
        blkA1 = a.add_block("A’s block 1")
        blkB1 = b.add_block("B’s block 1")
        # They should disagree on block1 hash
        self.assertNotEqual(a.get_latest_block().hash,
                            b.get_latest_block().hash)

        # Node A mines block #2 on top of its block1
        blkA2 = a.add_block("A’s block 2")
        self.assertEqual(len(a.chain), 3)  # genesis + blkA1 + blkA2

        # Node B sees blkA2 but rejects it (wrong prev_hash)
        added = b.add_block_from_dict(blkA2.to_dict())
        self.assertFalse(added)
        self.assertEqual(len(b.chain), 2)  # genesis + blkB1

        # Now B resolves conflicts by looking at A’s longer chain
        a_chain_dicts = [blk.to_dict() for blk in a.chain]
        replaced = b.resolve_conflicts([a_chain_dicts])
        self.assertTrue(replaced)

        # After resolution, B’s chain matches A’s
        self.assertEqual(len(b.chain), len(a.chain))
        for blk_b, blk_a in zip(b.chain, a.chain):
            self.assertEqual(blk_b.hash, blk_a.hash)

if __name__ == '__main__':
    unittest.main()