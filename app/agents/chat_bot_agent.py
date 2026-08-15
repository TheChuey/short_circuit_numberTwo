"""
app/agents/chat_bot_agent.py
============================

BUILDS THE CHATBOT AGENT FROM CONFIG
------------------------------------

This module's job is to turn the generated config files into a usable Agent:

    config/agent.json   -> the agent's name, system prompt, skills (per-agent list)
    app/tools/tools.py  -> SKILL_REGISTRY: the master catalog of tool functions

    build_agent(model)  -> Agent(model, tools, AgentProfile(...))

Tools resolution (one line):
    agent.json's 'skills' list says WHICH registered tools this agent gets.
    Each id is looked up in SKILL_REGISTRY (app/tools/tools.py) -> callables.

Flow of data:
    read_markdown/app_blueprint.md (human edits) -> read_markdown/markdown_loader.py
    (at server start) -> config/agent.json -> this module -> build_agent() ->
    POST /api/chat.

    config/skills.json (generated from SKILL_REGISTRY by AppConfig) is kept
    as a catalog / test point -- build_agent() resolves tools straight from
    SKILL_REGISTRY, so it does NOT read skills.json at runtime.

Why a factory (build_agent) instead of one global agent?
    Each HTTP request gets a FRESH agent with an empty conversation history.
    The frontend keeps its own chat history, so the server stays stateless
    and two requests can never share/leak conversation memory.
"""

import json
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# PATH BOOTSTRAP
# --------------------------------------------------------------------------
# Allow running this file directly (`python app/agents/chat_bot_agent.py`)
# from anywhere: make sure the backend root is on sys.path so that the
# `build` and `app` packages below can be imported. Harmless when the app is
# launched via `python server.py` (root is already on the path).
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# --------------------------------------------------------------------------
# IMPORTS
# --------------------------------------------------------------------------
# The Agent engine (Agent, AgentProfile) comes from the single
# source of truth for all classes: build/class_definition.py.
from build.class_definition import Agent, AgentProfile

# The skill-name -> function registry lives in the master tools module
# (app/tools/tools.py). To add a new skill: define the function there,
# register it in SKILL_REGISTRY, then list its name in read_markdown/app_blueprint.md.
from app.tools.tools import SKILL_REGISTRY

# --------------------------------------------------------------------------
# CONFIG FILE LOCATIONS
# --------------------------------------------------------------------------
# The JSON configs are generated at server start by read_markdown/markdown_loader.py:
#   chat_bot.json     <- read_markdown/chatbot_prompt.md   (CURRENT chat source)
#   agent.json        <- read_markdown/app_blueprint.md    (kept alongside, same shape)
# This module only READS the JSON file. To switch sources, change AGENT_FILE.
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
AGENT_FILE = CONFIG_DIR / "chat_bot.json"      # This line of code will give the agent its charate and basic information
SKILLS_FILE = CONFIG_DIR / "skills.json"    # {"skills": [{id, name, function}]} - generated
# catalog from SKILL_REGISTRY (kept as a test point; build_agent() does NOT
# read it at runtime - tools resolve straight from SKILL_REGISTRY).


# --------------------------------------------------------------------------
# THE FACTORY
# --------------------------------------------------------------------------

def build_agent(model: str | None = None) -> Agent:

    # 1. Agent character: name + system prompt from agent.json.
    try:
        config = json.loads(AGENT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = {
            "name": "Agent",
            "system_prompt": "You are a helpful AI agent.",
            "skills": [],
            "default_model": "",
        }
        print(f"[chat_bot_agent] warning: could not read {AGENT_FILE} - using defaults")
    profile = AgentProfile(
        name=config["name"],
        system_prompt=config["system_prompt"],
    )

    # 2. Pick the model: explicit arg wins, else the configured default.
    model_name = model or config.get("default_model") or None

    # 3. Tools: enable the skills listed in agent.json. The tool functions live
    #    in SKILL_REGISTRY (app/tools/tools.py) - agent.json only says WHICH
    #    registered tools this agent gets (ids == registry keys).
    tools = [SKILL_REGISTRY[sid] for sid in config.get("skills", []) if sid in SKILL_REGISTRY]

    # 4. Assemble the Agent with its model, tools and character.
    agent = Agent(
        model=model_name,
        tools=tools,
        profile=profile,
    )
    return agent


# --------------------------------------------------------------------------
# ONE CHAT TURN (with history) - what POST /api/chat calls
# --------------------------------------------------------------------------
# The server stays stateless: every turn builds a FRESH agent, then replays
# the frontend's stored history into the agent's message list so the LLM
# sees the whole conversation (system prompt + every prior user/AI turn).
# agent.tools is already loaded from SKILL_REGISTRY here, so a future tool
# loop (think -> act -> observe) can slot in inside this function.
def run_agent(message: str, history: list[dict] | None = None, model: str | None = None) -> str:
    agent = build_agent(model=model)  # Fresh agent (stateless server - no shared memory).

    # Rewind the stored conversation into the loop, keeping only non-empty content
    for m in (history or []):
        role = "assistant" if m.get("role") == "ai" else m.get("role", "user")
        content = m.get("content", "")
        if not content:  # drop empty bubbles so they don't pollute the prompt
            continue
        agent.messages.append({"role": role, "content": content})

    return agent.think(message)  # think() appends this new user turn, asks the LLM, returns the reply.


# --------------------------------------------------------------------------
# STANDALONE SANITY CHECK (no input(), no chat loop)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Quick check that the config loads and an agent can be built without
    # calling the LLM. Real conversation input comes from POST /api/chat.
    demo = build_agent()
    print(f"Built agent: '{demo.profile.name}'")
    print(f"  tools: {list(demo.tools.keys())}")
    print(f"  model: {demo.model}")

