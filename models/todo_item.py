from enum import Enum
from pydantic import BaseModel, Field


class TodoState(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class TodoItem(BaseModel):
    """A model representing a todo item in the task management system.

    Example:
        {
            "id": 1,
            "description": "Implement todo list feature",
            "state": "in_progress"
        }
    """

    id: int = Field(..., description="Unique identifier for the todo item")
    description: str = Field(..., description="Detailed description of the task to be completed")
    state: TodoState = Field(..., description="Current state of the todo item")

    model_config = {
        "extra": "forbid"
    }
