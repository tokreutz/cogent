from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class AgentDeps:
    cwd: str
    # Each agent instance gets its own bash session state to avoid cross-run leakage.
    bash_session: Dict[str, Any] = field(default_factory=lambda: {"cwd": None})