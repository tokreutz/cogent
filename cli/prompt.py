import os
import sys
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from Models.provider_config import list_available_models
from Models.model_state import save_last_selection
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

_PROMPT_SESSION: PromptSession | None = None

@dataclass
class PromptState:
    startup_hint_shown: bool = False
    piped_lines: list[str] | None = None
    piped_index: int = 0
    selected_provider: Optional[str] = None
    selected_model: Optional[str] = None
    model_switch_requested: bool = False  # flag for runner

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


def _render_prompt() -> str:
    state = _get_state()
    model = state.selected_model
    if model:
        # Shorten extremely long model names for display
        display = model
        if len(display) > 40:
            display = display[:37] + '...'
        return f'({display}) > '
    return '> '


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
        _render_prompt(),
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
    # Update prompt each time in case model changed
    try:
        session.message = _render_prompt()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        pass
    if not state.startup_hint_shown:
        print('(Enter for newline, Esc+Enter to send; history stored in .cogent/history)')
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
        # Show startup hint (once) before deciding which session factory to use
        if not state.startup_hint_shown:
            print('(Enter for newline, Esc+Enter to send; history stored in .cogent/history)')
            state.startup_hint_shown = True
        # Allow test monkeypatching via main.init_prompt_session by resolving dynamically
        try:
            import main as _main  # type: ignore
            if hasattr(_main, 'init_prompt_session') and _main.init_prompt_session is not init_prompt_session:  # type: ignore
                # Replace local cached session if different factory is provided
                session = _main.init_prompt_session()  # type: ignore
                if session is not _PROMPT_SESSION:
                    # Only show hint when using local creation path; tests patching bypass can still show once
                    pass
                try:
                    session.message = _render_prompt()  # type: ignore[attr-defined]
                except Exception:  # pragma: no cover
                    pass
                return await session.prompt_async()
        except Exception:  # pragma: no cover - fallback silently
            pass
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

    # Special interactive /model command
    if command == 'model':
        state = _get_state()
        pairs = list_available_models()
        if not pairs:
            print('[model] No models available')
            return ''
        # Display numbered list
        print('Available models:')
        for idx, (prov, model) in enumerate(pairs, start=1):
            marker = ''
            if prov == state.selected_provider and model == state.selected_model:
                marker = ' (current)'
            print(f"  {idx}. {prov}:{model}{marker}")
        # Prompt for selection
        while True:
            try:
                choice = input('Select number (or blank to cancel): ').strip()
            except EOFError:  # pragma: no cover - unlikely interactive edge
                return ''
            if choice == '':
                return ''
            if choice.isdigit():
                num = int(choice)
                if 1 <= num <= len(pairs):
                    prov, model = pairs[num - 1]
                    state.selected_provider = prov
                    state.selected_model = model
                    try:
                        save_last_selection(prov, model)
                    except Exception:  # pragma: no cover
                        pass
                    state.model_switch_requested = True
                    print(f"[model] Switched to {prov}:{model}. Conversation context will reset.")
                    return ''  # no message passed to agent
            print(f"Invalid selection. Enter 1-{len(pairs)} or blank to cancel.")

    # Default: treat as markdown command insertion
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
