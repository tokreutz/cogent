import os
import sys
import re
from pathlib import Path
from dataclasses import dataclass
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

_PROMPT_SESSION: PromptSession | None = None

@dataclass
class PromptState:
    startup_hint_shown: bool = False
    piped_lines: list[str] | None = None
    piped_index: int = 0

_PROMPT_STATE: PromptState | None = None


def _get_state() -> PromptState:
    global _PROMPT_STATE
    if _PROMPT_STATE is None:
        _PROMPT_STATE = PromptState()
    return _PROMPT_STATE


def _ensure_cogent_dir() -> Path:
    base = Path(os.getcwd()) / '.cogent'
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:  # pragma: no cover - unusual filesystem failure
        raise RuntimeError("Failed to create .cogent directory for history")
    return base


def init_prompt_session() -> PromptSession:
    global _PROMPT_SESSION
    if _PROMPT_SESSION is not None:
        return _PROMPT_SESSION
    cogent_dir = _ensure_cogent_dir()
    history_file = cogent_dir / 'history'

    kb = KeyBindings()

    @kb.add("escape", "enter")
    def _(event):  # type: ignore
        event.current_buffer.validate_and_handle()

    @kb.add('enter')
    def _(event):  # type: ignore
        event.current_buffer.insert_text("\n")

    @kb.add("tab")
    def _(event):  # type: ignore
        event.current_buffer.insert_text("    ")

    session = PromptSession(
        '> ',
        history=FileHistory(str(history_file)),
        multiline=True,
        key_bindings=kb,
        enable_history_search=True,
    )
    _PROMPT_SESSION = session
    return session


def is_interactive(stdin) -> bool:
    try:
        return stdin.isatty()
    except Exception:  # pragma: no cover
        return False


def load_piped_lines(stdin) -> list[str]:
    data = stdin.read()
    if not data:
        return []
    return data.splitlines()


async def read_interactive(state: PromptState) -> str:
    session = init_prompt_session()
    if not state.startup_hint_shown:
        print('(Shift+Enter for newline, Enter to send; history stored in .cogent/history)')
        state.startup_hint_shown = True
    return await session.prompt_async()


def read_piped_line(state: PromptState) -> str:
    if state.piped_lines is None:
        state.piped_lines = load_piped_lines(sys.stdin)
        state.piped_index = 0
    if state.piped_index >= len(state.piped_lines):
        raise EOFError
    line = state.piped_lines[state.piped_index]
    state.piped_index += 1
    return line


async def get_user_input() -> str:
    state = _get_state()
    if is_interactive(sys.stdin):
        return await read_interactive(state)
    return read_piped_line(state)


def _reset_prompt_for_tests():  # pragma: no cover - helper for unit tests
    global _PROMPT_SESSION, _PROMPT_STATE
    _PROMPT_SESSION = None
    _PROMPT_STATE = None


# Slash command processing left here for now (could move to separate module if it grows)
_SLASH_PATTERN = r'/([a-zA-Z0-9_]+)'


def process_slash_commands(user_text: str) -> str:
    """Replace leading slash command with markdown file content.

    Only processes a single leading command (after trimming). Adds two newlines
    after inserted content. If file cannot be read, returns original text.
    """
    trimmed_text = user_text.strip()
    if not trimmed_text.startswith('/'):
        return user_text
    match = re.search(_SLASH_PATTERN, trimmed_text)
    if not match:
        return user_text
    command = match.group(1)
    commands_dir = os.path.join(os.getcwd(), '.cogent', 'commands')
    if not os.path.exists(commands_dir):
        return user_text
    md_file_path = os.path.join(commands_dir, f"{command}.md")
    if os.path.exists(md_file_path):
        try:
            with open(md_file_path, 'r') as f:
                content = f.read()
                return re.sub(f'/{command}', content + "\n\n", user_text, count=1)
        except Exception:  # pragma: no cover
            pass
    return user_text
