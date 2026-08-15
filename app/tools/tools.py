# The model backend classes live in build/class_definition.py (pure class
# definitions); the shared instances are wired together in the composition
# root, build/composition.py. ask_llm is re-exported here so the public name
# `from app.tools.tools import ask_llm` keeps working.
from build.composition import ask_llm

# SKILL_REGISTRY shim: agent skills were removed because there is no tool loop
# (think() -> LLMClient.chat() -> ask_llm()); the only skill, get_current_date,
# was never invoked at runtime. Kept as an EMPTY dict so its consumers keep
# working unchanged: app/agents/chat_bot_agent.py resolves skills against it
# (yielding no tools), and write_markdown/app_config.py generates an empty
# skills.json / tools.md from it. Re-add skills here when a real tool loop ships.

SKILL_REGISTRY = {}
