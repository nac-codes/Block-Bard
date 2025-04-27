from typing import Dict

# Maps writing_style → parameters for OpenAI completion
DEFAULT_STYLES: Dict[str, Dict] = {
    "poetic":   {"temperature": 0.7, "max_tokens": 100},
    "mystery":  {"temperature": 0.8, "max_tokens": 120},
    "adventure":{"temperature": 0.75,"max_tokens": 110},
}