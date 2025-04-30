# agent/storyteller.py

import os
import json
import logging
from openai import OpenAI
from typing import List, Dict, Any, Tuple, Optional, Union

from agent.story_config import load_schema
from agent.schema_utils import create_pydantic_model_from_schema

class StoryTeller:
    def __init__(self, schema_name_or_path="bible", api_key=None, system_prompt=None):
        self.schema = load_schema(schema_name_or_path)
        
        # Set up logging
        self.logger = logging.getLogger("storyteller")
        
        # Get API key
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.logger.error("OpenAI API key not found in parameters or environment")
            raise RuntimeError("Please set OPENAI_API_KEY in your environment")
            
        # Initialize the OpenAI client
        self.logger.debug("Initializing OpenAI client")
        self.client = OpenAI(api_key=api_key)
        
        # Load system prompt if provided
        self.system_prompt = self._load_system_prompt(system_prompt)
        
        # Create a Pydantic model from the schema
        self.StoryModel = create_pydantic_model_from_schema(self.schema)

    def _load_system_prompt(self, system_prompt):
        """Load system prompt from file path or use provided string"""
        default_prompt = "You are a creative AI who responds with structured content."
        
        if not system_prompt:
            return default_prompt
            
        # Check if it's a file path
        if os.path.isfile(system_prompt):
            try:
                with open(system_prompt, 'r') as f:
                    prompt = f.read().strip()
                self.logger.info(f"Loaded system prompt from file: {system_prompt}")
                return prompt
            except Exception as e:
                self.logger.error(f"Error loading system prompt file: {e}")
                return default_prompt
        
        # Otherwise, return the provided string
        return system_prompt

    def _build_prompt(self, context: List[str], chain=None, node_id=None) -> str:
        """
        Build a prompt for the AI model using the context and schema
        """
        # Get last few entries for conciseness
        last_lines = "\n".join(context[-3:]) if context else "No previous entries."
        
        # Start building prompt
        prompt = f"Continue the content based on previous entries.\n\n"
        prompt += f"Previous content:\n{last_lines}\n\n"
        
        # Add information about all available positions
        if chain and len(chain) > 1:  # Skip if only genesis block
            prompt += "Content structure so far (you can branch from any of these):\n"
            positions_found = []
            
            # Get the last 1000 blocks maximum, from newest to oldest
            relevant_blocks = sorted(chain, key=lambda b: b.index, reverse=True)[:1000]
            
            for block in relevant_blocks:
                if block.index == 0:  # Skip genesis block
                    continue
                    
                try:
                    data = json.loads(block.data)
                    if "storyPosition" in data:
                        pos_str = json.dumps(data["storyPosition"])
                        content = data.get("Content", "")                        
                        author = data.get("Author", block.author if hasattr(block, "author") else "Unknown")
                        prompt += f"- Position {pos_str}: {content} [Author: {author}]\n"
                        positions_found.append(data["storyPosition"])
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            if not positions_found:
                prompt += "No structured positions found. You should create the first position (Genesis 1:1).\n"
            
            prompt += "\n"
        else:
            # If this is the first content, explicitly direct it to start with Genesis 1:1
            prompt += "You should start with Genesis 1:1.\n\n"
        
        # Add node ID information
        if node_id:
            prompt += f"You are node {node_id}. Make your contribution reflect your unique perspective.\n\n"
        
        # Add schema information
        prompt += f"Your response must be a valid JSON object with the following schema:\n{json.dumps(self.schema, indent=2)}\n\n"
        prompt += "IMPORTANT INSTRUCTIONS:\n"
        prompt += "1. You MUST include both 'storyPosition' and 'previousPosition' in your response.\n"
        prompt += "2. 'storyPosition' should be a NEW unique position that doesn't exist yet.\n"
        prompt += "3. 'previousPosition' should reference an EXISTING position from the content that you're continuing from.\n"
        prompt += "4. If this is the first content, use the position structure {\"book\": \"Genesis\", \"chapter\": 1, \"verse\": 1} and set previousPosition to null.\n"
        prompt += "5. Position should reflect the logical structure of the content (book, chapter, verse).\n"
        prompt += "6. You can branch from any previous position if there's a logical reason to create an alternate version.\n"
        
        return prompt

    def _extract_positions_from_chain(self, chain) -> List[Dict]:
        """Extract all position data from blocks in the chain"""
        positions = []
        for block in chain:
            if block.index == 0:  # Skip genesis
                continue
                
            try:
                data = json.loads(block.data)
                if "storyPosition" in data:
                    positions.append(data["storyPosition"])
            except (json.JSONDecodeError, AttributeError):
                continue
                
        return positions

    def generate(self, context: List[str], chain=None, node_id=None) -> Tuple[str, Dict, Optional[Dict]]:
        """
        Generate next content, letting the AI determine position and previous position
        Returns (content_json, position_dict, previous_position_dict)
        
        Args:
            context: List of previous content strings
            chain: The blockchain
            node_id: ID of the current node (for competition awareness)
        """
        prompt = self._build_prompt(context, chain, node_id)
        
        self.logger.debug("Calling OpenAI API to generate content")
        
        # Use the model parsing approach for structured data
        try:
            response = self.client.responses.parse(
                model="gpt-4.1-mini-2025-04-14",
                input=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                text_format=self.StoryModel
            )
            
            # Access the parsed Pydantic model
            story_entry = response.output_parsed
            
            # Convert Pydantic model to dict
            story_dict = story_entry.model_dump()
            json_response = json.dumps(story_dict)
            
            self.logger.debug(f"Successfully parsed structured response: {json_response}")
            
            position = story_dict.get("storyPosition")
            prev_position = story_dict.get("previousPosition")
            
            if not position:
                self.logger.error("Response missing required storyPosition field")
                raise ValueError("Missing storyPosition in response")
                
            return json_response, position, prev_position
            
        except Exception as e:
            self.logger.error(f"Failed to generate valid content: {e}")
            raise ValueError(f"Failed to generate valid content: {e}")
