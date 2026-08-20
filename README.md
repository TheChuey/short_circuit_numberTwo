# short_circuit_2 — AI Studio (Version 2)

Single-process web app: **FastAPI** backend + vanilla JS frontend, talking to a **local Ollama** LLM.
This is **version two** of the project, named `short_circuit_2`.

## Quickstart (Windows PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

Open **http://127.0.0.1:8000** (Chrome/Edge). Override port: `$env:PORT=9000; python server.py`.

## 1) Folder structure, module imports & exports (for AI readers)

```
short_circuit_2/
├── server.py                 # FastAPI entry point — the ONLY thing the browser talks to
├── read_markdown/            # READ side of the markdown pipeline (markdown -> JSON configs)
│   ├── markdown_loader.py    # class MarkdownLoader + load_all() + build_skills_from_folder()
│   ├── chat_bot_agent.md     # THE source of truth for the agent (identity + personality + skills)
│   ├── agents_index.md       # Global index of all agents
│   ├── skills/               # Detailed skill documentation (shared across agents)
│   │   ├── _header.md        # Explains the skills folder format
│   │   ├── create_file.md    # One file per skill
│   │   ├── read_file.md
│   │   ├── write_file.md
│   │   ├── create_folder.md
│   │   ├── setup_venv.md
│   │   ├── read_pdf.md
│   │   ├── get_current_date.md
│   │   └── tell_me_the_date_and_time.md
│   └── __init__.py
├── write_markdown/           # WRITE side of the markdown pipeline (code -> markdown/JSON)
│   ├── app_config.py         # class AppConfig: refresh_tools_md() -> tools.md; refresh_models() -> models.json
│   ├── tools.md              # AUTO-GENERATED from tools.py by AppConfig; read by markdown_loader -> tools.json
│   └── __init__.py
├── config/                   # GENERATED JSON configs (produced by the pipeline)
│   ├── models.json           # {"models": [...]} — written by AppConfig.refresh_models()
│   ├── chat_bot.json         # GENERATED from chat_bot_agent.md: {name, role, personality, boundaries, skills, ...}
│   ├── skills.json           # GENERATED from skills/*.md: detailed skill documentation per skill
│   ├── tools.json            # GENERATED from write_markdown/tools.json: {"tools": [{id, name, icon, enabled}]}
│   └── __init__.py
├── static/                   # frontend served by FastAPI
│   ├── index.html
│   ├── styles.css
│   └── js/
│       ├── app.js            # entry: imports loadModels/loadTools/sendMessage from ./api.js
│       └── api.js            # exports the 3 fetch wrappers (GET /api/models, GET /api/tools, POST /api/chat)
├── app/
│   ├── agents/
│   │   └── chat_bot_agent.py # build_agent(model) -> Agent; composes system_prompt from profile fields
│   └── tools/
│       └── tools.py          # MASTER: tool functions + SKILL_REGISTRY (skill name -> function)
├── build/
│   ├── __init__.py
│   └── class_definition.py   # AgentProfile + Agent + ask_llm()
├── about/
│   └── short_circuit_2.md    # Project changelog
└── docs/
```

Import graph (who imports whom):

| Module | Imports |
|---|---|
| `server.py` | `write_markdown.app_config.AppConfig`, `read_markdown.markdown_loader.load_all`, `app.agents.chat_bot_agent.run_agent` |
| `write_markdown/app_config.py` | `app.tools.tools.SKILL_REGISTRY` |
| `read_markdown/markdown_loader.py` | stdlib only |
| `app/agents/chat_bot_agent.py` | `build.class_definition.{Agent, AgentProfile}`, `app.tools.tools.SKILL_REGISTRY` |
| `app/tools/tools.py` | `build.class_definition.ask_llm` |
| `build/class_definition.py` | `ollama` |

Public exports:
- `read_markdown/markdown_loader.py`: `load_all()`, `build_skills_from_folder()`
- `app/agents/chat_bot_agent.py`: `build_agent(model=None, adjustments=None)`, `run_agent(message, history, model, adjustments)`
- `build/class_definition.py`: `AgentProfile`, `Agent`
- `write_markdown/app_config.py`: class `AppConfig` with `refresh_all()`

## 2) Server ↔ JavaScript fetch map

