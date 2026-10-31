# -*- coding: utf-8 -*-
# 本文件主要测试：测试数据源追踪相关功能
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.application.agent.provider_trace import (  # noqa: E402
    extract_provider_trace_turns,
    provider_namespace,
    resolved_model_provider_identity,
    resolved_provider_namespace,
    trace_model_matches,
)


def test_trace_model_matches_slashless_openai_namespace_without_widening_model_match() -> None:
    assert provider_namespace("gpt-4o-mini") == "openai"
    assert trace_model_matches("openai", "gpt-4o-mini", "gpt-4o-mini") is True
    assert trace_model_matches("anthropic", "gpt-4o-mini", "gpt-4o-mini") is False
    assert trace_model_matches("openai", "gpt-4o-mini", "openai/gpt-4o-mini") is False
    assert trace_model_matches(
        "anthropic",
        "claude-router",
        "claude-router",
        current_provider="anthropic",
    ) is True


def test_resolved_provider_namespace_uses_router_alias_before_slashless_default() -> None:
    model_list = [
        {
            "model_name": "claude-router",
            "litellm_params": {"model": "anthropic/claude-sonnet-test"},
        }
    ]

    assert resolved_provider_namespace("claude-router", model_list) == "anthropic"
    assert resolved_provider_namespace("gpt-4o-mini", model_list) == "openai"


def test_resolved_model_provider_identity_returns_wire_model_and_provider() -> None:
    model_list = [
        {
            "model_name": "fast",
            "litellm_params": {"model": "openai/gpt-4o"},
        }
    ]

    assert resolved_model_provider_identity("fast", model_list) == ("openai/gpt-4o", "openai")
    assert resolved_model_provider_identity("gpt-4o-mini", model_list) == ("gpt-4o-mini", "openai")


