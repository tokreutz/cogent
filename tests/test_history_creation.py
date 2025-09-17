import os
import importlib
from pathlib import Path

# We will import main and call the internal helpers directly.

def test_history_directory_created(tmp_path, monkeypatch):
    # Run in an isolated temporary cwd
    monkeypatch.chdir(tmp_path)
    # Copy minimal placeholder .cogent absence
    # Import main module fresh
    main = importlib.import_module('main')
    # Initialize session
    session = main.init_prompt_session()
    assert session is not None
    cogent_dir = Path(tmp_path) / '.cogent'
    assert cogent_dir.exists() and cogent_dir.is_dir()
    history_file = cogent_dir / 'history'
    # History file may not be written until first line is actually stored, but FileHistory should create it lazily.
    # Force a write by appending a dummy entry via history API if needed.
    session.history.append_string('dummy entry')
    assert history_file.exists()


def test_prompt_session_singleton(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main = importlib.import_module('main')
    s1 = main.init_prompt_session()
    s2 = main.init_prompt_session()
    assert s1 is s2, 'Expected singleton prompt session'
