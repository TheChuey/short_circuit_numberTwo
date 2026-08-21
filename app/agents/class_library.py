"""
app/agents/class_library.py
============================

Agent building blocks.

This module contains the classes that define what an agent is
and how its prompt is constructed:

    AgentProfile    — the agent's character (name, role, personality, etc.)
    PromptBuilder   — lightweight prompt template utilities
    PromptManager   — builds an AgentProfile from config

Zero external dependencies.
"""

import re
from dataclasses import dataclass, field
from string import Formatter
from typing import Any


# ==========================================================================
# AGENT PROFILE
# --------------------------------------------------------------------------
# The character of an agent: a display name, prompt sections,
# and the composed system prompt.
# ==========================================================================

@dataclass
class AgentProfile:
    """The character of an agent.

    Fields that go into the system prompt:
        role, purpose, personality, boundaries,
        communication, principles, decision_style, skills_table.

    The priorities field is documentation only and is NOT
    included in the prompt.
    """

    name: str = ""
    system_prompt: str = ""

    # Sections that compose the system prompt
    role: str = ""
    purpose: str = ""
    personality: str = ""
    boundaries: str = ""
    communication: str = ""
    principles: str = ""
    decision_style: str = ""
    skills_table: list = field(default_factory=list)

    # Documentation only (NOT in the system prompt)
    priorities: str = ""

    # Any additional '## sections' from the blueprint markdown, keyed by
    # section title. Each non-empty entry becomes an UPPERCASE-titled block
    # in the system prompt, so new sections need no code changes.
    extras: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, config: dict) -> "AgentProfile":
        """Create an AgentProfile from a configuration dict.

        Maps JSON keys to dataclass fields. Every other key is kept in
        'extras', so generic blueprint sections still reach the prompt.
        """
        known = {
            "name": config.get("name", ""),
            "role": config.get("role", ""),
            "purpose": config.get("purpose", ""),
            "personality": config.get("personality", ""),
            "boundaries": config.get("boundaries", ""),
            "communication": config.get("communication", ""),
            "principles": config.get("principles", ""),
            "decision_style": config.get("decision_style", ""),
            "skills_table": config.get("skills_table", []),
            "priorities": config.get("priorities", ""),
        }
        extras = {key: value for key, value in config.items() if key not in known and key != "system_prompt"}
        return cls(**known, extras=extras)


# ==========================================================================
# PROMPT BUILDER
# --------------------------------------------------------------------------
# Lightweight prompt template utilities.
# Supports {variable} substitution, role-based messages,
# chat-history placeholders, and message composition.
# ==========================================================================

