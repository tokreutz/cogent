from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class TodoItem(BaseModel):
    """A model representing a todo item in the task management system.
    
    Example:
    {
        "id": 1,
        "description": "Implement todo list feature",
        "state": "in_progress"
    }
    """
    
    id: int
    """ REQUIRED Unique identifier for the todo item """

    description: str
    """ REQUIRED Detailed description of the task to be completed """

    state: str
    """ REQUIRED  Current state of the todo item. Valid values are: "pending", "in_progress", "completed" """
