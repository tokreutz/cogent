import importlib
import asyncio
import os
import sys
from pathlib import Path

class FakeStdIn:
    def __init__(self, data: str, isatty: bool):
        self._data = data
        self._isatty = isatty
        self._read_called = False
    def isatty(self):
        return self._isatty
    def read(self):
        if self._read_called:
            return ''
        self._read_called = True
        return self._data

class FakeSession:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = 0
    async def prompt_async(self):
        if self.calls >= len(self.outputs):
            return ''
        out = self.outputs[self.calls]
        self.calls += 1
        return out

async def _run(coro):
    return await coro

def test_piped_lines_sequence_and_eof(monkeypatch):
    # Ensure working directory is project root so 'main' is importable
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    monkeypatch.chdir(project_root)
    main = importlib.import_module('main')
    main._reset_prompt_for_tests()
    fake_stdin = FakeStdIn('first\nsecond\n', isatty=False)
    monkeypatch.setattr(main.sys, 'stdin', fake_stdin)
    # first line
    line1 = asyncio.run(main.get_user_input())
    assert line1 == 'first'
    # second line
    line2 = asyncio.run(main.get_user_input())
    assert line2 == 'second'
    # EOF
    try:
        asyncio.run(main.get_user_input())
    except EOFError:
        pass
    else:
        assert False, 'Expected EOFError after consuming lines'

def test_interactive_path_uses_prompt_async(monkeypatch, capsys):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    monkeypatch.chdir(project_root)
    main = importlib.import_module('main')
    main._reset_prompt_for_tests()
    fake_stdin = FakeStdIn('', isatty=True)
    monkeypatch.setattr(main.sys, 'stdin', fake_stdin)
    # Inject fake session
    fake_session = FakeSession(['hello'])
    monkeypatch.setattr(main, 'init_prompt_session', lambda: fake_session)
    out = asyncio.run(main.get_user_input())
    assert out == 'hello'
    assert fake_session.calls == 1
    captured = capsys.readouterr().out
    # Ensure startup hint printed once
    assert captured.count('Shift+Enter') == 1

def test_startup_hint_only_once(monkeypatch, capsys):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    monkeypatch.chdir(project_root)
    main = importlib.import_module('main')
    main._reset_prompt_for_tests()
    fake_stdin = FakeStdIn('', isatty=True)
    monkeypatch.setattr(main.sys, 'stdin', fake_stdin)
    fake_session = FakeSession(['one', 'two'])
    monkeypatch.setattr(main, 'init_prompt_session', lambda: fake_session)
    out1 = asyncio.run(main.get_user_input())
    out2 = asyncio.run(main.get_user_input())
    assert out1 == 'one' and out2 == 'two'
    captured = capsys.readouterr().out
    # Hint string should appear exactly once
    assert captured.count('Shift+Enter') == 1