class PromptBuilder:
    """Small application-owned prompt builder.

    Provides:
        - {variable} string substitution
        - system / user / assistant message creation
        - chat-history placeholders
        - message composition from tuple syntax
        - input-variable detection

    Example:

        prompt = PromptBuilder.from_messages([
            ("system", "You are {name}."),
            ("placeholder", "chat_history"),
            ("human", "{input}"),
        ])

        messages = prompt.format_messages(
            name="Bob",
            chat_history=[],
            input="Hello"
        )
    """

    # ==============================================================
    # TEMPLATE
    # ==============================================================

    @staticmethod
    def template(text: str, **kwargs) -> str:
        """Format a string template with {variable} substitution.

        Raises ValueError if required variables are missing.
        """
        PromptBuilder._validate_variables(text, kwargs)
        return text.format(**kwargs)

    # ==============================================================
    # MESSAGE BUILDERS
    # ==============================================================

    @staticmethod
    def system(text: str, **kwargs) -> dict:
        """Create a system message dict."""
        return {"role": "system", "content": PromptBuilder.template(text, **kwargs)}

    @staticmethod
    def human(text: str, **kwargs) -> dict:
        """Create a user message dict."""
        return {"role": "user", "content": PromptBuilder.template(text, **kwargs)}

    @staticmethod
    def assistant(text: str, **kwargs) -> dict:
        """Create an assistant message dict."""
        return {"role": "assistant", "content": PromptBuilder.template(text, **kwargs)}

    # ==============================================================
    # PLACEHOLDER
    # ==============================================================

    @staticmethod
    def placeholder(variable_name: str, values: list | None = None, optional: bool = True) -> list[dict]:
        """Insert a list of existing messages (e.g. chat history).

        Returns [] if values is None and optional is True.
        Raises ValueError if values is None and optional is False.
        """
        if values is None:
            if optional:
                return []
            raise ValueError(f"Required placeholder '{variable_name}' was not provided.")

        if not isinstance(values, list):
            raise TypeError(f"Placeholder '{variable_name}' must be a list.")

        return [PromptBuilder._normalize_message(m) for m in values]

    # ==============================================================
    # COMPOSITION
    # ==============================================================

    @classmethod
    def from_messages(cls, messages: list[Any]) -> "PromptBuilder":
        """Build a prompt from message definitions.

        Supported tuple formats:
            ("system", "You are {name}.")
            ("human", "{input}")
            ("user", "{input}")
            ("ai", "Previous response")
            ("assistant", "Previous response")
            ("placeholder", "chat_history")

        Plain strings become user messages.
        """
        parsed = [cls._parse_message(m) for m in messages]
        return cls(parsed)

    def __init__(self, messages: list[Any] | None = None):
        self.messages = messages or []

    # ==============================================================
    # FORMATTING
    # ==============================================================

    def format_messages(self, **kwargs) -> list[dict]:
        """Convert the prompt definition into message dicts."""
        result = []
        for message in self.messages:
            if message["type"] == "placeholder":
                values = kwargs.get(message["variable"], None)
                result.extend(self.placeholder(message["variable"], values, optional=message["optional"]))
            else:
                result.append({
                    "role": message["role"],
                    "content": self.template(message["content"], **kwargs),
                })
        return result

    def format_system_prompt(self, **kwargs) -> str:
        """Return only system messages as one string."""
        messages = self.format_messages(**kwargs)
        return "\n\n".join(m["content"] for m in messages if m["role"] == "system")

    # ==============================================================
    # VARIABLES
    # ==============================================================

    @property
    def input_variables(self) -> list[str]:
        """Return all variables used by this prompt, in order of first appearance."""
        variables = []
        for message in self.messages:
            if message["type"] == "placeholder":
                var = message["variable"]
                if var not in variables:
                    variables.append(var)
            else:
                for name in self._find_variables(message["content"]):
                    if name not in variables:
                        variables.append(name)
        return variables

    # ==============================================================
    # INTERNAL HELPERS
    # ==============================================================

    @staticmethod
    def _parse_message(message: Any) -> dict:
        """Convert supported input formats into one internal format."""

        if isinstance(message, dict):
            if message.get("type") == "placeholder":
                return message
            return {"type": "message", "role": message.get("role", "user"), "content": message.get("content", "")}

        if isinstance(message, tuple) and len(message) == 2:
            role, content = message
            if role == "placeholder":
                return {"type": "placeholder", "variable": str(content), "optional": True}
            return {"type": "message", "role": PromptBuilder._normalize_role(role), "content": str(content)}

        if isinstance(message, str):
            return {"type": "message", "role": "user", "content": message}

        raise TypeError(f"Unsupported prompt message type: {type(message).__name__}")

    @staticmethod
    def _normalize_role(role: str) -> str:
        """Normalize common role aliases."""
        aliases = {"human": "user", "ai": "assistant"}
        return aliases.get(role.lower().strip(), role.lower().strip())

    @staticmethod
    def _normalize_message(message: Any) -> dict:
        """Convert different message formats into a standard dict."""
        if isinstance(message, dict):
            return {"role": message.get("role", "user"), "content": str(message.get("content", ""))}
        return {"role": getattr(message, "role", "user"), "content": str(getattr(message, "content", message))}

    @staticmethod
    def _find_variables(text: str) -> list[str]:
        """Find format variables using Python's Formatter."""
        variables = []
        for _, field_name, _, _ in Formatter().parse(text):
            if not field_name:
                continue
            root_name = field_name.split(".")[0].split("[")[0]
            if root_name not in variables:
                variables.append(root_name)
        return variables

    @staticmethod
    def _validate_variables(text: str, values: dict) -> None:
        """Detect missing variables before calling str.format()."""
        required = PromptBuilder._find_variables(text)
        missing = [name for name in required if name not in values]
        if missing:
            raise ValueError("Missing prompt variables: " + ", ".join(missing))


# ==========================================================================
# PROMPT MANAGER
# --------------------------------------------------------------------------
# Builds an AgentProfile from configuration and composes
# the system prompt used by the Agent.
# ==========================================================================

class PromptManager:
    """Builds an AgentProfile from config and composes the system prompt."""

    @staticmethod
    def build(config: dict, adjustments: dict | None = None) -> AgentProfile:
        """Build an AgentProfile from a configuration dict.

        Steps:
            1. Create profile from dict
            2. Apply runtime adjustments
            3. Compose the system prompt
        """
        profile = AgentProfile.from_dict(config)
        PromptManager._apply_adjustments(profile, adjustments)
        profile.system_prompt = PromptManager.compose_system_prompt(profile)
        return profile

    @staticmethod
    def compose_system_prompt(profile: AgentProfile) -> str:
        """Build the final system prompt from profile sections.

        Selective inclusion: role, purpose, personality, boundaries,
        communication, principles, decision_style, and skills_table
        go into the prompt. priorities is excluded.
        """
        parts = []

        if profile.role:
            parts.append(f"ROLE\n{profile.role}")

        if profile.purpose:
            parts.append(f"PURPOSE\n{profile.purpose}")

        if profile.personality:
            parts.append(f"PERSONALITY\n{profile.personality}")

        if profile.boundaries:
            parts.append(f"BOUNDARIES\n{profile.boundaries}")

        if profile.communication:
            parts.append(f"COMMUNICATION STYLE\n{profile.communication}")

        if profile.principles:
            parts.append(f"PRINCIPLES\n{profile.principles}")

        if profile.decision_style:
            parts.append(f"DECISION STYLE\n{profile.decision_style}")

        if profile.skills_table:
            lines = [f"- {skill['id']}: {skill['description']}" for skill in profile.skills_table]
            parts.append("AVAILABLE SKILLS\n" + "\n".join(lines))

        # Generic blueprint sections (user, greeting, project_notes, ...)
        # become UPPERCASE-titled blocks, sorted for deterministic prompts.
        for title, content in sorted(profile.extras.items()):
            if content:
                parts.append(f"{title.upper()}\n{content}")

        return "\n\n".join(parts)

    @staticmethod
    def _apply_adjustments(profile: AgentProfile, adjustments: dict | None) -> None:
        """Apply runtime profile overrides."""
        if not adjustments:
            return
        for field_name, value in adjustments.items():
            if hasattr(profile, field_name):
                setattr(profile, field_name, value)
