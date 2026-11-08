"""Unit tests for models.py configuration compatibility across Hermes config schemas."""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _import_fresh_models(mock_config: dict, env_vars: dict | None = None):
    """Import models.py with an isolated mock config and environment."""
    config_mod = types.ModuleType("hermes_cli.config")
    setattr(config_mod, "load_config", lambda: mock_config)
    # Test our self-contained fallback by simulating get_compatible_custom_providers
    try:
        from hermes_cli.config import get_compatible_custom_providers
        setattr(config_mod, "get_compatible_custom_providers", get_compatible_custom_providers)
    except Exception:
        setattr(config_mod, "get_compatible_custom_providers", None)
    setattr(config_mod, "load_env", lambda: env_vars or {})

    sys.modules["hermes_cli"] = types.ModuleType("hermes_cli")
    sys.modules["hermes_cli.config"] = config_mod

    # Import models under test
    import importlib.util
    spec = importlib.util.spec_from_file_location("enhancer_test.models", ROOT / "models.py")
    assert spec is not None and spec.loader is not None
    models_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models_mod)
    return models_mod


def test_v12_providers_dict_format():
    """Verify v12+ `providers:` dict format loads all models and provider info."""
    mock_config = {
        "providers": {
            "cpa": {
                "base_url": "http://127.0.0.1:8317/v1",
                "api_key": "${CPA_API_KEY}",
                "api_mode": "chat_completions",
                "models": {
                    "GPT-6-Luna": {"name": "GPT-6 Luna"},
                    "GPT-6.1-Sol": {"name": "GPT-6.1 Sol"},
                    "Claude-Sonnet-5.5": {"name": "Claude Sonnet 5.5"},
                },
            }
        },
        "model": {"default": "GPT-6.1-Sol", "provider": "cpa"},
    }
    models = _import_fresh_models(mock_config, env_vars={"CPA_API_KEY": "test-key-123"})

    # 1. Available models list
    available = models.get_available_models()
    assert "GPT-6.1-Sol" in available
    assert "GPT-6-Luna" in available
    assert "Claude-Sonnet-5.5" in available
    assert len(available) == 3

    # 2. Provider groups
    groups = models.get_models_by_provider()
    assert len(groups) == 1
    prov_name, label, model_ids = groups[0]
    assert prov_name == "cpa"
    assert "GPT-6.1-Sol" in model_ids
    assert "GPT-6-Luna" in model_ids
    assert "Claude-Sonnet-5.5" in model_ids
    assert len(model_ids) == 3

    # 3. Resolve provider config with env resolution
    resolved = models.resolve_provider_config("cpa")
    assert resolved is not None
    assert resolved["base_url"] == "http://127.0.0.1:8317/v1"
    assert resolved["api_key"] == "test-key-123"
    assert resolved["provider"] == "cpa"

    # 4. Resolve provider for model
    assert models._resolve_provider_for_model("GPT-6-Luna") == "cpa"
    assert models._resolve_provider_for_model("Claude-Sonnet-5.5") == "cpa"


def test_legacy_custom_providers_list_format():
    """Verify legacy `custom_providers:` list format continues to work seamlessly."""
    mock_config = {
        "custom_providers": [
            {
                "name": "zenmux",
                "base_url": "https://zenmux.ai/api/v1",
                "api_key": "zen-secret",
                "api_mode": "chat_completions",
                "models": {
                    "deepseek-v4-pro": {"name": "DeepSeek V4 Pro"},
                    "glm-5.3": {"name": "GLM 5.3"},
                },
            }
        ],
        "model": {"default": "deepseek-v4-pro", "provider": "custom:zenmux"},
    }
    models = _import_fresh_models(mock_config)

    available = models.get_available_models()
    assert "deepseek-v4-pro" in available
    assert "glm-5.3" in available

    groups = models.get_models_by_provider()
    assert len(groups) == 1
    prov_name, label, model_ids = groups[0]
    assert prov_name == "zenmux"
    assert "deepseek-v4-pro" in model_ids
    assert "glm-5.3" in model_ids

    resolved = models.resolve_provider_config("zenmux")
    assert resolved is not None
    assert resolved["base_url"] == "https://zenmux.ai/api/v1"
    assert resolved["api_key"] == "zen-secret"
    assert resolved["provider"] == "custom:zenmux"

    assert models._resolve_provider_for_model("deepseek-v4-pro") == "zenmux"


def test_dual_format_coexistence():
    """Verify that having both providers and custom_providers merges without collisions."""
    mock_config = {
        "providers": {
            "cpa": {
                "base_url": "http://127.0.0.1:8317/v1",
                "models": {"GPT-6.1-Sol": {}},
            }
        },
        "custom_providers": [
            {
                "name": "zenmux",
                "base_url": "https://zenmux.ai/api/v1",
                "models": {"deepseek-v4-pro": {}},
            }
        ],
        "model": {"default": "GPT-6.1-Sol", "provider": "cpa"},
    }
    models = _import_fresh_models(mock_config)

    available = models.get_available_models()
    assert "GPT-6.1-Sol" in available
    assert "deepseek-v4-pro" in available

    groups = models.get_models_by_provider()
    prov_names = {g[0] for g in groups}
    assert "cpa" in prov_names
    assert "zenmux" in prov_names
