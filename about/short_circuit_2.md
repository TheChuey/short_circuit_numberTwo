# short_circuit_2

## 2026-08-19 — PromptBuilder + Basic Chatbot Extraction

**What changed:** Added PromptBuilder utility class, moved AgentProfile to class_library.py, created PromptManager, extracted basic chatbot into its own module.

### New architecture

```
app/agents/class_library.py
    ├── AgentProfile (with from_dict)
    ├── PromptBuilder (template utilities)
    └── PromptManager (build + compose_system_prompt)

build/class_definition.py
    ├── Agent (runtime)
    └── ask_llm (LLM backend)

app/agents/chat_bot_agent.py
    └── build_agent() — thin wiring (imports fallback from chat_bot_basic)

app/agents/chat_bot_basic.py
    └── build_basic_agent() — minimal fallback, no tools
```

### New files

| File | Purpose |
|---|---|
| `read_markdown/chat_bot_basic.md` | Basic chatbot definition (no skills, simple role) |
| `app/agents/chat_bot_basic.py` | Builds basic agent from config/chat_bot_basic.json |
| `about/replicate_agent.txt` | Prompt for any AI to replicate agent creation |

### Files modified

| File | Change |
|---|---|
| `app/agents/class_library.py` | AgentProfile + PromptBuilder + PromptManager |
| `build/class_definition.py` | Agent + ask_llm (imports AgentProfile from class_library) |
| `app/agents/chat_bot_agent.py` | Thin wiring, imports fallback from chat_bot_basic |
| `read_markdown/markdown_loader.py` | Added BASIC_LOADER for chat_bot_basic.md |
| `read_markdown/agents_index.md` | Added basic chatbot to index |

---

## 2026-08-19 — Safety Net Removal + Graceful Fallback

**What changed:** Removed all hardcoded default agent/tool/model templates. If a config file is missing, the server falls back to a minimal chatbot (no tools, basic prompt) and the frontend shows a simplified UI.

### What was removed

| What | Before | After |
|---|---|---|
| `DEFAULT_AGENT_DEFINITION` | Hardcoded fallback template | **Removed** — raises `FileNotFoundError` |
| `DEFAULT_TOOLS_BLUEPRINT` | Hardcoded fallback template | **Removed** — raises `FileNotFoundError` |
| `DEFAULT_MODEL = "llama3.1"` | Hardcoded model string | **Removed** — raises `RuntimeError` if no model |
| `build_agent()` try/except | Returns agent with defaults | **Removed** — returns minimal chatbot |

### Graceful fallback

- `load_all()` catches `FileNotFoundError` — missing configs are skipped
- `build_agent()` returns minimal chatbot when no config exists
- `GET /api/agent` tells frontend whether a full agent is available
- Frontend hides tool buttons when agent is not available

### Files changed

| File | Change |
|---|---|
| `read_markdown/markdown_loader.py` | Removed defaults, simplified `ensure()`, graceful `load_all()` |
| `app/agents/chat_bot_agent.py` | Minimal chatbot fallback |
| `build/class_definition.py` | Removed `DEFAULT_MODEL`, raises error on no model |
| `server.py` | Added `GET /api/agent` endpoint |
| `static/js/api.js` | Added `loadAgent()` |
| `static/js/app.js` | Added `setupAgent()`, hides toolbox if unavailable |

---

## 2026-08-19 — Agent Definition Reorganization

**What changed:** Agent definitions moved from flat markdown to a structured format with personality, boundaries, and decision style. Skills got detailed documentation in a shared `skills/` folder. The system prompt is now composed from separate profile fields at build time.

### New file structure

```
read_markdown/
├── chat_bot_agent.md        ← THE source of truth (replaces chatbot_prompt.md + app_blueprint.md)
├── agents_index.md          ← Global index of all agents
├── skills/
│   ├── _header.md           ← Explains the skills folder format
│   ├── create_file.md       ← One detailed doc per skill
│   ├── read_file.md
│   ├── write_file.md
│   ├── create_folder.md
│   ├── setup_venv.md
│   ├── read_pdf.md
│   ├── get_current_date.md
│   └── tell_me_the_date_and_time.md
└── markdown_loader.py       ← Reads chat_bot_agent.md + skills/*.md
```

### Pipeline

```
chat_bot_agent.md  →  markdown_loader.py  →  chat_bot.json  →  chat_bot_agent.py  →  Agent
skills/*.md        →  markdown_loader.py  →  skills.json    →  (available as reference)
```

### Agent definition sections

| Section | In system prompt? | Purpose |
|---|---|---|
| `identity` | No | name, default_model, type |
| `skills` | Yes | Markdown table with skill ID, description, and docs link |
| `role` | Yes | Who the agent is |
| `purpose` | Yes | What the agent does |
| `personality` | Yes | How it behaves |
| `communication` | Yes | Communication style rules |
| `boundaries` | Yes | What it won't do |
| `principles` | Yes | Core principles |
| `decision_style` | Yes | How it makes decisions |
| `priorities` | **No** | Documentation only |

### Runtime adjustments

When the agent needs more clarity, pass `adjustments` to `build_agent()`:
```python
agent = build_agent(adjustments={
    "boundaries": profile.boundaries + "\n- Double-check all file paths.",
})
```

### Files added/removed

| Action | File |
|---|---|
| Added | `read_markdown/chat_bot_agent.md` (new format) |
| Added | `read_markdown/agents_index.md` |
| Added | `read_markdown/skills/*.md` (8 skill files + header) |
| Removed | `read_markdown/chatbot_prompt.md` |
| Removed | `read_markdown/app_blueprint.md` |
| Modified | `read_markdown/markdown_loader.py` |
| Modified | `build/class_definition.py` (AgentProfile new fields) |
| Modified | `app/agents/chat_bot_agent.py` (composes system prompt) |
| Added | `build/__init__.py` |

---

## 2026-08-15 — Initial Changes

- Added `about` directory and this markdown file.
- Created new agent soul definition `read_markdown/chat_bot_agent.md` with required sections.
- Updated `read_markdown/markdown_loader.py` to load from `chat_bot_agent.md` and generate `config/chat_bot.json`.
- Added runtime dataclasses `AgentState`, `Action`, `Observation`.
- Modified `app/agents/chat_bot_agent.py` to reference `config/chat_bot.json`.
- Updated documentation and comments throughout the codebase.
- Adjusted tool loading and configuration regeneration logic.
