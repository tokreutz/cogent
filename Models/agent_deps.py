from dataclasses import dataclass

@dataclass
class AgentDeps:
    cwd: str
    bash_session = {"cwd": None}