| JS caller | fetch | Server route (server.py) | What the server does |
|---|---|---|---|
| page load | `GET /` | `home()` | serves `static/index.html` |
| browser | `GET /static/*` | StaticFiles mount | serves css/js |
| `setupModels()` → `loadModels()` | `GET /api/models` | `get_models()` | reads `config/models.json`, returns `{"models": [...]}` |
| `setupTools()` → `loadTools()` | `GET /api/tools` | `get_tools()` | reads `config/tools.json`, returns the tool buttons |
| `send()` → `sendMessage(payload)` | `POST /api/chat` | `chat(data)` | builds a fresh agent via `run_agent()` and returns its LLM reply |

## 3) Data flow

### Markdown → JSON → Agent pipeline

```
chat_bot_agent.md  →  markdown_loader.py  →  chat_bot.json  →  chat_bot_agent.py  →  Agent
skills/*.md        →  markdown_loader.py  →  skills.json    →  (available as reference)
write_markdown/tools.md  →  markdown_loader.py  →  tools.json  →  GET /api/tools
```

### Startup sequence

```
server.py lifespan
  ├─ AppConfig.refresh_all()          (write_markdown/app_config.py)
  │    ├─ scan_models()               -> config/models.json
  │    └─ refresh_tools_md()          -> write_markdown/tools.md
  └─ load_all()                       (read_markdown/markdown_loader.py)
       ├─ AGENT_LOADER.load()         -> config/chat_bot.json    (from chat_bot_agent.md)
       ├─ TOOLS_LOADER.load()         -> config/tools.json       (from write_markdown/tools.md)
       └─ build_skills_from_folder()  -> config/skills.json      (from read_markdown/skills/*.md)
```

### Agent definition sections → system prompt

| Section | In system prompt? | Purpose |
|---|---|---|
| `identity` | No | Machine metadata (name, model, type) |
| `skills` | Yes (brief table) | Agent knows what tools it has |
| `role` | Yes | Who the agent is |
| `purpose` | Yes | What the agent does |
| `personality` | Yes | How it behaves |
| `communication` | Yes | Communication style rules |
| `boundaries` | Yes | What it won't do |
| `principles` | Yes | Core principles |
| `decision_style` | Yes | How it makes decisions |
| `priorities` | **No** | Documentation only |

### Runtime adjustments

When the agent needs more clarity or adjustment, pass `adjustments` to `build_agent()`:
```python
agent = build_agent(adjustments={
    "boundaries": profile.boundaries + "\n- Double-check all file paths before writing.",
    "communication": profile.communication + "\n- Explain each step before executing it.",
})
```

## 4) How to modify config

1. Edit `read_markdown/chat_bot_agent.md` (identity, role, personality, boundaries, skills table).
2. To add detailed skill docs, create `read_markdown/skills/{skill_id}.md`.
3. Restart the server — the lifespan event regenerates everything.
4. To add a new skill: define the function in `app/tools/tools.py`, register in `SKILL_REGISTRY`, add to the agent's `## skills` table, create a detail file in `skills/`.

## 5) CHANGELOG — 2026-08-19 (agent definition reorganization)

**What changed, in one line:** agent definitions moved from flat markdown to a structured format with personality, boundaries, and decision style; skills got detailed documentation in a shared `skills/` folder; the system prompt is now composed from separate profile fields at build time.

### 5.1) New agent definition format

`read_markdown/chat_bot_agent.md` is now the single source of truth per agent (replaces `chatbot_prompt.md` and `app_blueprint.md`). Sections:

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

### 5.2) Skills documentation

- `read_markdown/skills/` — shared folder with one `.md` per skill
- Each file documents: Purpose, When to Use, Parameters, Example, Related Skills
- Parsed at startup into `config/skills.json` by `build_skills_from_folder()`
- `_header.md` explains the folder format (skipped during parsing)

### 5.3) System prompt composition

- `markdown_loader.py` writes sections as separate fields to `chat_bot.json`
- `chat_bot_agent.py` composes the final system prompt from profile fields at build time
- `priorities` is excluded from the prompt (documentation only)
- Runtime `adjustments` parameter allows modifying any field before composition

### 5.4) Files added/removed

