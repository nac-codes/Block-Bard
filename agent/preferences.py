# agent/preferences.py
from dataclasses import dataclass
from typing import List

@dataclass
class AgentPreferences:
    """
    Configuration for an AI storyteller agent.
    """
    writing_style: str        # e.g. "poetic", "mystery"
    themes: List[str]         # e.g. ["adventure", "friendship"]
    characters: List[str]     # e.g. ["Alice", "The Dragon"]