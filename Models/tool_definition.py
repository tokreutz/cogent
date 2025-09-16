from dataclasses import dataclass
from typing import Callable
from pydantic import BaseModel
    
class ToolDefinition(BaseModel):
    fn: Callable
    usage_system_prompt: str