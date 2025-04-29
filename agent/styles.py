from typing import Dict

# Maps writing_style → parameters for OpenAI completion
DEFAULT_STYLES: Dict[str, Dict] = {
    # Literary styles
    "poetic": {
        "temperature": 0.7,
        "max_tokens": 100,
        "description": "Lyrical and metaphorical language with emphasis on rhythm and imagery"
    },
    "prose": {
        "temperature": 0.6,
        "max_tokens": 150,
        "description": "Standard narrative prose with clear structure and exposition"
    },
    "mystery": {
        "temperature": 0.8,
        "max_tokens": 120,
        "description": "Suspenseful writing with clues, red herrings, and gradual reveals"
    },
    "adventure": {
        "temperature": 0.75,
        "max_tokens": 110,
        "description": "Action-oriented style with exciting scenarios and obstacles to overcome"
    },
    
    # Scholarly styles
    "academic": {
        "temperature": 0.4,
        "max_tokens": 180,
        "description": "Formal language with citations, careful analysis, and measured conclusions"
    },
    "technical": {
        "temperature": 0.3,
        "max_tokens": 160,
        "description": "Precise, detailed descriptions using specialized terminology"
    },
    
    # Religious styles
    "biblical": {
        "temperature": 0.55,
        "max_tokens": 130,
        "description": "Formal, archaic language similar to King James or other traditional Bible translations"
    },
    "theological": {
        "temperature": 0.5,
        "max_tokens": 170,
        "description": "Explores religious concepts with doctrinal context and spiritual insights"
    },
    
    # Personal styles
    "casual": {
        "temperature": 0.85,
        "max_tokens": 100,
        "description": "Conversational and relaxed tone with colloquialisms"
    },
    "humorous": {
        "temperature": 0.9,
        "max_tokens": 120,
        "description": "Lighthearted, witty, or comedic content with jokes or wordplay"
    },
    "philosophical": {
        "temperature": 0.65,
        "max_tokens": 180,
        "description": "Contemplative style exploring deeper meanings and abstract concepts"
    }
}

def get_style_parameters(style_name: str) -> Dict:
    """Get parameters for a given style, falling back to 'prose' if not found"""
    if style_name in DEFAULT_STYLES:
        return DEFAULT_STYLES[style_name]
    return DEFAULT_STYLES["prose"]