import os
import sys
import importlib
import builtins
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Models.provider_config import load_providers_config, resolve_provider, build_chat_model, list_available_models
from Models.model_state import save_last_selection, load_last_selection
from cli import prompt as prompt_mod


def test_load_providers_config_defaults():
    cfg = load_providers_config()
    names = [p.name for p in cfg.providers]
    assert 'lmstudio' in names and 'openai' in names


def test_resolve_provider_env_override(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test')
    spec, model = resolve_provider()
    assert spec.name == 'openai'
    assert model in spec.models


def test_missing_required_key(monkeypatch, tmp_path):
    # Isolated directory with minimal providers.json and no .env
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath('providers.json').write_text('{"providers":[{"name":"openai","type":"openai","base_url":"https://api.openai.com/v1","api_key_env":"OPENAI_API_KEY","api_key_optional":false,"models":["gpt-4o-mini"],"default_model":"gpt-4o-mini"}]}' )
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    # Reload module to reset dotenv flag
    import importlib
    from Models import provider_config as pc
    importlib.reload(pc)
    with pytest.raises(RuntimeError) as e:
        pc.build_chat_model('openai')
    assert 'OPENAI_API_KEY' in str(e.value)


def test_list_available_models():
    pairs = list_available_models()
    assert any(p == 'openai' for p, _ in pairs)


def test_model_switch_flow(monkeypatch):
    # Ensure API keys present (openai required) and placeholder for lmstudio
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test')
    monkeypatch.delenv('LMSTUDIO_API_KEY', raising=False)

    importlib.reload(prompt_mod)

    # Monkeypatch input to simulate selecting first model
    inputs = ['1']
    def fake_input(prompt=''):
        return inputs.pop(0)
    monkeypatch.setattr(builtins, 'input', fake_input)

    # Trigger /model command
    out = prompt_mod.process_slash_commands('/model')
    assert out == ''  # command does not return user text
    state = prompt_mod._get_state()
    assert state.selected_provider is not None
    assert state.selected_model is not None
    assert state.model_switch_requested is True

    # Build model from selection to ensure it constructs
    m = build_chat_model(state.selected_provider, state.selected_model)
    assert m is not None

    # Simulate runner handling and clearing flag
    state.model_switch_requested = False
    assert state.model_switch_requested is False


def test_dotenv_auto_load(monkeypatch, tmp_path):
    # Move to temp directory and create providers.json + .env
    monkeypatch.chdir(tmp_path)
    # Write providers.json copying existing minimal openai entry
    tmp_path.joinpath('providers.json').write_text('{"providers":[{"name":"openai","type":"openai","base_url":"https://api.openai.com/v1","api_key_env":"OPENAI_API_KEY","api_key_optional":false,"models":["gpt-4o-mini"],"default_model":"gpt-4o-mini"}]}' )
    # Ensure env var not set
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    # Create .env file with key
    tmp_path.joinpath('.env').write_text('OPENAI_API_KEY=sk-from-dotenv\n')
    # Force reload module to reset dotenv loaded flag
    import importlib
    from Models import provider_config as pc
    importlib.reload(pc)
    m = pc.build_chat_model('openai')
    assert m is not None  # did not raise missing key


def test_persist_last_selection(monkeypatch, tmp_path):
    # Setup isolated env with providers.json
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath('providers.json').write_text('{"providers":[{"name":"lmstudio","type":"openai-compatible","base_url":"http://localhost:1234/v1","api_key_env":"LMSTUDIO_API_KEY","api_key_optional":true,"models":["model-x"],"default_model":"model-x"}]}' )
    # Save selection
    save_last_selection('lmstudio', 'model-x')
    sel = load_last_selection()
    assert sel and sel.provider == 'lmstudio' and sel.model == 'model-x'
    # Ensure create_main_agent picks it up (import after chdir)
    monkeypatch.delenv('MODEL_PROVIDER', raising=False)
    monkeypatch.delenv('MODEL_NAME', raising=False)
    from main_agent import create_main_agent
    agent = create_main_agent()
    assert hasattr(agent.model, '_cogent_provider_name')
    assert getattr(agent.model, '_cogent_model_name') == 'model-x'