| Action | File |
|---|---|
| Added | `read_markdown/chat_bot_agent.md` (new format) |
| Added | `read_markdown/agents_index.md` |
| Added | `read_markdown/skills/*.md` (8 skill files + header) |
| Removed | `read_markdown/chatbot_prompt.md` |
| Removed | `read_markdown/app_blueprint.md` |
| Modified | `read_markdown/markdown_loader.py` (reads chat_bot_agent.md, parses skills folder) |
| Modified | `build/class_definition.py` (AgentProfile has new fields) |
| Modified | `app/agents/chat_bot_agent.py` (composes system prompt, supports adjustments) |
| Added | `build/__init__.py` |

### 5.5) Generated config shapes

**`config/chat_bot.json`:**
```json
{
  "name": "AI Agent Development Assistant",
  "default_model": "gemma4:e2b",
  "type": "Chatbot",
  "skills": ["create_file", "read_file", ...],
  "skills_table": [{"id": "create_file", "description": "...", "docs": "skills/create_file.md"}],
  "role": "...",
  "purpose": "...",
  "personality": "...",
  "communication": "...",
  "boundaries": "...",
  "principles": "...",
  "decision_style": "...",
  "priorities": "...",
  "system_prompt": ""
}
```

**`config/skills.json`:**
```json
{
  "skills": [
    {
      "id": "create_file",
      "name": "create_file",
      "function": "create_file",
      "purpose": "Creates a new file with optional initial content.",
      "when_to_use": ["Creating new source files", ...],
      "parameters": [{"name": "file_path", "type": "string", "required": true, "description": "..."}],
      "example": "...",
      "related_skills": ["write_file", "create_folder"]
    }
  ]
}
```

## 6) CHANGELOG — 2026-08-19 (safety net removal + graceful fallback)

**What changed, in one line:** removed all hardcoded default agent/tool/model templates; if a config file is missing, the server falls back to a minimal chatbot (no tools, basic prompt) and the frontend shows a simplified UI.

### 6.1) What was removed

| What | Before | After |
|---|---|---|
| `DEFAULT_AGENT_DEFINITION` in markdown_loader.py | Hardcoded fallback template | **Removed** — raises `FileNotFoundError` |
| `DEFAULT_TOOLS_BLUEPRINT` in markdown_loader.py | Hardcoded fallback template | **Removed** — raises `FileNotFoundError` |
| `DEFAULT_MODEL = "llama3.1"` in class_definition.py | Hardcoded model string | **Removed** — raises `RuntimeError` if no model |
| `build_agent()` try/except block | Returns agent with defaults on error | **Removed** — returns minimal chatbot |
| `_resolve_model()` DEFAULT_MODEL check | Checks if "llama3.1" in Ollama list | **Removed** — fails loudly |

### 6.2) Graceful fallback behavior

| Scenario | Backend | Frontend |
|---|---|---|
| `chat_bot_agent.md` missing | `load_all()` catches `FileNotFoundError`, skips agent config | `GET /api/agent` returns `{available: false}` |
| `tools.md` missing | `load_all()` catches `FileNotFoundError`, skips tools config | Toolbox hidden |
| `chat_bot.json` missing at chat time | `build_agent()` returns minimal chatbot (no tools, basic prompt) | Tool buttons hidden |
| No model configured anywhere | `_resolve_model()` raises `RuntimeError` | Error shown in chat |

### 6.3) New endpoint

`GET /api/agent` — returns agent availability info:
```json
{"available": true, "name": "AI Agent Development Assistant", "type": "Chatbot"}
// or when missing:
{"available": false}
```

### 6.4) Files changed

| File | Change |
|---|---|
| `read_markdown/markdown_loader.py` | Removed `DEFAULT_AGENT_DEFINITION`, `DEFAULT_TOOLS_BLUEPRINT`; `ensure()` raises `FileNotFoundError`; `load_all()` catches exceptions gracefully |
| `app/agents/chat_bot_agent.py` | Removed try/except defaults; added minimal chatbot fallback when no config |
| `build/class_definition.py` | Removed `DEFAULT_MODEL`; `_resolve_model()` raises `RuntimeError` if no model |
| `server.py` | Added `GET /api/agent` endpoint |
| `static/js/api.js` | Added `loadAgent()` export |
| `static/js/app.js` | Added `setupAgent()`, checks agent availability on init, hides toolbox if unavailable |
