import json
import importlib
from pathlib import Path


def test_session_file_created_and_updated(tmp_path, monkeypatch):
    # Run in isolated cwd
    monkeypatch.chdir(tmp_path)

    # Import runner pieces lazily
    runner = importlib.import_module('cli.runner')
    recorder_mod = importlib.import_module('Models.session_recorder')

    # Create a recorder directly (avoid needing a real model call)
    recorder = recorder_mod.SessionRecorder(tmp_path)

    # Simulate two message turns with minimal stand-in objects
    class Msg:
        def __init__(self, role, content):
            self.role = role
            self.content = content

    history = [Msg('user', 'hello')]
    recorder.record(history)
    assert recorder.path.exists()
    data1 = json.loads(recorder.path.read_text())
    assert data1['message_count'] == 1
    assert data1['messages'][0]['content'] == 'hello'

    history.append(Msg('assistant', 'hi there'))
    recorder.record(history)
    data2 = json.loads(recorder.path.read_text())
    assert data2['message_count'] == 2
    roles = [m['role'] for m in data2['messages']]
    assert roles == ['user', 'assistant']
    assert data2['session_id'] == data1['session_id']
    assert data2['updated_at'] >= data1['updated_at']

    # Directory structure check
    sessions_dir = Path(tmp_path) / '.cogent' / 'sessions'
    assert sessions_dir.exists()
    assert any(p.suffix == '.json' for p in sessions_dir.iterdir())
