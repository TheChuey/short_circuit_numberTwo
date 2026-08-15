from dataclasses import dataclass  # A decorator that writes class boilerplate (init/repr/etc.).
from typing import Any, Callable, List  # Reusable type hints for the Agent classes below.

import json
from pathlib import Path

import ollama 


# ==========================================================================
# CATEGORY 1 - CONFIGURATION: THE AGENT'S "SOUL" AND ENGINE SETUP
# --------------------------------------------------------------------------
# The three pieces every agent needs before it can run:
#   - AgentProfile  -> the character (name + system prompt). Built from
#                      config/agent.json (composed from read_markdown/
#                      app_blueprint.md) in app/agents/chat_bot_agent.py
#                      build_agent(); read by Agent.think() to seed the chat.
#   - LLMClient     -> adapter between the generic Agent API
#                      (llm.chat(messages)) and the project's plain-text
#                      ask_llm() backend. Its backend is INJECTED at
#                      construction (built in build_agent() with the model
#                      picked from models.json); the class itself never
#                      reaches for a module global.
#   - ask_llm       -> the real LLM backend LLMClient talks to. It is created
#                      by build/composition.py (the composition root) and
#                      handed to LLMClient via its `backend` argument.
# How it fits together:  POST /api/chat (server.py) -> build_agent()
# (app/agents/chat_bot_agent.py) -> Agent.think() -> LLMClient.chat() ->
# backend(prompt). Nothing is hard-coded here: the character, tools and LLM
# are passed in when the Agent object is created (instantiated).
# ==========================================================================


@dataclass
class AgentProfile:
    """The "character" of an agent: a display name plus the system prompt
    (the instructions that shape the agent's personality and behaviour)."""

    name: str  # The character's name (e.g. "PlannerAgent").
    system_prompt: str  # The "soul": the instructions the LLM should follow.


class LLMClient:
    """Adapter between the generic Agent API (llm.chat(messages)) and a
    plain-text LLM backend: (prompt, model) -> str.

    The backend is INJECTED (constructor argument) so this class is fully
    independent - it works with any callable of that shape, and never reaches
    for a module global. build/composition.py produces the real ask_llm.
    """

    def __init__(self, model: str | None = None, backend: Callable | None = None):
        self.model = model  # The LLM model name to use (from models.json).
        self.backend = backend  # The injected callable: ask_llm(prompt, model) -> str.

    def chat(
        self,
        messages: List[dict],  # The conversation history (a list of role/content dicts).
    ) -> str:
        """Flatten the conversation (system + user/assistant turns) into one
        prompt string and send it to the injected backend, which takes a
        plain string. The system prompt is always the first message (think()
        puts it there), so order is preserved as-is."""

        if self.backend is None:
            raise RuntimeError(
                "LLMClient needs a backend - wire one in via build/composition.py"
            )

        label = {"system": "System", "user": "User", "assistant": "Assistant"}
        parts = [
            f"{label.get(m.get('role', 'user'), m.get('role', 'user'))}: {m['content']}"
            for m in messages
            if isinstance(m, dict) and m.get("content")
        ]
        return self.backend("\n\n".join(parts), model=self.model)


# ==========================================================================
# CATEGORY 2 - THE GENERIC AGENT OBJECT (THINK / ACT / OBSERVE)
# --------------------------------------------------------------------------
# One standard, reusable class. The character (profile), the LLM and the
# tools are not hard-coded here - they are passed in when the object is
# created, so the same class can power any agent in the app.
# Where it is used: built by app/agents/chat_bot_agent.py build_agent()
# (which wires in an LLMClient, the agent.json skills, and an AgentProfile),
# then driven by POST /api/chat in server.py via agent.think(message).
# ==========================================================================


class Agent:
    """A generic AI agent that can think (ask the LLM), act (call a tool) and
    observe (record the tool's result back into the conversation)."""

    def __init__(self, llm: Any, tools: List[Callable], profile: AgentProfile):
        """Store the LLM, the tools and the character so the methods can use them."""
        self.llm = llm  # The LLM backend (e.g. an LLMClient instance).
        self.profile = profile  # The character (name + system prompt).
        self.tools = {f.__name__: f for f in tools}  # Tool map: function name -> function.
        self.messages: List[dict] = []  # The running conversation history.

    def think(self, user_input: str) -> str:
        """Send the conversation to the LLM and return its text reply."""
        # Guarantee the character (system prompt) is always the first message.
        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": self.profile.system_prompt})
        self.messages.append({"role": "user", "content": user_input})  # The request we are answering.
        reply = self.llm.chat(messages=self.messages)  # Ask the LLM for a reply.
        self.messages.append({"role": "assistant", "content": reply})  # Remember the reply.
        return reply  # Hand the reply back to the caller.

    def act(self, tool_call: Any) -> str:
        """Run one tool that the LLM asked for, using the name and args it chose."""
        name = tool_call.function.name  # Which tool the LLM wants to use.
        args = tool_call.function.arguments or {}  # The arguments it wants to pass.
        if name in self.tools:  # If the tool exists in our name->function map...
            return str(self.tools[name](**args))  # ...call it and return the result.
        return f"Error: {name} missing"  # Otherwise report that the tool is unavailable.

    def observe(self, name: str, result: str) -> None:
        """Record a tool's result back into the conversation history."""
        self.messages.append({"role": "tool", "content": result, "name": name})



