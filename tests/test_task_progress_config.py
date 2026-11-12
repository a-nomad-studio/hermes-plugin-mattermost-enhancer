"""Tests for task_progress / tool_progress configuration in Mattermost Enhancer."""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock
import pytest

ROOT = Path(__file__).resolve().parent.parent

# ── Stubs for standalone test execution ──
types_mod = types
gateway_mod = types_mod.ModuleType("gateway")
platforms_mod = types_mod.ModuleType("gateway.platforms")
base_mod = types_mod.ModuleType("gateway.platforms.base")


class SendResult:
    def __init__(self, success=True, message_id=None, error=None):
        self.success = success
        self.message_id = message_id
        self.error = error


base_mod.SendResult = SendResult


class MattermostAdapter:
    MAX_POST_LENGTH = 4000

    def __init__(self, config):
        self.config = config
        self._bot_user_id = "bot123"
        self._base_url = "http://localhost:8065"
        self._token = "tok"
        self._reply_mode = "thread"
        self._closing = False


bundled_mm = types_mod.ModuleType("plugins.platforms.mattermost.adapter")
bundled_mm.MattermostAdapter = MattermostAdapter
bundled_mm.MAX_POST_LENGTH = 4000
bundled_mm._apply_yaml_config = lambda yaml_cfg, mm_cfg: dict(mm_cfg) if mm_cfg else None
bundled_mm._is_connected = lambda *a, **k: True
bundled_mm._standalone_send = lambda *a, **k: None
bundled_mm.interactive_setup = lambda *a, **k: None
bundled_mm.validate_mattermost_config = lambda *a, **k: (True, "")
bundled_mm._PLATFORM_HINT = "hint"

plugins_pkg = types_mod.ModuleType("plugins")
plugins_pkg.__path__ = []
platforms_pkg = types_mod.ModuleType("plugins.platforms")
platforms_pkg.__path__ = []
platforms_mattermost = types_mod.ModuleType("plugins.platforms.mattermost")
platforms_mattermost.__path__ = []

sys.modules.setdefault("plugins", plugins_pkg)
sys.modules.setdefault("plugins.platforms", platforms_pkg)
sys.modules.setdefault("plugins.platforms.mattermost", platforms_mattermost)
sys.modules.setdefault("plugins.platforms.mattermost.adapter", bundled_mm)

gateway_env = types_mod.ModuleType("plugins.platforms.mattermost.gateway_env")
gateway_env.AUTHZ = {}
gateway_env.ENV_OVERRIDES = ()
gateway_env.ENV_ENABLE_CREDENTIALS = ()
sys.modules.setdefault("plugins.platforms.mattermost.gateway_env", gateway_env)

sys.modules.setdefault("gateway", gateway_mod)
sys.modules.setdefault("gateway.platforms", platforms_mod)
sys.modules.setdefault("gateway.platforms.base", base_mod)

tools_pkg = types_mod.ModuleType("tools")
tools_pkg.__path__ = []
sys.modules.setdefault("tools", tools_pkg)
approval_mod = types_mod.ModuleType("tools.approval")
approval_mod.resolve_gateway_approval = lambda *args, **kwargs: 0
sys.modules.setdefault("tools.approval", approval_mod)

# Import adapter and __init__
import importlib.util

pkg_name = "mm_enhancer_progress_test_pkg"
pkg = types_mod.ModuleType(pkg_name)
pkg.__path__ = [str(ROOT)]
sys.modules[pkg_name] = pkg


def _load_pkg_mod(mod_name, filename):
    spec = importlib.util.spec_from_file_location(f"{pkg_name}.{mod_name}", ROOT / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"{pkg_name}.{mod_name}"] = mod
    spec.loader.exec_module(mod)
    return mod


cards_mod = _load_pkg_mod("cards", "cards.py")
branching_mod = _load_pkg_mod("branching", "branching.py")
adapter_mod = _load_pkg_mod("adapter", "adapter.py")
init_mod = _load_pkg_mod("__init__", "__init__.py")

