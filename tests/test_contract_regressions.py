"""Static contract regressions for the public Hermes plugin boundary.

These tests intentionally inspect source instead of importing the full Hermes runtime,
so they remain runnable in GitHub Actions without a local Hermes checkout.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _class(tree: ast.AST, name: str) -> ast.ClassDef:
    return next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == name)


def _method(cls: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    return next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def _function(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def test_platform_registration_keeps_bundled_adapter_contract():
    tree = ast.parse((ROOT / "__init__.py").read_text(encoding="utf-8"))
    register = _function(tree, "register")
    call = next(
        node
        for node in ast.walk(register)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "register_platform"
    )
    source = (ROOT / "__init__.py").read_text(encoding="utf-8")
    assert "from plugins.platforms.mattermost.adapter import" in source
    assert "from plugins.platforms.mattermost import gateway_env" in source
    names = {keyword.arg for keyword in call.keywords}
    required = {
        "name",
        "adapter_factory",
        "check_fn",
        "validate_config",
        "is_connected",
        "setup_fn",
        "apply_yaml_config_fn",
        "cron_deliver_env_var",
        "standalone_sender_fn",
        "max_message_length",
        "allow_update_command",
        "platform_hint",
        "display_tier",
        "dashboard_description",
        "dashboard_env_vars",
        "env_overrides",
        "env_enable_credentials",
    }
    assert required <= names
    assert any(
        keyword.arg is None
        and isinstance(keyword.value, ast.Attribute)
        and isinstance(keyword.value.value, ast.Name)
        and keyword.value.value.id == "gateway_env"
        and keyword.value.attr == "AUTHZ"
        for keyword in call.keywords
    ), "pass the bundled AUTHZ mapping so new authorization fields are not silently lost"


def test_dm_approval_cards_use_the_upstream_capability_hook():
    """Card capability must come from overriding the upstream prompt hook.

    ``BasePlatformAdapter.supports_exec_approval_buttons()`` is True exactly when a
    subclass overrides ``_send_exec_approval_prompt``. Keeping (or re-introducing) a
    hardcoded ``return True`` override decouples the plugin from that probe, and a full
    ``send_exec_approval`` override bypasses the upstream Deny-only guard entirely.
    """
    tree = ast.parse((ROOT / "adapter.py").read_text(encoding="utf-8"))
    adapter = _class(tree, "MattermostApprovalAdapter")
    _method(adapter, "_send_exec_approval_prompt")  # raises when the hook disappears
    own_methods = {
        node.name
        for node in adapter.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "send_exec_approval" not in own_methods, (
        "override _send_exec_approval_prompt, not send_exec_approval — the full override "
        "skips card_shows_whole_command(), so a truncated command could be approved"
    )


def test_exec_approval_cards_are_bound_to_the_request_that_created_them():
    tree = ast.parse((ROOT / "adapter.py").read_text(encoding="utf-8"))
    adapter = _class(tree, "MattermostApprovalAdapter")
    sender = _method(adapter, "_send_exec_approval_prompt")
    signature_names = {arg.arg for arg in sender.args.args + sender.args.kwonlyargs}
    assert "prompt" in signature_names

    action_contexts = []
    for node in ast.walk(sender):
        if not isinstance(node, ast.Dict):
            continue
        keys = {
            key.value for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        if "action" in keys and "session_key" in keys:
            action_contexts.append(keys)
    assert action_contexts, "approval buttons must carry callback context"
    assert all("request_id" in keys for keys in action_contexts)

    callback = _method(adapter, "_handle_callback")
    card_calls = [
        node for node in ast.walk(callback)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "resolve_gateway_approval_card"
    ]
    assert len(card_calls) == 1, "the card path must resolve through the card-aware resolver"
    assert len(card_calls[0].args) >= 3, "resolve_gateway_approval_card(session_key, choice, request_id, ...)"
    assert any(keyword.arg == "actor_id" for keyword in card_calls[0].keywords), (
        "passing actor_id makes the resolver check the clicker's authority in the same "
        "critical section as the Deny-only gate"
    )
    callback_source = ast.unparse(callback)
    assert "if request_id" in callback_source, "missing request IDs must fail closed, not fall back to FIFO"


def test_model_switch_writes_through_for_gateway_restart_rehydration():
    tree = ast.parse((ROOT / "session_actions.py").read_text(encoding="utf-8"))
    method = _function(tree, "switch_session_model")
    calls = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "set_model_override"
    ]
    assert calls, "session model selections must persist across Gateway restarts"


def test_mattermost_compress_commands_delegate_to_the_canonical_gateway_handler():
    tree = ast.parse((ROOT / "adapter.py").read_text(encoding="utf-8"))
    adapter = _class(tree, "MattermostApprovalAdapter")
    route = _method(adapter, "_route_slash_command")
    route_values = {
        node.value for node in ast.walk(route)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert {"compress", "compact", "ephemeral"} <= route_values
    assert "in_channel" not in route_values

    handler = _method(adapter, "_handle_compress_command")
    handler_source = ast.unparse(handler)
    handler_values = {
        node.value for node in ast.walk(handler)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "/compress " in handler_values
    assert "_handle_compress_command(event)" in handler_source
    assert "await self.send(channel_id, acknowledgement" in handler_source
    assert "await self.edit_message(chat_id=channel_id" in handler_source
    assert "metadata={'thread_id': root_id}" in handler_source


def test_mattermost_reasoning_command_uses_native_gateway_handler_and_command_tokens():
    tree = ast.parse((ROOT / "adapter.py").read_text(encoding="utf-8"))
    adapter = _class(tree, "MattermostApprovalAdapter")
    route = _method(adapter, "_route_slash_command")
    route_source = ast.unparse(route)
    assert "reasoning" in route_source and "command" in route_source
    assert "MATTERMOST_SLASH_COMMAND_TOKENS" in route_source
    assert "compare_digest" in route_source

    handler = _method(adapter, "_handle_reasoning_command")
    handler_source = ast.unparse(handler)
    assert "runner._handle_reasoning_command(event)" in handler_source
    assert "runner._async_profile_scope_for_source(source)" in handler_source
    assert "reasoning" in handler_source and "args" in handler_source
    assert "thread_id" in handler_source and "root_id" in handler_source


def test_mattermost_stop_command_delegates_to_the_native_session_stop_handler():
    """`/stop` must ride the gateway's command path, never a plugin-side interrupt.

    Only the upstream handler invalidates the run generation, force-cleans the pending
    sentinel, hard-kills a hung turn, cancels that session's background delegations and
    clears a stuck typing indicator. A plugin-side reimplementation would drift and can
    leave the session lock held, so the contract is "synthesize the event, delegate".
    """
    tree = ast.parse((ROOT / "adapter.py").read_text(encoding="utf-8"))
    adapter = _class(tree, "MattermostApprovalAdapter")
    route = _method(adapter, "_route_slash_command")
    route_source = ast.unparse(route)
    route_values = {
        node.value for node in ast.walk(route)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "stop" in route_values
    assert "_handle_stop_command(channel_id, user_id, root_id" in route_source
    assert "self._schedule_followup(" in route_source

    handler = _method(adapter, "_handle_stop_command")
    handler_source = ast.unparse(handler)
    assert "runner._handle_stop_command(event)" in handler_source
    assert "runner._async_profile_scope_for_source(source)" in handler_source
    # The synthesized source is what decides the upstream stop scope: a thread stop
    # must carry the thread slot, a channel-level stop must not.
    assert "thread_id=root_id" in handler_source
    assert "metadata={'thread_id': root_id}" in handler_source
    assert "'/stop'" in handler_source

    handler_values = {
        node.value for node in ast.walk(handler)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    # Scope wording must distinguish the two tiers instead of claiming a global stop.
    assert any("本对话" in value for value in handler_values)
    assert any("本频道全部对话" in value for value in handler_values)
    assert not any("全局" in value or "所有平台" in value for value in handler_values)
