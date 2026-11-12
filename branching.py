"""Message-level conversation branching for Mattermost (react with :new: to fork).

Hermes' built-in ``/branch`` on Mattermost can only clone the *whole* session and
switches the current thread in place. This module adds the CodeX-Desktop style
"branch from this message" flow:

    reaction_added(:new:) on any post
      → locate the matching Hermes transcript rows (user posts via platform_message_id,
        bot posts via "the user turn this reply belongs to")
      → post a fresh root post in the same channel (the sibling thread)
      → clone the transcript up to the cut point into a new session and bind it to the
        sibling thread's session key

Pure helpers (``locate_branch_cut``) carry no Hermes imports so they are unit-testable
in isolation; ``branch_from_post`` does the gateway wiring lazily.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_BRANCH_EMOJI = "new"
_PROMPT_QUOTE_LIMIT = 280


class BranchError(Exception):
    """A user-presentable reason why a branch could not be created."""


# ══════════════════════════════════════════════════════════════════════
# Pure helpers
# ══════════════════════════════════════════════════════════════════════

def parse_branch_emojis(raw: Optional[str]) -> frozenset:
    """``MATTERMOST_BRANCH_EMOJI`` → trigger emoji names. Unset → ``{"new"}``; ``off`` → empty."""
    if raw is None:
        return frozenset({DEFAULT_BRANCH_EMOJI})
    text = raw.strip().lower()
    if text in {"", "off", "false", "0", "none", "disabled"}:
        return frozenset()
    return frozenset(
        part.strip().strip(":") for part in text.split(",") if part.strip().strip(":")
    )


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts)
    return "" if content is None else str(content)


def locate_branch_cut(
    messages: List[Dict[str, Any]],
    thread_posts: List[Dict[str, Any]],
    post_id: str,
) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
    """Decide which transcript rows a branch from *post_id* inherits.

    ``messages``     Hermes transcript (``get_messages_as_conversation`` with row ids); user
                     rows carry the Mattermost post id in ``message_id``.
    ``thread_posts`` The Mattermost thread, oldest first (dicts with ``id``).
    ``post_id``      The post that received the trigger reaction.

    Returns ``(rows_to_copy, turns_kept, quoted_prompt)``.

    * User post      → every row *before* that prompt, so the new thread can re-ask or
                       rewrite it (``quoted_prompt`` carries the original text).
    * Assistant post → the whole turn the reply belongs to (prompt, tool calls and tool
                       results, final answer). Cutting at a turn boundary is what keeps
                       every tool call paired with its result.
    """
    user_idx_by_post: Dict[str, int] = {}
    for idx, msg in enumerate(messages):
        if msg.get("role") == "user" and msg.get("message_id"):
            user_idx_by_post[str(msg["message_id"])] = idx

    if post_id in user_idx_by_post:
        idx = user_idx_by_post[post_id]
        kept = messages[:idx]
        quoted = _text_of(messages[idx].get("content")).strip() or None
        return kept, _count_turns(kept), quoted

    # Bot reply (or any non-prompt post): belongs to the nearest preceding user prompt.
    ids = [str(p.get("id")) for p in thread_posts]
    if post_id not in ids:
        raise BranchError("在该串中找不到这条消息，无法定位分支点")
    anchor_idx: Optional[int] = None
    for pid in reversed(ids[: ids.index(post_id) + 1]):
        if pid in user_idx_by_post:
            anchor_idx = user_idx_by_post[pid]
            break
    if anchor_idx is None:
        raise BranchError("这条消息之前没有可继承的对话（可能已被压缩或属于其他会话）")

    end = len(messages)
    for idx in range(anchor_idx + 1, len(messages)):
        if messages[idx].get("role") == "user":
            end = idx
            break
    kept = messages[:end]
    return kept, _count_turns(kept), None


def _count_turns(rows: List[Dict[str, Any]]) -> int:
    return sum(1 for m in rows if m.get("role") == "user")


def render_branch_root_post(
    *, turns: int, permalink: Optional[str], quoted_prompt: Optional[str], title: str,
) -> str:
    """Markdown body of the sibling thread's root post."""
    origin = f"[原消息]({permalink})" if permalink else "原消息"
    lines = [f"⑂ **{title}** · 继承自{origin}（保留 {turns} 轮对话）"]
    if quoted_prompt:
        snippet = quoted_prompt if len(quoted_prompt) <= _PROMPT_QUOTE_LIMIT else (
            quoted_prompt[:_PROMPT_QUOTE_LIMIT] + "…"
        )
        quoted = "\n".join(f"> {line}" for line in snippet.splitlines() or [""])
        lines += ["", "原提问（可直接复制修改后在本串发送）：", quoted]
    lines += ["", "💡 在本串回复即可沿此分支继续；原对话保持不变。"]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# Gateway wiring
