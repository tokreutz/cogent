from pydantic import BaseModel, Field

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
    state: str = Field(..., description="Current state: pending | in_progress | completed")

    model_config = {
        "extra": "forbid"
    }
