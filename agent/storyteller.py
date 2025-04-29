# agent/storyteller.py

import os
from openai import OpenAI
from typing import List, Dict, Any

from agent.preferences import AgentPreferences
from agent.styles import DEFAULT_STYLES

class StoryTeller:
    def __init__(self, prefs: AgentPreferences):
        self.prefs = prefs
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Please set OPENAI_API_KEY in your environment")
        # Initialize the new client
        self.client = OpenAI(api_key=api_key)

    def _build_prompt(self, context: List[str]) -> str:
        last_lines = "\n".join(context[-3:])
        themes = ", ".join(self.prefs.themes)
        chars  = ", ".join(self.prefs.characters)
        return (
            f"Continue this collaborative story.\n\n"
            f"Previous lines:\n{last_lines}\n\n"
            f"Themes: {themes}\n"
            f"Characters: {chars}\n\n"
            f"Next line:"
        )
    
    def calculate_position(self, chain) -> Dict[str, int]:
        """
        Calculate the next story position based on blockchain content
        Default structure: book, chapter, verse
        """
        # Extract blocks with position_hash (skip Genesis)
        blocks_with_position = [b for b in chain if b.position_hash is not None and b.index > 0]
        
        if not blocks_with_position:
            # First real entry after Genesis
            return {"book": 1, "chapter": 1, "verse": 1}
            
        # For this simple implementation, we just increment the verse
        # A more complex implementation could handle chapter/book transitions
        return {"book": 1, "chapter": 1, "verse": len(blocks_with_position) + 1}

    def generate(self, context: List[str], chain=None) -> tuple:
        """
        Generate next story line and its position
        Returns (text, position_dict)
        """
        prompt = self._build_prompt(context)
        style = DEFAULT_STYLES.get(self.prefs.writing_style, {})
        
        # Calculate position
        position = None
        if chain:
            position = self.calculate_position(chain)
        
        try:
            resp = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative AI storyteller."},
                    {"role": "user",   "content": prompt}
                ],
                temperature=style.get("temperature", 0.7),
                max_tokens=style.get("max_tokens", 100)
            )
            text = resp.choices[0].message.content.strip()
            return text.split("\n")[0], position
        except Exception as e:
            # Fallback on any API error (rate limits, network, etc.)
            print(f"[StoryTeller] API error ({e}); using placeholder.")
            return "...", position  # fallback content
