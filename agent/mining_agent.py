# agent/mining_agent.py

import threading
import time
import json

from blockchain.blockchain import Blockchain
from blockchain.block import Block

class MiningAgent(threading.Thread):
    def __init__(self, bc: Blockchain, storyteller, broadcast_fn, mine_interval=5.0):
        """
        bc           - your Blockchain instance
        storyteller  - a StoryTeller instance
        broadcast_fn - function taking a block-dict and broadcasting it
        mine_interval- seconds between mining attempts
        """
        super().__init__(daemon=True)
        self.bc = bc
        self.st = storyteller
        self.broadcast = broadcast_fn
        self.interval = mine_interval

    def run(self):
        while True:
            # 1) Build context from existing chain
            context = [blk.data for blk in self.bc.chain]
            # 2) Ask the AI for the next line
            next_line = self.st.generate(context)
            # 3) Mine & append the new block
            blk = self.bc.add_block({"content": next_line, "author": self.st.prefs.writing_style})
            print(f"[Agent] Mined block #{blk.index}: {next_line!r}")
            # 4) Broadcast to peers
            self.broadcast(blk.to_dict())
            # 5) Wait before next mining round
            time.sleep(self.interval)
