"""
build/class_definition.py
=========================

Runtime classes for the agent system.

This module contains:
    Agent       — the generic agent that thinks, acts, and observes
    ask_llm     — the LLM backend (talks to Ollama)

AgentProfile lives in app/agents/class_library.py.
"""

import json
from pathlib import Path
from typing import Callable, List

import ollama

from app.agents.class_library import AgentProfile


# ==========================================================================
# THE GENERIC AGENT OBJECT
# --------------------------------------------------------------------------
# The Agent class maintains conversation history and provides the `think`
# method to interact with the LLM backend natively using structured messages.
# ==========================================================================

class Agent:
    """A generic AI agent that can think (ask the LLM), act (call a tool) and
    observe (record the tool's result back into the conversation)."""

    def __init__(self, model: str | None, tools: List[Callable], profile: AgentProfile):
        """Store the model, tools, and character to use during conversations."""
        self.model = model
        self.profile = profile
        self.tools = {f.__name__: f for f in tools}
        self.messages: List[dict] = []

    def think(self, user_input: str) -> str:
        """Add user input to history, send the conversation to the LLM, and return its reply."""
        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": self.profile.system_prompt})

        self.messages.append({"role": "user", "content": user_input})

        tool_callables = list(self.tools.values()) if self.tools else None

        message = ask_llm(messages=self.messages, model=self.model, tools=tool_callables)
        self.messages.append(message)

        if message.get("tool_calls"):
            print(f"[Agent.think] LLM requested {len(message['tool_calls'])} tool calls.")
            for tool_call in message["tool_calls"]:
                result = self.act(tool_call)
                self.observe(tool_call["function"]["name"], result)

            message = ask_llm(messages=self.messages, model=self.model, tools=tool_callables)
            self.messages.append(message)

        return message.get("content", "")

    def act(self, tool_call: dict) -> str:
        """Run one tool that the LLM asked for, using the name and args it chose."""
        name = tool_call.get("function", {}).get("name")
        args = tool_call.get("function", {}).get("arguments", {})
        if name in self.tools:
            try:
                result = str(self.tools[name](**args))
                print(f"[Agent.act] Executed {name} -> {result[:100]}...")
                return result
            except Exception as e:
                print(f"[Agent.act] Error executing {name}: {e}")
                return f"Error executing tool: {e}"
        print(f"[Agent.act] Missing tool requested: {name}")
        return f"Error: {name} missing"

    def observe(self, name: str, result: str) -> None:
        """Record a tool's result back into the conversation history."""
        self.messages.append({"role": "tool", "content": result, "name": name})


# ==========================================================================
# THE LLM BACKEND (talking to Ollama)
# --------------------------------------------------------------------------
# Model resolution, context sizing, and calling the Ollama API.
# ==========================================================================

MAX_NUM_CTX = 32768
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _resolve_model(model: str | None) -> str:
    """Pick which model to use: explicit arg > config > Ollama list."""
    if model:
        print(f"[ask_llm] explicit model used: {model}")
        return model

    try:
        data = json.loads((CONFIG_DIR / "models.json").read_text(encoding="utf-8"))
        models = data.get("models", [])
        if models:
            cfg = models[0].get("id")
            if cfg:
                print(f"[ask_llm] model from config/models.json: {cfg}")
                return cfg
    except (OSError, json.JSONDecodeError):
        pass

    try:
        data = ollama.list()
        names = [
            m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
            for m in data.get("models", [])
        ]
        names = [n for n in names if n]
        if names:
            print(f"[ask_llm] first installed Ollama model: {names[0]}")
            return names[0]
    except Exception as exc:
        print(f"[ask_llm] Ollama list failed: {exc}")

    raise RuntimeError(
        "No model available. Specify one in the frontend, "
        "add models to config/models.json, or install one in Ollama."
    )


def _get_context_window(model: str) -> int | None:
    """Return the model's max context length from Ollama, capped; None if unknown."""
    try:
        info = ollama.show(model=model).model_dump()
        model_info = info.get("modelinfo") or info.get("model_info") or {}
        length = model_info.get("llama.context_length")
        if not length:
            return None
        return min(int(length), MAX_NUM_CTX)
    except Exception as exc:
        print(f"[ask_llm] context lookup failed for {model}: {exc}")
        return None


def ask_llm(messages: List[dict], model: str | None = None, tools: List[Callable] | None = None) -> dict:
    """Send structured messages to the resolved model via Ollama and return the full message dict."""
    resolved = _resolve_model(model)
    num_ctx = _get_context_window(resolved)

    options = {"num_ctx": num_ctx} if num_ctx else {}
    print(f"[ask_llm] calling ollama.chat with model={resolved} num_ctx={num_ctx} tools={len(tools) if tools else 0}")

    for attempt in (1, 2):
        kwargs = {
            "model": resolved,
            "messages": messages,
            "options": options,
        }
        if tools:
            kwargs["tools"] = tools

        response = ollama.chat(**kwargs)
        message = response["message"]

        content = message.get("content", "") or ""
        tool_calls = message.get("tool_calls") or []

        print(f"[ask_llm] reply received ({len(content)} chars, {len(tool_calls)} tool calls)")

        if content.strip() or tool_calls:
            return message

        print(f"[ask_llm] empty reply on attempt {attempt} - retrying")

    return {"role": "assistant", "content": "(The model returned an empty reply. Please try again.)"}
