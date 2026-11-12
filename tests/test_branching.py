"""Tests for message-level branching (react with :new: to fork a conversation).

Only the pure helpers and the reaction dispatcher are exercised here, so the suite runs
in CI without a Hermes checkout.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_branching():
    spec = importlib.util.spec_from_file_location("enhancer_branching_test", ROOT / "branching.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


branching = _load_branching()


# ── fixtures: one conversation with a tool-using turn in the middle ──────────

def _transcript():
    return [
        {"role": "user", "content": "q1", "message_id": "P1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2 (needs tools)", "message_id": "P3"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t1"}]},
        {"role": "tool", "content": "result", "tool_call_id": "t1"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "q3", "message_id": "P6"},
        {"role": "assistant", "content": "a3"},
    ]


def _thread():
    # P2 = reply to q1, P4/P5 = streamed pieces of the reply to q2, P7 = reply to q3
    return [{"id": i} for i in ("P1", "P2", "P3", "P4", "P5", "P6", "P7")]


# ── locate_branch_cut ────────────────────────────────────────────────────────

def test_user_post_cuts_before_that_prompt():
    kept, turns, quoted = branching.locate_branch_cut(_transcript(), _thread(), "P3")
    assert [m["content"] for m in kept] == ["q1", "a1"]
    assert turns == 1
    assert quoted == "q2 (needs tools)"


def test_first_user_post_has_nothing_to_inherit():
    kept, turns, _ = branching.locate_branch_cut(_transcript(), _thread(), "P1")
    assert kept == [] and turns == 0


def test_assistant_post_keeps_whole_turn_including_tool_rows():
    kept, turns, quoted = branching.locate_branch_cut(_transcript(), _thread(), "P5")
    roles = [m["role"] for m in kept]
    assert roles == ["user", "assistant", "user", "assistant", "tool", "assistant"]
    assert turns == 2
    assert quoted is None
    # every tool call is followed by its result — never a dangling call
    assert kept[-1]["content"] == "a2"


def test_assistant_reply_to_last_prompt_keeps_everything():
    kept, turns, _ = branching.locate_branch_cut(_transcript(), _thread(), "P7")
    assert len(kept) == len(_transcript()) and turns == 3


def test_unknown_post_is_rejected():
    with pytest.raises(branching.BranchError):
        branching.locate_branch_cut(_transcript(), _thread(), "NOPE")


def test_reply_before_any_known_prompt_is_rejected():
    with pytest.raises(branching.BranchError):
        branching.locate_branch_cut(_transcript(), [{"id": "X0"}, {"id": "X1"}], "X1")


def test_multimodal_prompt_is_quoted_as_text():
    msgs = [{"role": "user", "message_id": "P1",
             "content": [{"type": "text", "text": "look"}, {"type": "image_url", "image_url": {}}]}]
    _, _, quoted = branching.locate_branch_cut(msgs, [{"id": "P1"}], "P1")
    assert quoted == "look"


# ── trigger-emoji config ─────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    (None, {"new"}),
    ("", set()),
    ("off", set()),
    (":new:", {"new"}),
    ("new, twisted_rightwards_arrows", {"new", "twisted_rightwards_arrows"}),
])
def test_parse_branch_emojis(raw, expected):
    assert branching.parse_branch_emojis(raw) == frozenset(expected)


# ── root post rendering ──────────────────────────────────────────────────────

def test_root_post_quotes_prompt_and_links_origin():
    text = branching.render_branch_root_post(
        turns=2, permalink="/team/pl/abc", quoted_prompt="line1\nline2", title="foo #2")
    assert "[原消息](/team/pl/abc)" in text
    assert "> line1\n> line2" in text
    assert "保留 2 轮" in text


def test_root_post_truncates_long_prompt():
    text = branching.render_branch_root_post(
        turns=1, permalink=None, quoted_prompt="x" * 1000, title="t")
    assert "…" in text and len(text) < 700


# ── wiring contracts (source-level, no Hermes runtime needed) ────────────────

def _adapter_class():
    tree = ast.parse((ROOT / "adapter.py").read_text(encoding="utf-8"))
    return next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "MattermostApprovalAdapter")


def test_adapter_delegates_other_ws_events_to_upstream():
    cls = _adapter_class()
    method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_handle_ws_event")
    calls = [n for n in ast.walk(method) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "_handle_ws_event"]
    assert calls, "non-reaction events must still reach the bundled _handle_ws_event"


def test_branch_requires_authorization_before_cloning():
    cls = _adapter_class()
    method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef)
                  and n.name == "_run_branch_from_reaction")
    src = ast.unparse(method)
    assert src.index("_branch_user_allowed") < src.index("branch_from_post")
