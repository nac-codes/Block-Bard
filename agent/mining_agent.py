#!/usr/bin/env python3
import threading
import time
import json
import logging

from blockchain.blockchain import Blockchain
from agent.storyteller import StoryTeller

class MiningAgent(threading.Thread):
    def __init__(self, bc: Blockchain, storyteller: StoryTeller, broadcast_fn,
                 agent_name: str, mine_interval=5.0, story_schema="bible"):
        """
        bc           - your Blockchain instance
        storyteller  - a StoryTeller instance
        broadcast_fn - function taking a block-dict and broadcasting it
        agent_name   - unique name to stamp each block's author
        mine_interval- seconds between mining attempts
        story_schema - name of the story schema to use
        """
        super().__init__(daemon=True)
        self.bc = bc
        self.st = storyteller
        self.broadcast = broadcast_fn
        self.agent_name = agent_name
        self.interval = mine_interval
        self.story_schema = story_schema
        
        # Set up logging
        self.logger = logging.getLogger(f"mining_agent_{agent_name}")
        
        # Track failed attempts to avoid repeatedly trying the same thing
        self.recent_failures = []
        self.max_failures = 3

    def run(self):
        while True:
            try:
                # 1) Build context from existing chain
                context = [blk.data for blk in self.bc.chain]
                
                # 2) Ask the AI for the next story content and position data
                json_content, position, previous_position = self.st.generate(
                    context, 
                    self.bc.chain,
                    node_id=self.agent_name
                )
                
                # Skip if we couldn't generate a position
                if not position:
                    self.logger.warning("Couldn't determine story position, skipping this round")
                    time.sleep(self.interval)
                    continue
                
                # Check if we recently failed with this position
                position_key = json.dumps(position, sort_keys=True)
                if position_key in self.recent_failures:
                    self.logger.warning(f"Position already failed recently: {position}, skipping")
                    time.sleep(self.interval)
                    continue
                    
                # 3) Mine & append the new block with this agent's name and position
                try:
                    # Parse the JSON content returned by storyteller
                    try:
                        data_dict = json.loads(json_content)
                        # Update the Author field
                        data_dict["Author"] = f"{self.agent_name}"
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON content from storyteller: {json_content}")
                        # Use the raw string content
                        data_dict = None
                    
                    # Prepare the payload with position data
                    if data_dict:
                        # If the position data is valid
                        if isinstance(position, dict) and len(position) > 0:
                            # Use the full JSON as data
                            payload = {
                                "content": json.dumps(data_dict),
                                "author": self.agent_name,
                                "position": position
                            }
                            # Add previous position if available and valid
                            if isinstance(previous_position, dict) and len(previous_position) > 0:
                                payload["previous_position"] = previous_position
                        else:
                            self.logger.warning(f"Invalid position data: {position}")
                            raise ValueError("Invalid position data")
                    else:
                        # Use the raw text as data
                        payload = {
                            "content": json_content,
                            "author": self.agent_name,
                            "position": position
                        }
                        # Add previous position if available and valid
                        if isinstance(previous_position, dict) and len(previous_position) > 0:
                            payload["previous_position"] = previous_position
                    
                    # Mine the block
                    blk = self.bc.add_block(payload)
                    
                    pos_str = json.dumps(position)
                    prev_pos_str = f", continuing from {json.dumps(previous_position)}" if previous_position else ""
                    self.logger.info(f"Mined block #{blk.index}: {json_content[:50]}... {pos_str}{prev_pos_str}")
                    
                    # Clear failures list on success
                    self.recent_failures = []
                    
                    # 4) Broadcast to peers
                    self.broadcast(blk.to_dict())
                    
                except ValueError as e:
                    # This happens if position hash is already taken or previous position not found
                    self.logger.warning(f"Mining failed: {e}")
                    
                    # Add to failures list
                    self.recent_failures.append(position_key)
                    if len(self.recent_failures) > self.max_failures:
                        self.recent_failures.pop(0)  # Remove oldest
                    
            except Exception as e:
                self.logger.error(f"Error in mining loop: {e}")
                
            # 5) Wait before next mining round
            jitter = (0.5 + 0.5 * hash(self.agent_name) % 100 / 100.0)  # Add jitter of ±50%
            wait_time = self.interval * jitter
            self.logger.debug(f"Waiting {wait_time:.2f} seconds before next attempt")
            time.sleep(wait_time)