# ==========================================================================
# CATEGORY 3 - MODEL SELECTION & THE LLM BACKEND (talking to Ollama)
# --------------------------------------------------------------------------
# Every chat turn ends up at Ollama, but "which model?" and "how big a
# context?" are separate concerns. Four small classes split that work so each
# one can be understood, tested and reused alone:
#
#   - ModelStore     the DATA SOURCE half of model selection. It only reads
#                    config/models.json and answers one question: "what is the
#                    first configured model id?" (or None). It never decides
#                    anything. No dependencies.
#
#   - ModelSelector  the DECISION half. It turns a (possibly None) model hint
#                    from the frontend into a concrete Ollama model id, using
#                    a priority chain: explicit arg > config/models.json (via
#                    the injected ModelStore) > installed Ollama models >
#                    the hardcoded MODEL. Exactly one of these always wins, so
#                    ask_llm() can never call Ollama with an empty model name.
#
#   - ModelContext   context-window sizing. Ollama's default runtime window is
#                    tiny (2048-4096 tokens) unless num_ctx is set, which
#                    truncates the conversation and yields empty replies. This
#                    class asks Ollama for the model's max context length and
#                    returns it CAPPED at MAX_NUM_CTX, so long prompts survive
#                    without blowing up the KV cache. No dependencies.
#
#   - ChatBackend    the terminal step. It orchestrates the other three on
#                    every call: selector picks the model, context sizes the
#                    window, then ollama.chat() produces the reply - retrying
#                    once if it comes back empty. Its public surface is
#                    .ask_llm(prompt, model) -> str, the plain-text backend the
#                    whole app ultimately calls.
#
# HOW THEY FIT TOGETHER: POST /api/chat (server.py) -> build_agent()
# (app/agents/chat_bot_agent.py) -> Agent.think() -> LLMClient.chat() ->
# ask_llm. The instances the app shares (and ask_llm = chat_backend.ask_llm)
# are wired in build/composition.py, the composition root - NOT here. This
# file holds only pure class definitions: each class takes its dependencies
# explicitly (e.g. ModelSelector gets its ModelStore in __init__), so nothing
# here reaches for a module global and every class works independently.
# ==========================================================================

class ModelStore:
    """Where the app's KNOWN models come from: config/models.json.

    This is the DATA SOURCE half of model selection. It never decides which
    model to use - it only answers "what's the first configured model id?".
    If the file is missing or unreadable it returns None (the selector then
    falls back to Ollama's installed list, then to the hardcoded MODEL).

    No dependencies; safe for any agent to share.
    """

    # models.json lives at the backend root, next to the config/ folder that
    # holds it. (This corrects the old llm_tool.py bug, which pointed at a
    # non-existent app/server/config/models.json.)
    CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

    def _models_json_path(self) -> Path:
        """Return the path to config/models.json (kept fresh by AppConfig)."""
        return self.CONFIG_DIR / "models.json"

    def config_model(self) -> str | None:
        """Return the first model id from config/models.json; None if none.

        Used by ModelSelector as priority #2 in its chain (it is the only
        caller today).
        """
        try:
            data = json.loads(self._models_json_path().read_text(encoding="utf-8"))
            models = data.get("models", [])
            if models:
                return models[0].get("id")
        except (OSError, json.JSONDecodeError):
            pass
        return None


