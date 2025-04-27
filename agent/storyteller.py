# agent/storyteller.py

import os
from openai import OpenAI
from typing import List

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

    def generate(self, context: List[str]) -> str:
        prompt = self._build_prompt(context)
        style = DEFAULT_STYLES.get(self.prefs.writing_style, {})
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
            return text.split("\n")[0]
        except Exception as e:
            # Fallback on any API error (rate limits, network, etc.)
            print(f"[StoryTeller] API error ({e}); using placeholder.")
            return "..."  # fallback content
