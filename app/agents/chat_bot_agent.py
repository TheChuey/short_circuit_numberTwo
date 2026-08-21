"""
app/agents/chat_bot_agent.py
============================

Thin wiring: config/chat_bot.json -> PromptManager -> Agent

All prompt logic lives in class_library.py.
All runtime logic lives in class_definition.py.
"""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from build.class_definition import Agent
from app.agents.class_library import PromptManager
from app.tools.tools import SKILL_REGISTRY

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
AGENT_FILE = CONFIG_DIR / "chat_bot.json"

# PERMISSION CONTROL: restrict which tools the AI may use.
# None = every skill listed in chat_bot.json is allowed.
# Example: TOOL_ALLOWLIST = {"read_file", "get_current_date", "tell_me_the_date_and_time"}
TOOL_ALLOWLIST: set[str] | None = None


def _select_tools(config: dict) -> tuple[list, list[str]]:
    """Apply TOOL_ALLOWLIST and SKILL_REGISTRY checks to the config's skills.

    Returns (tool functions, loaded skill IDs). Blocked and missing skills are
    reported loudly instead of silently dropped.
    """
    loaded_ids: list[str] = []
    for skill_id in config.get("skills", []):
        if TOOL_ALLOWLIST is not None and skill_id not in TOOL_ALLOWLIST:
            print(f"[TOOLS] '{skill_id}' blocked by TOOL_ALLOWLIST - not loaded")
        elif skill_id in SKILL_REGISTRY:
            loaded_ids.append(skill_id)
        else:
            print(f"[TOOLS] WARNING: skill '{skill_id}' is listed in chat_bot.json but missing from SKILL_REGISTRY - skipped")
    return [SKILL_REGISTRY[sid] for sid in loaded_ids], loaded_ids


def run_agent(message: str, history: list[dict] | None = None, model: str | None = None, adjustments: dict | None = None) -> str:
    """Build a fresh agent, replay history, ask the LLM."""
    config = json.loads(AGENT_FILE.read_text(encoding="utf-8"))
    profile = PromptManager.build(config, adjustments)
    tools, loaded_ids = _select_tools(config)
    # Keep the prompt honest: advertise exactly the skills that were loaded,
    # so the model never tries to call a blocked or missing tool.
    profile.skills_table = [s for s in profile.skills_table if s.get("id") in loaded_ids]
    chat_bot_agent = Agent(model or config.get("default_model"), tools, profile)

    for m in (history or []):
        role = "assistant" if m.get("role") == "ai" else m.get("role", "user")
        content = m.get("content", "")
        if not content:
            continue
        chat_bot_agent.messages.append({"role": role, "content": content})

    return chat_bot_agent.think(message)


if __name__ == "__main__":
    demo = run_agent("hello", [], None, None)
    print(f"Agent replied: {demo[:100]}...")


# HOW IT WORKS
# ============
# 1. server.py calls run_agent() with the user's message, chat history, and model.
# 2. run_agent() reads config/chat_bot.json (generated from chat_bot_agent.md).
# 3. PromptManager.build() creates an AgentProfile with a composed system prompt.
# 4. SKILL_REGISTRY maps skill IDs from config to actual functions.
# 5. Agent is created with model, tools, and profile.
# 6. Chat history is replayed into agent.messages.
# 7. agent.think() sends everything to the LLM and returns the reply.
