from dataclasses import dataclass
from typing import Any, Callable, List
import json
from pathlib import Path
import ollama

# ==========================================================================
# CATEGORY 1 - CONFIGURATION: THE AGENT'S "SOUL"
# --------------------------------------------------------------------------
# AgentProfile holds the character data: name and system prompt.
# It is used to seed the conversation history before the first LLM request.
# ==========================================================================

@dataclass
class AgentProfile:
    """The "character" of an agent: a display name plus the system prompt
    (the instructions that shape the agent's personality and behaviour)."""
    name: str
    system_prompt: str


# ==========================================================================
# CATEGORY 2 - THE GENERIC AGENT OBJECT
# --------------------------------------------------------------------------
# The Agent class maintains conversation history and provides the `think`
# method to interact with the LLM backend natively using structured messages.
# ==========================================================================

class Agent:
    """A generic AI agent that can think (ask the LLM), act (call a tool) and
    observe (record the tool's result back into the conversation)."""

    def __init__(self, model: str | None, tools: List[Callable], profile: AgentProfile):
        """Store the model, tools, and character to use during conversations."""
        self.model = model  # The model id to use (e.g., 'llama3.1')
        self.profile = profile  # The character (name + system prompt).
        self.tools = {f.__name__: f for f in tools}  # Tool map: function name -> function.
        self.messages: List[dict] = []  # The running conversation history.

    def think(self, user_input: str) -> str:
        """Add user input to history, send the conversation to the LLM, and return its reply."""
        # Guarantee the character (system prompt) is always the first message.
        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": self.profile.system_prompt})
            
        self.messages.append({"role": "user", "content": user_input})  # The request we are answering.
        
        # We need the list of Callables to pass to Ollama
        tool_callables = list(self.tools.values()) if self.tools else None

        message = ask_llm(messages=self.messages, model=self.model, tools=tool_callables)  # Ask the LLM for a reply.
        self.messages.append(message)  # Remember the reply (including any tool calls).

        if message.get("tool_calls"):
            print(f"[Agent.think] LLM requested {len(message['tool_calls'])} tool calls.")
            # Execute each requested tool
            for tool_call in message["tool_calls"]:
                result = self.act(tool_call)
                self.observe(tool_call["function"]["name"], result)
            
            # Send the results back to the LLM so it can formulate a final answer
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
# CATEGORY 3 - THE LLM BACKEND (talking to Ollama)
# --------------------------------------------------------------------------
# A simplified, cohesive backend function that handles model resolution, 
# context sizing, and calling the Ollama API with structured messages.
# ==========================================================================

# Hardcoded fallback model used if the frontend didn't specify one, 
# config/models.json has no models, and Ollama has no installed models.
DEFAULT_MODEL = "llama3.1"
MAX_NUM_CTX = 32768  # Max safe context window limit to preserve GPU memory
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

def _resolve_model(model: str | None) -> str:
    """Pick which model to use: explicit arg > config > Ollama list > default."""
    if model:
        print(f"[ask_llm] explicit model used: {model}")
        return model

    # Try config/models.json
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

    # Try Ollama installed list
    try:
        data = ollama.list()
        names = [
            m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
            for m in data.get("models", [])
        ]
        names = [n for n in names if n]
        if DEFAULT_MODEL in names:
            print(f"[ask_llm] fallback default found in Ollama: {DEFAULT_MODEL}")
            return DEFAULT_MODEL
        if names:
            print(f"[ask_llm] first installed Ollama model: {names[0]}")
            return names[0]
    except Exception as exc:
        print(f"[ask_llm] Ollama list failed: {exc}")

    # Ultimate fallback
    print(f"[ask_llm] last-resort default: {DEFAULT_MODEL}")
    return DEFAULT_MODEL

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

    # Make the call, retrying once if the reply comes back empty (and has no tools).
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
        
        # Accept if there's either text or tool calls
        if content.strip() or tool_calls:
            return message
            
        print(f"[ask_llm] empty reply on attempt {attempt} - retrying")
        
    return {"role": "assistant", "content": "(The model returned an empty reply. Please try again.)"}