# ══════════════════════════════════════════════════════════════════════

def _runner():
    from gateway.run import _gateway_runner_ref

    runner = _gateway_runner_ref()
    if runner is None:
        raise BranchError("Gateway 尚未就绪，请稍后再试")
    return runner


async def _permalink(adapter: Any, channel: Dict[str, Any], post_id: str) -> Optional[str]:
    team_id = channel.get("team_id")
    if not team_id:  # DM / group channels have no team → Mattermost resolves /pl/ per team
        return None
    team = await adapter._api_get(f"teams/{team_id}")
    name = (team or {}).get("name")
    return f"/{name}/pl/{post_id}" if name else None


async def branch_from_post(adapter: Any, *, post_id: str, user_id: str) -> Dict[str, Any]:
    """Fork the conversation at *post_id* into a sibling thread. Returns a result summary.

    Raises ``BranchError`` with a user-presentable message on any expected failure.
    """
    from gateway.session import SessionSource  # noqa: F401  (import check: gateway present)

    post = await adapter._api_get(f"posts/{post_id}")
    if not post or not post.get("id"):
        raise BranchError("无法读取这条消息（可能已被删除）")
    channel_id = post["channel_id"]
    thread_root = post.get("root_id") or post_id

    # ── 1. Resolve the parent session (same key a user reply in this thread would use) ──
    chat_info = await adapter.get_chat_info(channel_id)
    chat_type = chat_info.get("type", "channel")
    adapter._channel_type_cache[channel_id] = chat_type
    # Mirror the adapter's inbound rule: a top-level post is its own thread root only in
    # thread reply mode outside DMs; otherwise the parent session has no thread id.
    src_thread_id = post.get("root_id") or (
        post_id if getattr(adapter, "_reply_mode", "") == "thread" and chat_type != "dm" else None
    )
    src_source = adapter.build_source(
        chat_id=channel_id, chat_type=chat_type, user_id=user_id, thread_id=src_thread_id,
    )
    runner = _runner()
    src_key = runner._session_key_for_source(src_source)
    entry = await runner.async_session_store.lookup_by_session_key(src_key)
    if entry is None:
        raise BranchError("这个串还没有 Hermes 对话记录，无法分支")

    running = getattr(runner, "_running_agents", None) or {}
    if src_key in running:
        raise BranchError("原对话正在运行中，请等当前回复结束后再分支（避免复制到不完整的一轮）")

    db = runner._session_db
    if db is None:
        raise BranchError("会话数据库不可用")
    parent_id = entry.session_id
    messages = await db.get_messages_as_conversation(parent_id, include_row_ids=True)

    # ── 2. Locate the cut point ──
    thread = await adapter._api_get(f"posts/{thread_root}/thread")
    posts = (thread or {}).get("posts") or {}
    order = (thread or {}).get("order") or []
    ordered = sorted((posts[i] for i in order if i in posts), key=lambda p: p.get("create_at", 0))
    kept, turns, quoted = locate_branch_cut(messages, ordered, post_id)
    if not kept:
        raise BranchError("这条消息之前没有可继承的历史，直接在频道里开一个新话题即可")

    # ── 3. Title + sibling thread root post ──
    parent_row = await db.get_session(parent_id) or {}
    base_title = (await db.get_session_title(parent_id)) or "branch"
    title = await db.get_next_title_in_lineage(base_title)
    channel = await adapter._api_get(f"channels/{channel_id}")
    permalink = await _permalink(adapter, channel or {}, post_id)
    body = render_branch_root_post(
        turns=turns, permalink=permalink, quoted_prompt=quoted, title=title,
    )
    payload: Dict[str, Any] = {"channel_id": channel_id, "message": body}
    try:
        from plugins.platforms.mattermost.adapter import _with_mentions_disabled

        payload = _with_mentions_disabled(payload)
    except Exception:
        logger.debug("mentions-disabled helper unavailable", exc_info=True)
    root_post = await adapter._api_post("posts", payload)
    new_root = (root_post or {}).get("id")
    if not new_root:
        raise BranchError("在频道里创建分支帖失败（Mattermost 未返回帖子 ID）")
    adapter._root_id_cache[new_root] = (new_root, time.time())

    # ── 4. Clone transcript into a new session bound to the sibling thread ──
    try:
        new_id = await _clone_into_new_session(
            adapter, runner, db, entry, parent_row, kept, title,
            channel_id=channel_id, chat_type=chat_type, user_id=user_id,
            new_root=new_root, src_key=src_key,
        )
    except Exception as exc:
        logger.error("Branch clone failed (post=%s): %s", post_id, exc, exc_info=True)
        await adapter._api("DELETE", f"posts/{new_root}")  # don't leave an orphan thread
        raise BranchError(f"复制对话历史失败：{exc}") from exc

    logger.info(
        "Branch created: parent=%s new=%s rows=%d turns=%d thread=%s trigger_post=%s",
        parent_id, new_id, len(kept), turns, new_root, post_id,
    )
    return {"session_id": new_id, "root_post_id": new_root, "rows": len(kept), "turns": turns,
            "title": title, "parent_session_id": parent_id}


