import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pydantic_ai.models.openai import Model, OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider


@dataclass
class ProviderSpec:
    name: str
    type: str
    base_url: str
    api_key_env: str
    api_key_optional: bool = False
    models: List[str] = field(default_factory=list)
    default_model: Optional[str] = None

    def choose_model(self, override: Optional[str]) -> str:
        if override:
            if self.models and override not in self.models:
                raise ValueError(f"Model '{override}' not in provider '{self.name}' models: {', '.join(self.models)}")
            return override
        if self.default_model:
            return self.default_model
        if self.models:
            return self.models[0]
        raise ValueError(f"Provider '{self.name}' has no models configured")


@dataclass
class ProvidersConfig:
    providers: List[ProviderSpec]

    def get(self, name: str) -> ProviderSpec:
        for p in self.providers:
            if p.name == name:
                return p
        raise KeyError(name)

    def first(self) -> ProviderSpec:
        if not self.providers:
            raise ValueError("No providers configured")
        return self.providers[0]


_DEFAULT_CONFIG_JSON = {
    "providers": [
        {
            "name": "lmstudio",
            "type": "openai-compatible",
            "base_url": "http://localhost:1234/v1",
            "api_key_env": "LMSTUDIO_API_KEY",
            "api_key_optional": True,
            "models": ["qwen3-coder-30b-a3b-instruct-mlx@6bit"],
            "default_model": "qwen3-coder-30b-a3b-instruct-mlx@6bit"
        },
        {
            "name": "openai",
            "type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "api_key_optional": False,
            "models": ["gpt-4o-mini", "gpt-4o"],
            "default_model": "gpt-4o-mini"
        }
    ]
}


def _coerce_provider(obj: dict) -> ProviderSpec:
    return ProviderSpec(
        name=obj["name"],
        type=obj.get("type", "openai"),
        base_url=obj["base_url"],
        api_key_env=obj["api_key_env"],
        api_key_optional=bool(obj.get("api_key_optional", False)),
        models=list(obj.get("models", [])),
        default_model=obj.get("default_model"),
    )


def load_providers_config(path: Optional[str] = None) -> ProvidersConfig:
    """Load providers configuration from JSON file or fallback to defaults.

    If the file is missing, returns embedded defaults and prints a one-line warning.
    """
    if path is None:
        path = os.path.join(os.getcwd(), 'providers.json')
    data = None
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception as e:  # pragma: no cover - rare read error
            raise RuntimeError(f"Failed to read providers config '{path}': {e}")
    else:
        # Warn once per process
        if not getattr(load_providers_config, '_warned_missing', False):
            print("[providers] providers.json not found – using built-in defaults")
            setattr(load_providers_config, '_warned_missing', True)
        data = _DEFAULT_CONFIG_JSON
    providers = [_coerce_provider(p) for p in data.get("providers", [])]
    return ProvidersConfig(providers=providers)


def resolve_provider(provider_name: Optional[str] = None, model_name: Optional[str] = None) -> Tuple[ProviderSpec, str]:
    # Allow environment fallbacks here for symmetry with build_chat_model
    provider_name = provider_name or os.environ.get('MODEL_PROVIDER')
    model_name = model_name or os.environ.get('MODEL_NAME')
    cfg = load_providers_config()
    provider: ProviderSpec
    if provider_name:
        try:
            provider = cfg.get(provider_name)
        except KeyError:
            available = ', '.join(p.name for p in cfg.providers)
            raise RuntimeError(f"Unknown provider '{provider_name}'. Available: {available}")
    else:
        provider = cfg.first()
    chosen_model = provider.choose_model(model_name)
    return provider, chosen_model


_DOTENV_LOADED = False


def _load_dotenv_once():
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    dotenv_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(dotenv_path):
        _DOTENV_LOADED = True
        return
    try:
        with open(dotenv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # Do not overwrite existing environment variables
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:  # pragma: no cover - reading .env should be robust
        pass
    _DOTENV_LOADED = True


def _resolve_api_key(provider: ProviderSpec) -> str:
    _load_dotenv_once()
    key = os.environ.get(provider.api_key_env)
    if key:
        return key
    if provider.api_key_optional:
        return "none"
    raise RuntimeError(f"Provider '{provider.name}' requires env var {provider.api_key_env} (not set)")


def build_chat_model(provider_name: Optional[str] = None, model_name: Optional[str] = None) -> Model:
    provider, chosen_model = resolve_provider(
        provider_name or os.environ.get('MODEL_PROVIDER'),
        model_name or os.environ.get('MODEL_NAME'),
    )
    api_key = _resolve_api_key(provider)
    openai_provider = OpenAIProvider(api_key=api_key, base_url=provider.base_url)

    if provider.type == 'openai':
        model_obj: Model = OpenAIResponsesModel(chosen_model, provider=openai_provider)
    elif provider.type == 'openai-compatible':
        model_obj = OpenAIChatModel(chosen_model, provider=openai_provider)
    else:
        raise RuntimeError(f"Unsupported provider type '{provider.type}' for provider '{provider.name}'")
    try:
        setattr(model_obj, '_cogent_provider_name', provider.name)
        setattr(model_obj, '_cogent_model_name', chosen_model)
    except Exception:  # pragma: no cover
        pass
    return model_obj



def list_available_models() -> list[tuple[str, str]]:
    cfg = load_providers_config()
    pairs = []
    for p in cfg.providers:
        if p.models:
            for m in p.models:
                pairs.append((p.name, m))
        else:
            pairs.append((p.name, p.default_model or "<none>"))
    return pairs
