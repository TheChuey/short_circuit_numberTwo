"""
app/agents/chat_bot_basic.py
============================

Builds the minimal fallback chatbot from config/chat_bot_basic.json.
No tools. Basic system prompt.

This is the fallback used when chat_bot_agent.py has no valid config.
"""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from build.class_definition import Agent
from app.agents.class_library import AgentProfile, PromptManager

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
BASIC_FILE = CONFIG_DIR / "chat_bot_basic.json"


def build_basic_agent(model: str | None = None) -> Agent:
    """Build a minimal Agent from config/chat_bot_basic.json.

    If the config is missing or empty, uses hardcoded defaults.
    """
    try:
        config = json.loads(BASIC_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = {}

    if not config.get("name"):
        config = {"name": "Chat", "role": "You are a helpful assistant."}

    profile = PromptManager.build(config)
    return Agent(model=model, tools=[], profile=profile)


if __name__ == "__main__":
    demo = build_basic_agent()
    print(f"Built basic agent: '{demo.profile.name}'")
    print(f"  tools: {list(demo.tools.keys())}")
    print(f"  model: {demo.model}")
    print(f"  system_prompt: {demo.profile.system_prompt}")
