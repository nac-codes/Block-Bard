# agent/preferences.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class AgentPreferences:
    """
    Configuration for an AI storyteller agent.
    """
    writing_style: str        # e.g. "poetic", "mystery", "biblical"
    themes: List[str]         # e.g. ["adventure", "friendship"]
    characters: List[str]     # e.g. ["Alice", "The Dragon"]
    
    # Tone preferences
    tone: str = "neutral"     # e.g. "neutral", "optimistic", "ominous", "serene"
    
    # Content controls
    genre: Optional[str] = None       # e.g. "fantasy", "sci-fi", "historical" 
    era: Optional[str] = None         # e.g. "ancient", "medieval", "modern"
    setting: Optional[str] = None     # e.g. "forest", "spaceship", "kingdom"
    
    # Theological preferences (for religious content)
    denomination: Optional[str] = None    # e.g. "Catholic", "Protestant", "Orthodox"
    theological_positions: Dict[str, str] = field(default_factory=dict)  # e.g. {"grace": "works-based"}
    doctrinal_emphasis: List[str] = field(default_factory=list)  # e.g. ["salvation", "authority"]
    
    # Format preferences
    verbosity: float = 1.0    # Multiplier for response length (0.5 = shorter, 2.0 = longer)
    formality: int = 5        # 1-10 scale, 1 = very casual, 10 = very formal
    
    # Custom values for extra flexibility
    custom_properties: Dict[str, Any] = field(default_factory=dict)