from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import os

# App modules:
#   write_markdown.app_config.AppConfig -> scans LLMs into config/models.json and
#                                          regenerates write_markdown/tools.md from
#                                          app/tools/tools.py's SKILL_REGISTRY
#   read_markdown.markdown_loader.load_all -> reads read_markdown/chat_bot_agent.md +
#                                          read_markdown/skills/*.md +
#                                          write_markdown/tools.md at startup and
#                                          regenerates config/chat_bot.json +
#                                          config/skills.json + config/tools.json
#   app.agents.chat_bot_agent.run_agent -> builds a fresh Agent from
#                                          config/chat_bot.json + SKILL_REGISTRY,
#                                          replays chat history, and returns the
#                                          LLM reply for /api/chat
from contextlib import asynccontextmanager
from write_markdown.app_config import AppConfig
from read_markdown.markdown_loader import load_all
from app.agents.chat_bot_agent import run_agent

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# One shared instance, used by the startup hook below.
app_config = AppConfig()

# Startup hook: regenerate the dynamic configs BEFORE any request is served,
# so edits always take effect on restart.
# Order matters: refresh_all() writes tools.md from the SKILL_REGISTRY,
# and load_all() then turns that tools.md plus chat_bot_agent.md and
# skills/*.md into the JSON files (chat_bot.json / tools.json / skills.json).
@asynccontextmanager
async def lifespan(app: FastAPI):
    app_config.refresh_all()   # scan LLMs -> models.json; registry -> skills.json + tools.md
    load_all()                 # markdown -> agent.json / tools.json
    yield                      # serve requests; code after this runs on shutdown

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    model: str = ""
    agent: str = ""
    tool: str = ""
    history: List[dict] = []  # Prior turns from the frontend: [{role, content}, ...]

# --- UI SOURCE OF TRUTH ---

"""
GET /api/models
---------------
What this request is:
    The front-end calls this endpoint on page load to populate the model
    dropdown (#model-select). It is a simple GET request with no body.

What it needs:
    1. A file named "models.json" located in the config folder of the project
       (config/models.json, relative to server.py).
    2. The file must contain a "models" key: a list of objects shaped like
       {"id": str, "name": str}.

Behaviour:
    - If models.json exists and has models, the list is returned.
    - If the file is missing, unreadable, or contains no models, the
      endpoint returns an empty list: {"models": []}.
"""

MODELS_FILE = BASE_DIR / "config" / "models.json"

# The tool button list comes from tools.json, which the loader regenerates
# from write_markdown/tools.md (the ## tools section) at every server start.
TOOLS_FILE = BASE_DIR / "config" / "tools.json"

# The agent definition comes from chat_bot.json, generated from chat_bot_agent.md.
AGENT_FILE = BASE_DIR / "config" / "chat_bot.json"

@app.get("/api/models")
async def get_models():
    # Look for the models.json file next to server.py.
    if not MODELS_FILE.exists():
        print("[MODELS] models.json not found - returning empty list")
        return {"models": []}

    try:
        data = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("[MODELS] models.json unreadable - returning empty list")
        return {"models": []}

    models = data.get("models", [])

    if not models:
        print("[MODELS] models.json has no models - returning empty list")
        return {"models": []}

    print("json file sent: models")
    return {"models": models}

@app.get("/api/agent")
async def get_agent():
    """Return whether a full agent is available.

    The frontend checks this on page load to decide whether to show
    agent features (tool buttons, agent-specific UI) or fall back to
    a basic chatbot (no tools, no agent personality).
    """
    if not AGENT_FILE.exists():
        return {"available": False}
    try:
        data = json.loads(AGENT_FILE.read_text(encoding="utf-8"))
        if data.get("name"):
            return {"available": True, "name": data["name"], "type": data.get("type", "")}
        return {"available": False}
    except (OSError, json.JSONDecodeError):
        return {"available": False}

@app.get("/api/tools")
async def get_tools():
    """Return the tool buttons for the frontend toolbox.

    Reads config/tools.json (regenerated from write_markdown/tools.md at startup)
    so the UI tool list is editable in one markdown file.
    """
    try:
        data = json.loads(TOOLS_FILE.read_text(encoding="utf-8"))
        return {"tools": data.get("tools", [])}
    except (OSError, json.JSONDecodeError):
        print("[TOOLS] tools.json unreadable - returning empty list")
        return {"tools": []}

# --- I/O ROUTES ---

@app.post("/api/chat")
def chat(data: ChatRequest):
    """Handle a chat message from the frontend.

    The request payload carries {message, model, agent, tool}. We build a
    FRESH agent for this request (stateless - the frontend keeps its own
    conversation history), using the model the user picked in the dropdown,
    then return the agent's reply.

    NOTE: this is a SYNC endpoint (def, not async def) on purpose. The LLM
    call inside agent.think() is blocking (it waits 10-60s for Ollama to
    generate). FastAPI runs sync endpoints in a THREADPOOL, so the event loop
    stays free and two chat requests do NOT block each other. An async def
    would run the blocking LLM call on the event loop and stall the whole
    server for every reply.
    """
    print(f"[SERVER] Message from {data.model}: {data.message}")
    print(f"[SERVER] history turns received: {len(data.history)}")

    # One call in chat_bot_agent.py does it all: build a fresh agent, replay
    # the frontend's history into the conversation, and ask the LLM.
    reply = run_agent(data.message, data.history, data.model)
    print(f"[SERVER] Reply from {data.model}: {reply[:120]}...")
    

    return {"reply": reply}

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)