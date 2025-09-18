import json
import os
from dataclasses import dataclass
from typing import Optional, Tuple

STATE_DIR_NAME = '.cogent'
STATE_FILE_NAME = 'state.json'


@dataclass
class ModelSelection:
    provider: str
    model: str


def _state_path(cwd: Optional[str] = None) -> str:
    base = cwd or os.getcwd()
    return os.path.join(base, STATE_DIR_NAME, STATE_FILE_NAME)


def load_last_selection(cwd: Optional[str] = None) -> Optional[ModelSelection]:
    path = _state_path(cwd)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        provider = data.get('provider')
        model = data.get('model')
        if isinstance(provider, str) and isinstance(model, str):
            return ModelSelection(provider=provider, model=model)
    except Exception:  # pragma: no cover - corrupt file
        return None
    return None


def save_last_selection(provider: str, model: str, cwd: Optional[str] = None) -> None:
    base = cwd or os.getcwd()
    state_dir = os.path.join(base, STATE_DIR_NAME)
    try:
        os.makedirs(state_dir, exist_ok=True)
        with open(os.path.join(state_dir, STATE_FILE_NAME), 'w') as f:
            json.dump({'provider': provider, 'model': model}, f)
    except Exception:  # pragma: no cover - IO failure not fatal
        pass
