"""
write_markdown/app_config.py
============================

THE WRITE SIDE OF THE MARKDOWN PIPELINE
---------------------------------------

WHAT THIS MODULE AFFECTS:
    Writes  write_markdown/tools.md   <- SKILL_REGISTRY (app/tools/tools.py)  [auto-generated, do not hand-edit]
    Writes  config/skills.json        <- SKILL_REGISTRY (the skills catalog)
    Writes  config/models.json        <- live LLM scan (Ollama + LM Studio)
    Affects GET /api/tools (tools.md -> read_markdown/markdown_loader.py -> config/tools.json),
            the agent's tool list, and the model dropdown.

AppConfig owns the things that must be kept in sync with the real world / the
real code:

    1. config/models.json  <- the LLM models available right now
       (scan_models() + refresh_models() write config/models.json)

    2. config/skills.json  <- the skills catalog (id/name/function/description)
       and write_markdown/tools.md <- the tools the agent can actually call
       Both come from the SKILL_REGISTRY in app/tools/tools.py:
       (list_registered_tools() + refresh_skills_json() + refresh_tools_md())

Run standalone:    python write_markdown/app_config.py
Used at startup:   server.py's lifespan calls refresh_all() BEFORE load_all(),
                   because read_markdown/markdown_loader.py reads tools.md to
                   build config/tools.json.
"""

import json
import sys
import urllib.request
from pathlib import Path

import ollama

# Allow running this file directly from anywhere: put the backend root on
# sys.path so the `app` package below can be imported. Harmless when the app
# is launched via `python server.py` (root is already on the path).
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.tools.tools import SKILL_REGISTRY  # the single source of tool truth

LM_STUDIO_URL = "http://127.0.0.1:1234/v1/models"
LM_STUDIO_TIMEOUT = 2.0


class AppConfig:
    """Scan LLM models -> config/models.json, and list SKILL_REGISTRY -> tools.md."""

    def __init__(self):
        self.config_dir = BACKEND_DIR / "config"
        self.models_file = self.config_dir / "models.json"
        self.skills_file = self.config_dir / "skills.json"
        self.tools_file = BACKEND_DIR / "write_markdown" / "tools.md"

    # ------------------------------------------------------------------
    # MODELS
    # ------------------------------------------------------------------

    def scan_models(self) -> list:
        """Return the deduped list of available LLM models.

        Scans Ollama (via the ollama package) and LM Studio (via its HTTP
        endpoint). Each source is wrapped in its own try/except so one
        unreachable backend never crashes the scan - it just gets skipped.
        """
        models = []

        # 1. Ollama: list locally installed models.
        try:
            for m in ollama.list().get("models", []):
                model_id = m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
                size = m.get("size", 0) if isinstance(m, dict) else getattr(m, "size", 0)
                if model_id:
                    models.append(
                        {"id": model_id, "name": model_id, "source": "ollama", "size": size}
                    )
        except Exception as exc:
            print(f"[app_config] ollama scan failed: {exc}")

        # 2. LM Studio: hit its /v1/models endpoint.
        try:
            with urllib.request.urlopen(LM_STUDIO_URL, timeout=LM_STUDIO_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("data", []):
                if m.get("id"):
                    models.append(
                        {"id": m["id"], "name": m["id"], "source": "lmstudio", "size": 0}
                    )
        except Exception as exc:
            print(f"[app_config] lm_studio scan failed: {exc}")

        # 3. Dedupe by model id, keeping the first occurrence's order.
        seen, unique = set(), []
        for m in models:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)
        return unique

    def refresh_models(self) -> list:
        """Scan models and write config/models.json (returns the model list).

        The file is only overwritten when the scan finds models - an empty
        scan (e.g. Ollama down) leaves the last known good file untouched.
        """
        models = self.scan_models()
        if models:
            self.models_file.write_text(
                json.dumps({"models": models}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"[app_config] wrote {len(models)} models to {self.models_file}")
        else:
            print(f"[app_config] scan found no models - keeping {self.models_file}")
        return models

    # ------------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------------

    def list_registered_tools(self) -> dict:
        """Return {tool_id: first-line-of-docstring} from SKILL_REGISTRY.

        The registry lives in app/tools/tools.py, so the tool list here can
        never drift from the functions the agent can actually call.
        """
        tools = {}
        for name, fn in SKILL_REGISTRY.items():
            doc = (fn.__doc__ or "").strip()
            tools[name] = doc.splitlines()[0] if doc else ""
        return tools

    def refresh_skills_json(self) -> None:
        """Rewrite config/skills.json from the registry (the skills catalog).

        Format: {"skills": [{id, name, function, description}, ...]} where
        id == function == the SKILL_REGISTRY key. Kept as a generated catalog
        / test point: build_agent() resolves tools straight from SKILL_REGISTRY
        and does NOT read this file at runtime.
        """
        skills = []
        for tool_id, doc in self.list_registered_tools().items():
            skills.append(
                {
                    "id": tool_id,
                    "name": tool_id.replace("_", " ").title(),
                    "function": tool_id,
                    "description": doc,
                }
            )
        self.skills_file.write_text(
            json.dumps({"skills": skills}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[app_config] wrote {len(skills)} skills to {self.skills_file}")

    def refresh_tools_md(self) -> None:
        """Rewrite write_markdown/tools.md's '## tools' section from the registry.

        The file is AUTO-GENERATED: hand edits are overwritten at every
        server start (this runs before read_markdown/markdown_loader.py
        builds tools.json).
        """
        lines = [
            "# AI Agent Studio — Tools (auto-generated)",
            "",
            "> AUTO-GENERATED by `write_markdown/app_config.py` from the `SKILL_REGISTRY`",
            "> in `app/tools/tools.py` — do not hand-edit; restart to regenerate.",
            "> READ by `read_markdown/markdown_loader.py` → regenerates `config/tools.json`.",
            "",
            "## tools",
            "",
        ]
        for tool_id, doc in self.list_registered_tools().items():
            icon = "🔧"
            if "folder" in tool_id: icon = "📁"
            elif "pdf" in tool_id: icon = "📕"
            elif "venv" in tool_id: icon = "🐍"
            elif "read" in tool_id: icon = "📖"
            elif "write" in tool_id or "create" in tool_id: icon = "✍️"
            elif "date" in tool_id or "time" in tool_id: icon = "🕒"

            lines += [
                f"### {tool_id}",
                f"- name: {tool_id.replace('_', ' ').title()}",
                f"- icon: {icon}",
                "- enabled: true",
            ]
            if doc:
                lines.append(f"- description: {doc}")
            lines.append("")
        self.tools_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        print(f"[app_config] wrote {len(SKILL_REGISTRY)} tools to {self.tools_file}")

    # ------------------------------------------------------------------
    # ALL
    # ------------------------------------------------------------------

    def refresh_all(self) -> dict:
        """Refresh models.json, skills.json and tools.md; return a summary."""
        models = self.refresh_models()
        self.refresh_skills_json()
        self.refresh_tools_md()
        return {
            "models": [m["id"] for m in models],
            "skills": list(SKILL_REGISTRY.keys()),
            "tools": list(SKILL_REGISTRY.keys()),
        }


if __name__ == "__main__":
    # Running `python write_markdown/app_config.py` scans the LLMs, regenerates
    # skills.json + tools.md and prints a short summary of what was refreshed.
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(AppConfig().refresh_all(), indent=2, ensure_ascii=False))