async def _clone_into_new_session(
    adapter: Any, runner: Any, db: Any, entry: Any, parent_row: Dict[str, Any],
    kept: List[Dict[str, Any]], title: str, *, channel_id: str, chat_type: str,
    user_id: str, new_root: str, src_key: str,
) -> str:
    """Mirror ``gateway/slash_commands_session._handle_branch_command`` for a truncated copy."""
    from gateway.slash_commands_session import _branch_row

    dest_source = adapter.build_source(
        chat_id=channel_id, chat_type=chat_type, user_id=user_id, thread_id=new_root,
    )
    dest_key = runner._session_key_for_source(dest_source)
    new_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    try:
        origin_json = json.dumps(dest_source.to_dict())
    except Exception:
        origin_json = None

    await db.create_session(
        session_id=new_id,
        source="mattermost",
        model=parent_row.get("model"),
        model_config={"_branched_from": entry.session_id},
        parent_session_id=entry.session_id,
        user_id=dest_source.user_id,
        session_key=dest_key,
        chat_id=dest_source.chat_id,
        chat_type=dest_source.chat_type,
        thread_id=dest_source.thread_id,
        origin_json=origin_json,
        display_name=getattr(entry, "display_name", None),
        system_prompt=parent_row.get("system_prompt") or None,
    )
    await db.append_messages_batch(new_id, [_branch_row(m) for m in kept], chunk_rows=500)
    try:
        await db.set_session_title(new_id, title)
    except Exception:
        logger.debug("branch title not set", exc_info=True)

    # Materialize the thread's own routing entry, then point it at the clone.
    await runner.async_session_store.get_or_create_session(dest_source)
    new_entry = await runner.async_session_store.switch_session(dest_key, new_id)
    if not new_entry:
        raise RuntimeError("无法把新分支绑定到新线程")
    runner._clear_session_boundary_security_state(dest_key)
    runner._evict_cached_agent(dest_key)

    # Carry the parent thread's runtime choices (model / reasoning) over to the branch.
    override = runner._session_model_overrides.get(src_key)
    if override:
        runner._session_model_overrides[dest_key] = dict(override)
        try:
            await runner.async_session_store.set_model_override(dest_key, dict(override))
        except Exception:
            logger.debug("branch model override persisted in memory only", exc_info=True)
    getter = getattr(runner, "_session_reasoning_overrides", None)
    if getter and src_key in getter and hasattr(runner, "_set_session_reasoning_override"):
        runner._set_session_reasoning_override(dest_key, getter[src_key])
    return new_id
