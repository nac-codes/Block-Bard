#!/usr/bin/env python3
import threading
import time

from blockchain.blockchain import Blockchain

class MiningAgent(threading.Thread):
    def __init__(self, bc: Blockchain, storyteller, broadcast_fn,
                 agent_name: str, mine_interval=5.0):
        """
        bc           - your Blockchain instance
        storyteller  - a StoryTeller instance
        broadcast_fn - function taking a block-dict and broadcasting it
        agent_name   - unique name to stamp each block's author
        mine_interval- seconds between mining attempts
        """
        super().__init__(daemon=True)
        self.bc = bc
        self.st = storyteller
        self.broadcast = broadcast_fn
        self.agent_name = agent_name
        self.interval = mine_interval

    def run(self):
        while True:
            # 1) Build context from existing chain
            context = [blk.data for blk in self.bc.chain]
            # 2) Ask the AI for the next line
            next_line = self.st.generate(context)
            # 3) Mine & append the new block with this agent’s name
            blk = self.bc.add_block({
                "content": next_line,
                "author": self.agent_name
            })
            print(f"[Agent] Mined block #{blk.index}: {next_line!r}")
            # 4) Broadcast to peers
            self.broadcast(blk.to_dict())
            # 5) Wait before next mining round
            time.sleep(self.interval)