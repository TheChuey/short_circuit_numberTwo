from dataclasses import dataclass

@dataclass
class Observation:
    """The result of an action executed by the agent."""
    action: str
    success: bool
    result: str
