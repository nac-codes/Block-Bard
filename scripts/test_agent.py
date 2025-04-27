#!/usr/bin/env python3
import os
from agent.preferences import AgentPreferences
from agent.storyteller import StoryTeller

# 1) Ensure API key is loaded
assert os.getenv("OPENAI_API_KEY"), "Please export OPENAI_API_KEY first"

# 2) Configure your agent’s style, themes, characters
prefs = AgentPreferences(
    writing_style="poetic",
    themes=["magic", "courage"],
    characters=["Alice", "The Dragon"]
)
st = StoryTeller(prefs)

# 3) Provide some context
context = [
    "Once upon a time there was a brave knight.",
    "He ventured into the dark forest."
]

# 4) Generate and print one line
print("AI →", st.generate(context))
