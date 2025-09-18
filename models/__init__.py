import warnings
from models.agent_deps import AgentDeps  # noqa: F401
from models.model_state import load_last_selection, save_last_selection  # noqa: F401
from models.provider_config import (  # noqa: F401
    build_chat_model,
    list_available_models,
    load_providers_config,
    resolve_provider,
)
from models.session_recorder import SessionRecorder  # noqa: F401
from models.todo_item import TodoItem, TodoState  # noqa: F401
from models.tool_definition import ToolDefinition  # noqa: F401

__all__ = [
    'AgentDeps',
    'load_last_selection',
    'save_last_selection',
    'build_chat_model',
    'list_available_models',
    'load_providers_config',
    'resolve_provider',
    'SessionRecorder',
    'TodoItem',
    'TodoState',
    'ToolDefinition',
]

warnings.warn("Import 'Models' is deprecated; use 'models' instead.", DeprecationWarning, stacklevel=2)
