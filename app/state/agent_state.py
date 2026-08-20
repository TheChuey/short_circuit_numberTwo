from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class AgentState:
    """The current runtime state of the agent."""
    task: str
    observations: List[dict] = field(default_factory=list)
    actions: List[dict] = field(default_factory=list)
    tool_results: List[dict] = field(default_factory=list)
    final_response: Optional[str] = None
