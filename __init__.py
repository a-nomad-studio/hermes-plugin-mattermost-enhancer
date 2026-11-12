"""
Mattermost Unified Plugin — DM 审批 + /model + /new Interactive Message 卡片交互。

通过 register_platform(name="mattermost") 覆盖内置 MattermostAdapter，
新增回调服务器、Slash 指令处理、卡片渲染。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _apply_yaml_config_enhancer(yaml_cfg: dict, mattermost_cfg: dict) -> dict | None:
    """``apply_yaml_config_fn``: 扩展内置 YAML 桥接，支持 task_progress / tool_progress 配置。"""
    import os
    from plugins.platforms.mattermost.adapter import _apply_yaml_config
    from .adapter import _get_configured_task_progress, _resolve_task_progress_setting

    seeded = _apply_yaml_config(yaml_cfg, mattermost_cfg) or {}

    raw_val = None
    for key in ("task_progress", "tool_progress", "progress"):
        if key in mattermost_cfg and mattermost_cfg[key] is not None:
            raw_val = mattermost_cfg[key]
            seeded[key] = raw_val
            break

    if raw_val is not None and not os.getenv("MATTERMOST_TASK_PROGRESS"):
        os.environ["MATTERMOST_TASK_PROGRESS"] = "on" if _resolve_task_progress_setting(raw_val) else "off"

    # 同步动态更新 platform_registry 中 mattermost 的 display_overrides
    is_on = _get_configured_task_progress()
    try:
        from gateway.platform_registry import platform_registry
        entry = platform_registry.get("mattermost")
        if entry is not None:
            if not is_on:
                entry.display_overrides["tool_progress"] = "off"
                entry.display_overrides["thinking_progress"] = "off"
            else:
                if entry.display_overrides.get("tool_progress") == "off":
                    entry.display_overrides.pop("tool_progress", None)
                if entry.display_overrides.get("thinking_progress") == "off":
                    entry.display_overrides.pop("thinking_progress", None)
    except Exception as e:
        logger.debug("Failed to sync display_overrides for mattermost: %s", e)

    return seeded or None


def register(ctx):
    """Plugin entry point — called by Hermes plugin system at startup."""
    from .adapter import (
        MattermostApprovalAdapter,
        _get_configured_task_progress,
        _resolve_task_progress_setting,
    )
    from .callback_server import check_mattermost_requirements

    # Reuse the bundled plugin's infrastructure so that the enhancer's
    # register_platform preserves everything the bundled plugin provides
    # (YAML→env bridge, connected-probe, interactive setup, standalone
    # cron delivery, auth helpers, message-length limit, and display
    # settings) while layering the enhancer's own DM-approval + slash-
    # command + clarify-card features on top.
    from plugins.platforms.mattermost.adapter import (
        _apply_yaml_config,
        _is_connected,
        _standalone_send,
        interactive_setup,
        validate_mattermost_config,
        MAX_POST_LENGTH,
        _PLATFORM_HINT,
    )
    from plugins.platforms.mattermost import gateway_env
    task_progress_on = _get_configured_task_progress()
    display_overrides = {}
    if not task_progress_on:
        display_overrides = {
            "tool_progress": "off",
            "thinking_progress": "off",
        }

    ctx.register_platform(
        name="mattermost",
        label="Mattermost (Approval)",
        adapter_factory=lambda cfg: MattermostApprovalAdapter(cfg),
        check_fn=check_mattermost_requirements,
        validate_config=validate_mattermost_config,
        is_connected=_is_connected,
        required_env=[
            "MATTERMOST_URL",
            "MATTERMOST_TOKEN",
        ],
        install_hint=(
            "MATTERMOST_URL=https://mm.example.com"
            " MATTERMOST_TOKEN=xxx MATTERMOST_CALLBACK_BIND=0.0.0.0"
        ),
        setup_fn=interactive_setup,
        apply_yaml_config_fn=_apply_yaml_config_enhancer,
        cron_deliver_env_var="MATTERMOST_HOME_CHANNEL",
        standalone_sender_fn=_standalone_send,
        max_message_length=MAX_POST_LENGTH,
        emoji="💬",
        allow_update_command=True,
        platform_hint=_PLATFORM_HINT,
        display_tier="medium",
        display_overrides=display_overrides,
        dashboard_description="Connect Hermes to Mattermost channels and direct messages.",
        docs_url="https://mattermost.com/deploy/",
        dashboard_env_vars=("MATTERMOST_URL", "MATTERMOST_TOKEN", "MATTERMOST_ALLOWED_USERS"),
        **gateway_env.AUTHZ,
        env_overrides=gateway_env.ENV_OVERRIDES,
        env_enable_credentials=gateway_env.ENV_ENABLE_CREDENTIALS,
    )

    # 注册 pre_gateway_dispatch hook — 实现 Channel → Thread 模型继承
    ctx.register_hook("pre_gateway_dispatch", _model_inheritance_hook)

    logger.info("Mattermost Approval Plugin registered (overrides built-in adapter)")


def _model_inheritance_hook(event, gateway, session_store, **kwargs):
    """Channel → Thread 模型继承。

    当用户在 Channel 中通过 /model 切换模型后，新建的 Thread 自动继承
    Channel 的模型设置，无需在每个 Thread 中重复切换。

    session key 通过上游 build_session_key() 构建 — 与 Gateway 单一真源一致。
    历史教训：手拼 key 缺少 per-user 后缀，group/channel 层级的 override
    （agent:main:mattermost:group:{chat}:{user}）永远查不到。

    返回 {"action": "allow"} 始终放行消息，不改变消息处理流程。
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    source = event.source

    # 仅处理 Mattermost 的 Thread 消息
    if getattr(source.platform, "value", "") != "mattermost":
        return {"action": "allow"}
    if not source.thread_id:
        return {"action": "allow"}

    try:
        overrides = gateway._session_model_overrides

        # Thread 已有 override → 不做任何事（用户已在 Thread 内独立切模型）
        thread_key = gateway._session_key_for_source(source)
        if thread_key in overrides:
            return {"action": "allow"}

        # 查父 Channel 是否有 override（同一 chat、无 thread_id 的 source）
        try:
            from gateway.session import SessionSource as _SS
            parent_source = _SS(
                platform=source.platform, chat_id=source.chat_id,
                chat_type=source.chat_type, user_id=source.user_id,
                user_name=source.user_name, thread_id=None,
            )
        except Exception:
            parent_source = None
        parent_key = (
            gateway._session_key_for_source(parent_source)
            if parent_source is not None and hasattr(gateway, "_session_key_for_source")
            else None
        )
        parent_override = overrides.get(parent_key) if parent_key else None
        if not parent_override:
            return {"action": "allow"}

        # 继承 Channel 的模型设置到 Thread
        overrides[thread_key] = dict(parent_override)

        _log.info(
            "Model inherited: thread=%s ← channel=%s model=%s",
            thread_key, parent_key,
            parent_override.get("model", "?"),
        )

    except Exception:
        _log.debug("Model inheritance check failed", exc_info=True)

    return {"action": "allow"}
