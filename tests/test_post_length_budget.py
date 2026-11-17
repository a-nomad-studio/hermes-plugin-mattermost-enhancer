"""Tests for the Mattermost per-post character budget (4000 → 16000).

Regression guard: upstream bundled ``MattermostAdapter.send()`` chunks at the
module-global ``MAX_POST_LENGTH`` (4000, an OpenClaw leftover). A single long
reply then arrives as 2–3 posts, each collapsed behind the client's hardcoded
600px "Show more". The enhancer must raise that budget — ideally without
touching upstream code.
"""
from __future__ import annotations

import importlib.util
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
approval_mod.resolve_gateway_approval_card = lambda *args, **kwargs: 0
sys.modules.setdefault("tools.approval", approval_mod)

pkg_name = "mm_enhancer_post_length_test_pkg"
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

_resolve_max_post_length = adapter_mod._resolve_max_post_length
_apply_max_post_length = adapter_mod._apply_max_post_length
MATTERMOST_POST_LENGTH_CEILING = adapter_mod.MATTERMOST_POST_LENGTH_CEILING
DEFAULT_MAX_POST_LENGTH = adapter_mod.DEFAULT_MAX_POST_LENGTH


@pytest.fixture(autouse=True)
def clean_env():
    key = "MATTERMOST_MAX_POST_LENGTH"
    saved = os.environ.get(key)
    os.environ.pop(key, None)
    yield
    if saved is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = saved


class DummyConfig:
    def __init__(self, extra=None):
        self.extra = extra or {}


def test_default_budget_is_16000():
    assert DEFAULT_MAX_POST_LENGTH == 16000
    assert MATTERMOST_POST_LENGTH_CEILING == 16383  # model.PostMessageMaxRunesV2
    assert _resolve_max_post_length(None) == 16000


def test_env_override_and_clamp():
    assert _resolve_max_post_length("8000") == 8000
    assert _resolve_max_post_length(" 12000 ") == 12000
    # Above the server ceiling → clamped, never rejected
    assert _resolve_max_post_length("99999") == MATTERMOST_POST_LENGTH_CEILING
    assert _resolve_max_post_length(str(MATTERMOST_POST_LENGTH_CEILING)) == MATTERMOST_POST_LENGTH_CEILING
    # Malformed / too small → default, not a crash
    assert _resolve_max_post_length("abc") == DEFAULT_MAX_POST_LENGTH
    assert _resolve_max_post_length("100") == DEFAULT_MAX_POST_LENGTH
    assert _resolve_max_post_length("") == DEFAULT_MAX_POST_LENGTH


def test_apply_patches_bundled_module_global():
    os.environ["MATTERMOST_MAX_POST_LENGTH"] = "9000"
    limit = _apply_max_post_length()
    assert limit == 9000
    # send() reads the global at call time — the patch is what stops the 4000 chunking
    assert bundled_mm.MAX_POST_LENGTH == 9000


def test_adapter_instantiation_patches_bundled_module():
    bundled_mm.MAX_POST_LENGTH = 4000  # simulate a freshly imported upstream module
    adapter = adapter_mod.MattermostApprovalAdapter(DummyConfig())
    assert adapter._max_post_length == DEFAULT_MAX_POST_LENGTH
    assert bundled_mm.MAX_POST_LENGTH == DEFAULT_MAX_POST_LENGTH


def test_register_passes_raised_max_message_length():
    ctx = MagicMock()
    init_mod.register(ctx)
    assert ctx.register_platform.called
    _, kwargs = ctx.register_platform.call_args
    # Gateway's streaming/progress/approval text paths read this value, so it
    # must match the post budget rather than the upstream 4000.
    assert kwargs.get("max_message_length") == DEFAULT_MAX_POST_LENGTH
