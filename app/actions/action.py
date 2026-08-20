from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class Action:
    """An operation requested by the agent."""
    name: str
    tool: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