MattermostApprovalAdapter = adapter_mod.MattermostApprovalAdapter
_resolve_task_progress_setting = adapter_mod._resolve_task_progress_setting
_get_configured_task_progress = adapter_mod._get_configured_task_progress


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure environment is clean before and after each test."""
    env_keys = [
        "MATTERMOST_TASK_PROGRESS",
        "MATTERMOST_TOOL_PROGRESS",
        "MATTERMOST_PROGRESS",
    ]
    saved = {k: os.environ.get(k) for k in env_keys}
    for k in env_keys:
        os.environ.pop(k, None)
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


class DummyConfig:
    def __init__(self, extra=None):
        self.extra = extra or {}


def test_resolve_task_progress_setting_truthy_and_falsy():
    # None defaults to True
    assert _resolve_task_progress_setting(None) is True

    # Booleans
    assert _resolve_task_progress_setting(True) is True
    assert _resolve_task_progress_setting(False) is False

    # Truthy strings
    for s in ("on", "ON", "true", "True", "1", "yes", "YES"):
        assert _resolve_task_progress_setting(s) is True

    # Falsy strings
    for s in ("off", "OFF", "false", "False", "0", "no", "NO"):
        assert _resolve_task_progress_setting(s) is False

    # Arbitrary strings default to True
    assert _resolve_task_progress_setting("anything_else") is True


def test_get_configured_task_progress_default():
    assert _get_configured_task_progress() is True


def test_get_configured_task_progress_env_vars():
    # Main env var
    os.environ["MATTERMOST_TASK_PROGRESS"] = "off"
    assert _get_configured_task_progress() is False

    # Tool progress alias
    os.environ.pop("MATTERMOST_TASK_PROGRESS")
    os.environ["MATTERMOST_TOOL_PROGRESS"] = "off"
    assert _get_configured_task_progress() is False

    # Progress alias
    os.environ.pop("MATTERMOST_TOOL_PROGRESS")
    os.environ["MATTERMOST_PROGRESS"] = "off"
    assert _get_configured_task_progress() is False

    # Main env var precedence
    os.environ["MATTERMOST_TASK_PROGRESS"] = "on"
    os.environ["MATTERMOST_TOOL_PROGRESS"] = "off"
    assert _get_configured_task_progress() is True


def test_adapter_task_progress_instance_attribute():
    # Default is on
    adapter_default = MattermostApprovalAdapter(DummyConfig())
    assert adapter_default._task_progress is True

    # extra task_progress = off
    adapter_off = MattermostApprovalAdapter(DummyConfig(extra={"task_progress": "off"}))
    assert adapter_off._task_progress is False

    # extra tool_progress = off
    adapter_tool_off = MattermostApprovalAdapter(DummyConfig(extra={"tool_progress": "off"}))
    assert adapter_tool_off._task_progress is False

    # extra progress = off
    adapter_prog_off = MattermostApprovalAdapter(DummyConfig(extra={"progress": "off"}))
    assert adapter_prog_off._task_progress is False

    # env var fallback
    os.environ["MATTERMOST_TASK_PROGRESS"] = "off"
    adapter_env_off = MattermostApprovalAdapter(DummyConfig())
    assert adapter_env_off._task_progress is False


def test_register_passes_display_overrides_when_task_progress_off():
    ctx = MagicMock()
    os.environ["MATTERMOST_TASK_PROGRESS"] = "off"

    init_mod.register(ctx)

    assert ctx.register_platform.called
    _, kwargs = ctx.register_platform.call_args
    assert kwargs.get("display_overrides") == {
        "tool_progress": "off",
        "thinking_progress": "off",
    }


def test_register_passes_empty_display_overrides_when_task_progress_on():
    ctx = MagicMock()
    # Default is on
    init_mod.register(ctx)

    assert ctx.register_platform.called
    _, kwargs = ctx.register_platform.call_args
    assert kwargs.get("display_overrides") == {}


def test_apply_yaml_config_enhancer_bridges_task_progress():
    yaml_cfg = {}
    mattermost_cfg = {"task_progress": "off", "require_mention": True}

    seeded = init_mod._apply_yaml_config_enhancer(yaml_cfg, mattermost_cfg)
    assert seeded is not None
    assert seeded.get("task_progress") == "off"
    assert os.environ.get("MATTERMOST_TASK_PROGRESS") == "off"