class ModelSelector:
    """Decides WHICH model id will handle a request.

    WHEN IT RUNS: exactly once per chat turn. It is the FIRST thing
    ChatBackend.ask_llm() does on every POST /api/chat:
        selector._resolve_model(model)
    The frontend's chosen model reaches it via server.py -> run_agent() ->
    build_agent() -> LLMClient -> ask_llm(model=...); this class turns that
    (possibly None) value into a concrete Ollama model id.

    How it picks (first match wins):
        1. the explicit model argument (frontend dropdown) - the usual case
        2. the first id in config/models.json (via the injected ModelStore)
        3. a fallback MODEL if it is installed in Ollama
        4. the first installed Ollama model
        5. finally, the hardcoded MODEL ("llama3.1")

    Depends on: a ModelStore (for priority #2). Shared by all agents.
    """

    # Hardcoded fallback model, used only when models.json and Ollama both fail.
    MODEL = "llama3.1"

    def __init__(self, model_store: ModelStore):
        self.model_store: ModelStore = model_store

    def _resolve_model(self, model: str | None = None) -> str:
        """Pick which model to use: explicit arg > config > Ollama list > MODEL."""
        # Priority 1: the caller passed an explicit model (frontend dropdown).
        if model:
            print(f"[tools.ask_llm] explicit model used: {model}")
            return model

        # Priority 2: the first configured model in config/models.json.
        cfg = self.model_store.config_model()
        if cfg:
            print(f"[tools.ask_llm] model from config/models.json: {cfg}")
            return cfg

        # Priorities 3-4: consult Ollama's installed models directly.
        try:
            data = ollama.list()
            names = [
                m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
                for m in data.get("models", [])
            ]
            names = [n for n in names if n]
            if self.MODEL in names:
                print(f"[tools.ask_llm] fallback MODEL found in Ollama: {self.MODEL}")
                return self.MODEL
            if names:
                print(f"[tools.ask_llm] first installed Ollama model: {names[0]}")
                return names[0]
        except Exception as exc:
            print(f"[tools.ask_llm] Ollama list failed: {exc}")

        # Priority 5: last resort, the hardcoded MODEL.
        print(f"[tools.ask_llm] last-resort MODEL: {self.MODEL}")
        return self.MODEL


class ModelContext:
    """How big is this model's context window (capped)? Feeds num_ctx.

    Ollama's default runtime window is 2048-4096 tokens unless num_ctx is set.
    The app re-sends the whole conversation every turn, so a tiny window makes
    the model truncate the prompt and return empty replies. We raise num_ctx
    per request to (at most) MAX_NUM_CTX to fit the full conversation.

    No dependencies; shared by all agents.
    """

    # Upper cap for the per-request context window (num_ctx). The model itself
    # may support much more (e.g. 131072), but a huge window costs GPU memory
    # for the KV cache, and a 5B local model rarely needs more than this.
    MAX_NUM_CTX = 32768

    def _context_window(self, model: str) -> int | None:
        """Return the model's max context length from Ollama, capped; None if unknown."""
        try:
            info = ollama.show(model=model).model_dump()
            model_info = info.get("modelinfo") or info.get("model_info") or {}
            length = model_info.get("llama.context_length")
            if not length:
                return None
            return min(int(length), self.MAX_NUM_CTX)
        except Exception as exc:
            print(f"[tools.ask_llm] context lookup failed for {model}: {exc}")
            return None


class ChatBackend:
    """The terminal step: actually talk to the LLM and return plain text.

    Orchestrates the other classes - this is WHEN each of them is used, on
    every call:
        1. selector._resolve_model(model)   -> the winning model id
        2. context._context_window(id)      -> safe num_ctx (capped)
        3. ollama.chat(model=id, options={num_ctx})  -> the reply

    Guards against silent failures:
        - num_ctx is raised to the model's (capped) window so long prompts are
          NOT truncated by Ollama's small default context.
        - empty replies are retried once; if the model still emits nothing, a
          readable fallback is returned instead of a blank string (a blank
          reply would be stored in the chat and confuse the next turn).

    Depends on: a ModelSelector and a ModelContext. Shared by all agents.
    """

    def __init__(self, selector: ModelSelector, context: ModelContext):
        self.selector: ModelSelector = selector
        self.context: ModelContext = context

    def ask_llm(self, prompt: str, model: str | None = None) -> str:
        """Send a prompt to the resolved model via Ollama and return its reply."""
        # Step 1: ask the selector which model id wins for this request.
        resolved = self.selector._resolve_model(model)

        # Step 2: ask the context helper for a safe num_ctx for that model.
        num_ctx = self.context._context_window(resolved)
        options = {"num_ctx": num_ctx} if num_ctx else {}
        print(f"[tools.ask_llm] calling ollama.chat with model={resolved} num_ctx={num_ctx}")

        # Step 3: make the call, retrying once if the reply comes back empty.
        for attempt in (1, 2):
            response = ollama.chat(
                model=resolved,
                messages=[{"role": "user", "content": prompt}],
                options=options,
            )
            reply = response["message"]["content"]
            print(f"[tools.ask_llm] reply received ({len(reply)} chars)")
            if reply.strip():
                return reply
            print(f"[tools.ask_llm] empty reply on attempt {attempt} - retrying")
        return "(The model returned an empty reply. Please try again.)"

