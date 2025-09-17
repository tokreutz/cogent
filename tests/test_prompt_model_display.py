import os, sys, importlib

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli import prompt as prompt_mod


def test_render_prompt_without_model(monkeypatch):
    prompt_mod._reset_prompt_for_tests()
    # Access private render
    r = prompt_mod._render_prompt()
    assert r == '> '


def test_render_prompt_with_model(monkeypatch):
    prompt_mod._reset_prompt_for_tests()
    state = prompt_mod._get_state()
    state.selected_model = 'gpt-4o-mini'
    r = prompt_mod._render_prompt()
    assert '(gpt-4o-mini) > ' == r


def test_render_prompt_truncates(monkeypatch):
    prompt_mod._reset_prompt_for_tests()
    state = prompt_mod._get_state()
    state.selected_model = 'x' * 100
    r = prompt_mod._render_prompt()
    assert r.startswith('(xxxxxxxx')
    assert '...' in r
    assert r.endswith(' > ')
