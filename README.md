# short_circuit_1 — AI Studio (Version 1)

Single-process web app: **FastAPI** backend + vanilla JS frontend, talking to a **local Ollama** LLM.
This is **version one** of the project, named `short_circuit_1`.

## Quickstart (Windows PowerShell)

```powershell
cd application/backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

Open **http://127.0.0.1:8000** (Chrome/Edge). Override port: `$env:PORT=9000; python server.py`.

## 1) Folder structure, module imports & exports (for AI readers)

```
application/backend/
├── server.py                 # FastAPI entry point — the ONLY thing the browser talks to
├── requirements.txt
├── read_markdown/            # READ side of the markdown pipeline (markdown -> JSON configs)
│   ├── markdown_loader.py    # class MarkdownLoader + load_all(); app_blueprint.md -> agent.json, tools.md -> tools.json
│   ├── app_blueprint.md      # source of truth: agent + role + user + job sections (READ -> config/agent.json)
│   ├── chatbot_prompt.md     # plain documentation only (no parser; kept for reference)
│   └── __init__.py
├── write_markdown/           # WRITE side of the markdown pipeline (code -> markdown/JSON)
│   ├── app_config.py         # class AppConfig: refresh_tools_md() -> tools.md; refresh_skills_json() -> skills.json; refresh_models() -> models.json (from SKILL_REGISTRY)
│   ├── tools.md              # AUTO-GENERATED from tools.py by AppConfig; read back by markdown_loader -> tools.json
│   └── __init__.py
├── config/                   # GENERATED JSON configs (produced by the pipeline)
│   ├── models.json           # data store: {"models": [...]} — written by AppConfig.refresh_models()
│   ├── agent.json            # GENERATED from read_markdown/app_blueprint.md: {name, system_prompt, skills, default_model}
│   ├── skills.json           # GENERATED from tools.py SKILL_REGISTRY by AppConfig: {"skills": [{id, name, function}]}
│   ├── tools.json            # GENERATED from write_markdown/tools.md: {"tools": [{id, name, icon, enabled}]}
│   └── __init__.py
├── static/                   # frontend served by FastAPI
│   ├── index.html            # loads ONLY /static/js/app.js
│   ├── styles.css
│   └── js/
│       ├── app.js            # entry: imports loadModels/loadTools/sendMessage from ./api.js
│       ├── api.js            # exports the 3 fetch wrappers (GET /api/models, GET /api/tools, POST /api/chat)
│       └── ui.js             # UNUSED — exports never imported by app.js
├── app/
│   ├── agents/
│   │   ├── chat_bot_agent.py # build_agent(model) -> Agent; imports SKILL_REGISTRY from app/tools/tools.py
│   │   └── class_library.py  # EMPTY file
│   ├── task/
│   │   └── token_counter.py  # class TokenCounter — UNUSED
│   └── tools/
│       └── tools.py          # MASTER: get_current_date(), ask_llm() + SKILL_REGISTRY (skill name -> function)
├── build/
│   └── class_definition.py   # single source of truth: AgentProfile + LLMClient + Agent
├── docs/                     # EMPTY (older README referenced a missing docs/log_update_AIprompt.md)
└── notes/                    # offline PDF (not code)
```

Import graph (who imports whom):

| Module | Imports |
|---|---|
| `server.py` | `write_markdown.app_config.AppConfig`, `read_markdown.markdown_loader.load_all`, `app.agents.chat_bot_agent.build_agent` |
| `write_markdown/app_config.py` | `app.tools.tools.SKILL_REGISTRY` |
| `read_markdown/markdown_loader.py` | stdlib only |
| `app/agents/chat_bot_agent.py` | `build.class_definition.{Agent, AgentProfile, LLMClient}`, `app.tools.tools.SKILL_REGISTRY` |
| `app/tools/tools.py` | `ollama` |
| `build/class_definition.py` | `app.tools.tools.{get_current_date, ask_llm}` |

Public exports:
- `api.js`: `loadModels()`, `loadTools()`, `sendMessage(payload)`
- `write_markdown/app_config.py`: class `AppConfig` with `scan_models()`, `refresh_models()`, `list_registered_tools()`, `refresh_skills_json()`, `refresh_tools_md()`, `refresh_all()`
- `read_markdown/markdown_loader.py`: `load_all()`
- `app/agents/chat_bot_agent.py`: `build_agent(model=None)`
- `build/class_definition.py`: `AgentProfile`, `LLMClient(model)`, `Agent(llm, tools, profile)`

## 2) Server ↔ JavaScript fetch map & what is NOT used

| JS caller | fetch | Server route (server.py) | What the server does |
|---|---|---|---|
| page load | `GET /` | `home()` | serves `static/index.html` |
| browser | `GET /static/*` | StaticFiles mount | serves css/js |
| `setupModels()` → `loadModels()` | `GET /api/models` | `get_models()` | reads `config/models.json`, returns `{"models": [...]}` |
| `setupTools()` → `loadTools()` | `GET /api/tools` | `get_tools()` | reads `config/tools.json` (built from the auto-generated `write_markdown/tools.md`), returns the registry tools |
| `send()` → `sendMessage(payload)` | `POST /api/chat` | `chat(data)` | builds a fresh agent (`build_agent(model=data.model)`) and returns its real LLM reply |

`send()` payload = `{message, model, agent, tool}` — only `model` and `message` are used by the server.

NOT used (dead code, safe for an AI to ignore):
- **Python**: `app/task/token_counter.py`, `app/agents/class_library.py` (empty).
- **JS**: `static/js/ui.js` (its 3 exports are never imported).
- **UI controls**: `#research-btn`, `#code-btn`, `#file-loader` only log to console — no backend endpoint behind them.

## 3) Data & version

**Version:** one (repo root: `short_circuit_1`; app lives in `application/backend`).

**`config/models.json` shape (written by `AppConfig.refresh_models()`):**
```json
{
  "models": [ {"id": "gemma4:e2b", "name": "gemma4:e2b", "source": "ollama", "size": 7162405886} ]
}
```
- `models` — live models found by `AppConfig.scan_models()` (Ollama + LM Studio). The file is only rewritten when the scan finds models; an empty scan keeps the last known good file.

**Chat files:** the frontend saves each chat to a `.txt` via the File System Access API (Chrome/Edge only); chat metadata lives in localStorage + IndexedDB file handles. None of this is stored by the backend.

---

## 4) CHANGELOG — 2026-08-14 11:46 PDT (UTC-07:00)

**What changed, in one line:** config now flows from ONE editable markdown file
(`read_markdown/app_blueprint.md`) into three generated JSON files, the tool endpoint
reads from config instead of a hardcoded list, and `/api/chat` now calls the
real chatbot agent (with the configured system prompt) instead of echoing.

### 4.1) New config architecture (markdown → JSON)

```
read_markdown/app_blueprint.md  --(read_markdown/markdown_loader.py::load_all)-->
        config/agent.json    {name, system_prompt, skills[] (per-agent list), default_model}
        write_markdown/tools.md  --(markdown_loader)--> config/tools.json  {"tools": [{id, name, icon, enabled}]}

app/tools/tools.py (SKILL_REGISTRY)  --(write_markdown/app_config.py::refresh_all)-->
        config/skills.json   {"skills": [{id, name, function, description}]}   (catalog / test point)
        write_markdown/tools.md  (auto-generated tools list)
config/models.json           written by AppConfig.refresh_models() (scans LLMs)
```

- **`read_markdown/app_blueprint.md`** — the single source of truth. Sections:
  `## agent` (name, default_model, comma-separated `skills` list), `## role`
  (who the agent is), `## user` (knowledge of the user), `## job` (job
  description). The three free-text sections are stored raw in `agent.json`
  AND composed into the final `system_prompt` (ROLE / ABOUT THE USER /
  JOB DESCRIPTION headers). A top-of-file MAP lists which modules/functions
  read this file and which JSON it produces. If this file is deleted, the
  loader recreates it from its default template on next start.
- **`read_markdown/markdown_loader.py`** (new) — stdlib parser. `load_all()`:
  1) `ensure_blueprint()` creates the markdown if missing, 2) parses it,
  3) writes the three JSON files. Run standalone: `python read_markdown/markdown_loader.py`.
- **`config/agent.json` / `skills.json` / `tools.json`** (new, generated) —
  machine-readable outputs; regenerated at EVERY server start.
- **`config/models.json`** — unchanged; the loader does NOT touch the model list.

### 4.2) Endpoint changes

| Endpoint | Before | After |
|---|---|---|
| `GET /api/models` | read `config/models.json` | unchanged |
| `GET /api/tools` | hardcoded `save/cut/paste/test` list | reads `config/tools.json` (from `write_markdown/tools.md`'s `## tools` section) |
| `POST /api/chat` | echo `"AI (model) processed: ..."` | builds a FRESH `Agent` via `build_agent(model=data.model)` and returns its real reply `{"reply": ...}` |
| (startup) | none | FastAPI `lifespan` event calls `load_all()` to regenerate JSON configs before serving |

`POST /api/chat` request body is unchanged: `{message, model, agent, tool}`.
The `model` field now selects the LLM (falls back to the blueprint's
`default_model`); `agent` and `tool` are still unused by the backend.

### 4.3) New/changed variables

- **`app/agents/chat_bot_agent.py`** (rewritten):
  - `BACKEND_DIR` — sys.path bootstrap (backend root) so the script runs directly.
  - `AGENT_FILE`, `SKILLS_FILE` — paths to the generated JSON configs.
  - `SKILL_REGISTRY` — the ONLY place mapping a skill `function` name → real
    Python callable (currently `get_current_date`). Skills with an unknown
    function are skipped with a warning, not fatal.
  - `load_agent_config()`, `load_skills()`, `resolve_skills()` — config readers.
  - `build_agent(model=None)` — factory returning a stateless
    `Agent(LLMClient(model or default_model), tools, AgentProfile(name, system_prompt))`.
  - REMOVED: the old `models = SimpleNamespace(...)` double-read of models.json,
    the unused `refresh_models` import, `print(prompts)`, and the `input()` loop.
    The agent is now driven by `POST /api/chat`, not stdin.
- **`build/class_definition.py::LLMClient.chat`** — now sends the **system
  prompt + latest user message** to `ask_llm`. Previously it dropped the system
  prompt, so the configured character never reached the LLM.
- **`server.py`** — added imports `load_all` (read_markdown.markdown_loader) and
  `build_agent` (app.agents.chat_bot_agent); added `TOOLS_FILE` and the
  `lifespan` startup hook. Other env vars unchanged (`HOST`, `PORT`).

### 4.4) For AI readers — how to modify config

1. Edit `read_markdown/app_blueprint.md` (name, prompt — the role/user/job sections, and the per-agent `skills` list).
2. Restart the server (`python server.py`) — the lifespan event regenerates
   everything: `AppConfig.refresh_all()` scans models into `config/models.json` and
   regenerates `config/skills.json` + `write_markdown/tools.md` from `SKILL_REGISTRY`; `load_all()`
   builds `config/agent.json` from the blueprint and `config/tools.json` from `tools.md`.
3. To add a skill/tool: define the function in `app/tools/tools.py` and
   register it in `SKILL_REGISTRY` there — then add its id to `## agent` →
   `skills:` in `read_markdown/app_blueprint.md` if the agent should have it. `skills.json`
   and `tools.md`/`tools.json` update themselves.
4. `models.json` is generated by `AppConfig` — do not hand-edit it.

---

## 5) CHANGELOG — 2026-08-14 (refactor: loader class + consolidated tools)

**What changed, in one line:** the config loader became a reusable class, the
UI tool buttons moved to their own markdown, the six `app/tools/` modules were
consolidated into one master `tools.py`, and the `_models_json_path()` bug was
fixed.

### 5.1) Loader: functions → `MarkdownLoader` class

- `read_markdown/markdown_loader.py` now defines **`MarkdownLoader`** (class) instead
  of top-level functions. Each instance owns ONE blueprint + its JSON outputs,
  so the same parser serves two blueprints:
  - `AGENT_LOADER` → `read_markdown/app_blueprint.md` → `config/agent.json`
  - `TOOLS_LOADER` → `write_markdown/tools.md` → `config/tools.json`
- Public API preserved: **`load_all()`** still exists and returns
  `{"agent", "tools"}` — `server.py` is unchanged.
- Each loader embeds its own **default template** and recreates its blueprint
  if missing (`ensure()`).

### 5.2) Config files split

| File | Before | After |
|---|---|---|
| `read_markdown/app_blueprint.md` | `## agent`, `## system_prompt`, `## skills`, `## tools` | `## tools` section **removed** (moved out) |
| `write_markdown/tools.md` | (did not exist) | NEW — `## tools` UI buttons (save/cut/paste/test) |
| `config/tools.json` | generated from app_blueprint.md | generated from `write_markdown/tools.md` |
| `config/agent.json` / `skills.json` | — | unchanged (still from read_markdown/app_blueprint.md) |

### 5.3) Tools consolidated into `app/tools/tools.py` (master)

- **NEW `app/tools/tools.py`** holds every agent function:
  - `get_current_date()` (moved from `date_tool.py`)
  - `ask_llm()`, `_resolve_model()`, `config_model()`, `MODEL` (moved from `llm_tool.py`)
  - **`SKILL_REGISTRY`** (moved from `app/agents/chat_bot_agent.py`) — the single
    name→function lookup used by `build_agent()` and referenced by the blueprint.
- **Bug fixed:** `_models_json_path()` now points at the real
  `config/models.json` (the old `llm_tool.py` pointed at a non-existent
  `app/server/config/models.json`).
- **DELETED 6 modules:** `date_tool.py`, `llm_tool.py`, `article_tool.py`,
  `search_tool.py`, `url_tool.py`, `file_tool.py` (the last 4 were dead code).
- **Updated imports:** `build/class_definition.py` and
  `app/agents/chat_bot_agent.py` now import from `app.tools.tools`.

### 5.4) Endpoints / server

- `server.py` — **no logic change**; still calls `load_all()` in the lifespan
  hook and reads `config/tools.json` in `GET /api/tools`. Comment updated to
  point at `write_markdown/tools.md`.

### 5.5) For AI readers — how to add a skill now

1. Define the function in `app/tools/tools.py`.
2. Register it in `SKILL_REGISTRY` there.
3. Add a `### <id>` block under `## skills` in `read_markdown/app_blueprint.md` and
   append the id to `## agent` → `skills:`.
4. Restart the server; `build_agent()` picks it up automatically.

---

## 6) CHANGELOG — 2026-08-14 (simplified factory: loaders removed)

`app/agents/chat_bot_agent.py` dropped its separate CONFIG LOADERS section.

- **DELETED functions:** `_read_json`, `load_agent_config`, `load_skills`,
  `resolve_skills` — they were only used by `build_agent()`.
- **Inlined into `build_agent()`:** the factory now reads `AGENT_FILE`
  (agent.json) and `SKILLS_FILE` (skills.json) directly with try/except
  fallbacks, and resolves enabled skills to callables via `SKILL_REGISTRY`
  in a short inline loop. Same behavior, fewer layers.
- `SKILL_REGISTRY` stays in `app/tools/tools.py`; no changes to
  `server.py`, `read_markdown/markdown_loader.py`, or the JSON configs.

---

## 7) CHANGELOG — 2026-08-14 (consolidated AppConfig: models + tools in one class)

`config/model_probe.py` + `prompts/markdown_manager.py` +
`app/task/model_scanner.py` were replaced by ONE class.

### 7.1) New `write_markdown/app_config.py` — class `AppConfig`

Two jobs, ~5 public methods, no helper clutter:

| Method | Job |
|---|---|
| `scan_models()` | Ollama (`ollama.list()`) + LM Studio (HTTP) → deduped `[{id, name, source, size}]`; each source wrapped in try/except so an offline backend is skipped, never fatal |
| `refresh_models()` | `scan_models()` → write `config/models.json` (keeps the old file if the scan is empty) |
| `list_registered_tools()` | reads `SKILL_REGISTRY` from `app/tools/tools.py` → `{tool_id: docstring-first-line}` |
| `refresh_skills_json()` | writes `config/skills.json` (the skills catalog) from the registry |
| `refresh_tools_md()` | rewrites `write_markdown/tools.md` from the registry (header: AUTO-GENERATED) |
| `refresh_all()` | all of the above; returns a `{models, skills, tools}` summary |

Run standalone: `python write_markdown/app_config.py`.

### 7.2) Deletions (dead / duplicated code)

- **DELETED files:** `config/model_probe.py`, `prompts/markdown_manager.py`,
  `app/task/model_scanner.py` (logic folded into `AppConfig`).
- **REMOVED from `build/class_definition.py`:** `AgentProfile.from_prompt_pairs`,
  the `MarkdownFile` class (and its `pathlib` import) — nothing read the
  `prompt_file` key or called those at runtime.
- **`config/models.json`:** `prompt_file` key gone — the file is now just
  `{"models": [...]}`.
- **Kept on disk:** `read_markdown/chatbot_prompt.md` (plain documentation; no parser).
- **`tools.md` semantics changed:** previously hand-edited UI buttons
  (save/cut/paste/test); now AUTO-GENERATED from `SKILL_REGISTRY`, so the
  frontend toolbox lists the tools the agent can actually call
  (`GET /api/tools` now returns `get_current_date`).

### 7.3) server.py

- Lifespan now runs `app_config.refresh_all()` **then** `load_all()` — order
  matters because `markdown_loader` builds `tools.json` from the freshly
  generated `tools.md`. `models.json` is now auto-refreshed at every startup.

### 7.4) For AI readers — how the config refreshes now

```
server.py lifespan
  ├─ AppConfig.refresh_all()      (write_markdown/app_config.py)
  │    ├─ scan_models()            -> config/models.json
  │    ├─ refresh_skills_json()    -> config/skills.json
  │    └─ refresh_tools_md()       -> write_markdown/tools.md
  └─ MarkdownLoader.load_all()    (read_markdown/markdown_loader.py)
       ├─ read_markdown/app_blueprint.md  -> config/agent.json
       └─ write_markdown/tools.md         -> config/tools.json  -> GET /api/tools
```

---

## 8) CHANGELOG — 2026-08-14 (skills.json now comes from tools.py; one-line tool resolution)

### 8.1) Skills flow moved: blueprint → `SKILL_REGISTRY`

- **Before:** `config/skills.json` was generated by `markdown_loader` from the
  `## skills` section of `read_markdown/app_blueprint.md`, and `build_agent()` read it to
  build the catalog (a no-op id→function mapping).
- **After:** `skills.json` is generated by `AppConfig.refresh_skills_json()`
  from `app/tools/tools.py`'s `SKILL_REGISTRY` (the master catalog), alongside
  `tools.md`. The `## skills` section is gone from `read_markdown/app_blueprint.md` and
  `markdown_loader` no longer builds skills.json.
- **`build_agent()` step 3 is now one line:** `agent.json`'s `skills` list says
  WHICH registered tools the agent gets (per-agent selection); each id is
  looked up in `SKILL_REGISTRY`. `SKILLS_FILE` is kept in `chat_bot_agent.py`
  as a test point / for future per-agent skill detail.
- **Test point:** `skills.json` ids should always equal `SKILL_REGISTRY` keys —
  regenerate with `python write_markdown/app_config.py` to verify.

### 8.2) Files touched

- `app/agents/chat_bot_agent.py` — one-line tools resolution; comments/docs
  updated; `SKILLS_FILE` kept (unused at runtime).
- `write_markdown/app_config.py` — new `refresh_skills_json()`; `refresh_all()`
  returns `{models, skills, tools}`.
- `read_markdown/markdown_loader.py` — no longer produces skills.json; removed
  `build_skills()`, the `skills` kind, `SKILLS_FILE`, and the `## skills`
  template section.
- `read_markdown/app_blueprint.md` — `## skills` section removed (selector lives in
  `## agent → skills:`).
- `server.py` — comments updated; no logic change.

---

## 9) CHANGELOG — 2026-08-14 (markdown pipeline split into read_markdown/ + write_markdown/)

**What changed, in one line:** the markdown pipeline files were reorganized into
two folders — `read_markdown/` (markdown → JSON) and `write_markdown/` (code →
markdown/JSON) — each headed with a "what it affects" docstring. No behavior changed.

### 9.1) File moves (functionality preserved)

| Old path | New path |
|---|---|
| `config/markdown_loader.py` | `read_markdown/markdown_loader.py` |
| `config/app_blueprint.md` | `read_markdown/app_blueprint.md` |
| `prompts/chatbot_prompt.md` | `read_markdown/chatbot_prompt.md` |
| `config/app_config.py` | `write_markdown/app_config.py` |
| `app/tools/tools.md` | `write_markdown/tools.md` |
| (deleted) `prompts/` | — |

- `config/` now holds ONLY the generated JSON outputs (`agent.json`, `tools.json`,
  `skills.json`, `models.json`); `app/tools/` keeps just `tools.py`.
- **Code headers:** both moved modules open with a "WHAT THIS MODULE AFFECTS"
  block listing what they read/write and which endpoints they affect; the moved
  `.md` files note who reads/generates them.
- **Imports updated:** `server.py` now uses `write_markdown.app_config.AppConfig`
  and `read_markdown.markdown_loader.load_all` (routes/behavior unchanged).
- **Paths updated inside the moved modules** (`markdown_loader.py` blueprint/output
  paths, `app_config.py` `tools_file` → `write_markdown/tools.md`); comments in
  `tools.py`/`chat_bot_agent.py` point at the new locations.
- Standalone run commands changed to `python read_markdown/markdown_loader.py` and
  `python write_markdown/app_config.py`.

---

## 10) CHANGELOG — 2026-08-14 (blueprint: agent now has a role, user, and job)

**What changed, in one line:** `read_markdown/app_blueprint.md` was reorganized so
the agent is defined by **role**, **user knowledge**, and **job description**
(instead of one free-form `## system_prompt`), and now opens with a **MAP** that
lists every module/function/JSON file that consumes it.

### 10.1) Blueprint sections (before → after)

| `read_markdown/app_blueprint.md` | Before | After |
|---|---|---|
| Top | intro text | `## MAP — who uses this file` (modules, functions, JSON output, flow) |
| `## agent` | name, default_model, skills | unchanged |
| `## system_prompt` | one free-text blob | **removed** |
| `## role` | — | NEW — who the agent is |
| `## user` | — | NEW — knowledge of the user (from `chatbot_prompt.md`) |
| `## job` | — | NEW — what the agent does |

### 10.2) `config/agent.json` shape

- **New keys:** `role`, `user`, `job` — the raw section text (kept for
  transparency/tests).
- **`system_prompt` is now composed** by `MarkdownLoader._compose_system_prompt()`
  as `ROLE` / `ABOUT THE USER` / `JOB DESCRIPTION` (blank sections skipped).

### 10.3) Code changes

- `read_markdown/markdown_loader.py` — `build_agent()` parses the three new
  sections + composes the prompt; `DEFAULT_BLUEPRINT` updated to the new format;
  header docstring updated.
- `app/agents/chat_bot_agent.py`, `build/class_definition.py`, `server.py` — **no
  code changes**; they keep reading the composed `system_prompt` from
  `config/agent.json`.