def test_extract_trace_scans_only_current_run_and_keeps_multi_step_tool_loop() -> None:
    messages = [
        {
            "role": "assistant",
            "_trace_provider": "deepseek",
            "_trace_model": "deepseek/deepseek-chat",
            "reasoning_content": "old",
            "tool_calls": [{"id": "old", "name": "echo", "arguments": {}}],
        },
        {"role": "tool", "tool_call_id": "old", "content": "old-result"},
        {"role": "user", "content": "current"},
        {
            "role": "assistant",
            "_trace_provider": "deepseek",
            "_trace_model": "deepseek/deepseek-chat",
            "content": "step1",
            "reasoning_content": "r1",
            "tool_calls": [{"id": "c1", "name": "echo", "arguments": {}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "result1"},
        {
            "role": "assistant",
            "_trace_provider": "deepseek",
            "_trace_model": "deepseek/deepseek-chat",
            "content": "step2",
            "reasoning_content": "r2",
            "tool_calls": [{"id": "c2", "name": "echo", "arguments": {}}],
        },
        {"role": "tool", "tool_call_id": "c2", "content": "result2"},
    ]

    turns, diagnostics = extract_provider_trace_turns(
        messages,
        baseline_len=3,
        run_id="run-1",
        anchor_user_message_id=10,
        anchor_assistant_message_id=11,
    )

    assert diagnostics.trace_dropped_reason == ""
    assert len(turns) == 1
    assert [msg["role"] for msg in turns[0].messages] == ["assistant", "tool", "assistant", "tool"]
    assert turns[0].messages[0]["reasoning_content"] == "r1"
    assert turns[0].messages[2]["reasoning_content"] == "r2"
    assert "_trace_provider" not in turns[0].messages[0]
    assert turns[0].must_roundtrip is True


def test_extract_trace_drops_deepseek_without_required_tool_reasoning_pair_and_mixed_model() -> None:
    no_tool_turns, no_tool_diag = extract_provider_trace_turns(
        [
            {"role": "user", "content": "u"},
            {
                "role": "assistant",
                "_trace_provider": "deepseek",
                "_trace_model": "deepseek/deepseek-chat",
                "reasoning_content": "reasoning-only",
                "content": "final",
            },
        ],
        baseline_len=1,
    )

    assert no_tool_turns == []
    assert no_tool_diag.trace_dropped_reason == ""

    no_reasoning_turns, no_reasoning_diag = extract_provider_trace_turns(
        [
            {"role": "user", "content": "u"},
            {
                "role": "assistant",
                "_trace_provider": "deepseek",
                "_trace_model": "deepseek/deepseek-chat",
                "tool_calls": [
                    {
                        "id": "c0",
                        "name": "echo",
                        "arguments": {},
                        "provider_specific_fields": {"extra": "not-enough"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "c0", "content": "result"},
        ],
        baseline_len=1,
    )

    assert no_reasoning_turns == []
    assert no_reasoning_diag.trace_dropped_reason == "not_required"

    mixed_turns, mixed_diag = extract_provider_trace_turns(
        [
            {"role": "user", "content": "u"},
            {
                "role": "assistant",
                "_trace_provider": "deepseek",
                "_trace_model": "deepseek/deepseek-chat",
                "reasoning_content": "r1",
                "tool_calls": [{"id": "c1", "name": "echo", "arguments": {}}],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "result1"},
            {
                "role": "assistant",
                "_trace_provider": "deepseek",
                "_trace_model": "deepseek/deepseek-reasoner",
                "reasoning_content": "r2",
                "tool_calls": [{"id": "c2", "name": "echo", "arguments": {}}],
            },
        ],
        baseline_len=1,
    )

    assert mixed_turns == []
    assert mixed_diag.mixed_model_trace is True
    assert mixed_diag.trace_dropped_reason == "mixed_model_trace"


# ---------------------------------------------------------------------------
# W4.2 依赖倒置收敛：persist_provider_trace_turns 默认 db_factory seam
# ---------------------------------------------------------------------------

_TRACEABLE_MESSAGES = [
    {"role": "user", "content": "question"},
    {
        "role": "assistant",
        "content": "checking",
        "_trace_provider": "deepseek",
        "_trace_model": "deepseek/deepseek-chat",
        "reasoning_content": "r1",
        "tool_calls": [{"id": "call_1", "name": "echo", "arguments": {"message": "x"}}],
    },
    {"role": "tool", "tool_call_id": "call_1", "content": "tool-result"},
]


def test_provider_trace_default_db_factory_seam_accessor() -> None:
    """seam setter/getter 往返；可置 None 回退，不污染进程级默认值。"""
    from src.application.agent import provider_trace as pt_mod

    prior = pt_mod._get_default_db_factory()
    sentinel = object()
    try:
        pt_mod.set_default_db_factory(sentinel)
        assert pt_mod._get_default_db_factory() is sentinel
        pt_mod.set_default_db_factory(None)
        assert pt_mod._get_default_db_factory() is None
    finally:
        pt_mod.set_default_db_factory(prior)


def test_persist_provider_trace_turns_consumes_default_db_factory_seam() -> None:
    """未显式传入 db_factory 时应经模块级默认 seam 取库（收敛后的真实持久化路径）。"""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from src.application.agent import provider_trace as pt_mod

    calls = []
    db = SimpleNamespace(
        save_agent_provider_turn=MagicMock(side_effect=lambda **kw: (calls.append(kw), 1)[1])
    )
    prior = pt_mod._get_default_db_factory()
    pt_mod.set_default_db_factory(lambda: db)
    try:
        pt_mod.persist_provider_trace_turns(
            session_id="s-seam",
            run_id="r-seam",
            messages=_TRACEABLE_MESSAGES,
            baseline_len=1,
            user_message_id=10,
            assistant_message_id=11,
        )
    finally:
        pt_mod.set_default_db_factory(prior)

    assert db.save_agent_provider_turn.called
    assert calls and calls[0]["session_id"] == "s-seam"


def test_persist_provider_trace_turns_fails_open_when_seam_unwired() -> None:
    """seam 未装配（None）时不得抛出，沿用既有 try/except fail-open 语义。"""
    from src.application.agent import provider_trace as pt_mod

    prior = pt_mod._get_default_db_factory()
    pt_mod.set_default_db_factory(None)
    try:
        assert pt_mod.persist_provider_trace_turns(
            session_id="s-unwired",
            run_id="r-unwired",
            messages=_TRACEABLE_MESSAGES,
            baseline_len=1,
            user_message_id=10,
            assistant_message_id=11,
        ) is None
    finally:
        pt_mod.set_default_db_factory(prior)


def test_configure_provider_trace_wires_database_manager_get_instance() -> None:
    """bootstrap 装配将 DatabaseManager.get_instance 绑定为默认 db_factory（幂等）。"""
    from unittest.mock import patch

    from src.application.agent import provider_trace as pt_mod
    from src.bootstrap.agent import configure_provider_trace

    with patch("src.bootstrap.agent.DatabaseManager") as mock_dm, patch.object(
        pt_mod, "set_default_db_factory"
    ) as mock_set:
        configure_provider_trace()

    mock_set.assert_called_once_with(mock_dm.get_instance)
