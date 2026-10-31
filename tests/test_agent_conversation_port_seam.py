# -*- coding: utf-8 -*-
"""W4.2 回归测试：agent 会话/上下文层的端口 seam。

收敛前 ``ConversationSession.add_message`` / ``get_history`` 与 ``chat_context`` 的
上下文读写直接调用 ``src.storage.get_db()``；收敛后改由 bootstrap 装配
``ConversationMessagePort`` / ``ChatContextPort``。这些用例锁住三条契约：
装配即可用、装配对象被真实消费、端口协议能被生产仓储真实满足。
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from src.application.agent import chat_context as chat_context_module
from src.application.agent import conversation as conversation_module
from src.application.agent.chat_context import _load_visible_messages
from src.application.agent.ports import ChatContextPort, ConversationMessagePort
from src.application.agent.conversation import ConversationSession
from src.infrastructure.persistence.repositories.conversation_repo import ConversationRepository


@pytest.fixture()
def _restore_port():
    prior = conversation_module._conversation_port
    try:
        yield
    finally:
        conversation_module.set_conversation_port(prior)


def test_set_conversation_port_roundtrip(_restore_port):
    fake = MagicMock()

    conversation_module.set_conversation_port(fake)

    assert conversation_module._conversation_port is fake
    assert conversation_module._get_conversation_port() is fake


def test_add_message_consumes_wired_port(_restore_port):
    fake = MagicMock()
    fake.save_conversation_message.return_value = 42
    conversation_module.set_conversation_port(fake)
    session = ConversationSession(session_id="s-1")

    message_id = session.add_message("user", "hello")

    fake.save_conversation_message.assert_called_once_with("s-1", "user", "hello")
    assert message_id == 42


def test_get_history_consumes_wired_port(_restore_port):
    fake = MagicMock()
    fake.get_conversation_history.return_value = [{"role": "user", "content": "hi"}]
    conversation_module.set_conversation_port(fake)
    session = ConversationSession(session_id="s-2")

    history = session.get_history()

    fake.get_conversation_history.assert_called_once_with("s-2")
    assert history == [{"role": "user", "content": "hi"}]


def test_configure_agent_conversation_wires_repository_over_database_manager():
    sentinel = object()
    with patch("src.bootstrap.agent.DatabaseManager") as mock_dm, patch(
        "src.bootstrap.agent.ConversationRepository"
    ) as mock_repo, patch(
        "src.application.agent.conversation.set_conversation_port"
    ) as mock_conv_set, patch(
        "src.application.agent.chat_context.set_chat_context_port"
    ) as mock_ctx_set:
        mock_dm.get_instance.return_value = sentinel

        from src.bootstrap.agent import configure_agent_conversation

        configure_agent_conversation()

    mock_repo.assert_called_once_with(sentinel)
    mock_conv_set.assert_called_once_with(mock_repo.return_value)
    mock_ctx_set.assert_called_once_with(mock_repo.return_value)


# ---------------------------------------------------------------------------
# ChatContextPort seam (chat_context.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def _restore_chat_port():
    prior = chat_context_module._chat_context_port
    try:
        yield
    finally:
        chat_context_module.set_chat_context_port(prior)


def test_set_chat_context_port_roundtrip(_restore_chat_port):
    fake = MagicMock()

    chat_context_module.set_chat_context_port(fake)

    assert chat_context_module._chat_context_port is fake
    assert chat_context_module._get_chat_context_port() is fake


def test_load_visible_messages_consumes_wired_chat_context_port(_restore_chat_port):
    fake = MagicMock()
    fake.get_visible_conversation_messages.return_value = [
        {"id": 7, "role": "user", "content": "hi"},
        {"id": 0, "role": "assistant", "content": "dropped-zero-id"},
        {"id": 8, "role": "system", "content": "dropped-role"},
    ]
    chat_context_module.set_chat_context_port(fake)

    messages = _load_visible_messages("s-3", limit=5)

    fake.get_visible_conversation_messages.assert_called_once_with("s-3", limit=5)
    assert [(msg.id, msg.role) for msg in messages] == [(7, "user")]


def _shape(fn):
    """Signature shape ignoring annotations (Protocol 与实现分属不同模块的字符串注解)。"""
    return [
        (p.name, p.kind, p.default)
        for p in inspect.signature(fn).parameters.values()
    ]


@pytest.mark.parametrize("protocol", [ConversationMessagePort, ChatContextPort])
def test_port_protocol_is_satisfied_by_conversation_repository(protocol):
    """锁住端口声明不落后于真实调用点（包含写侧 upsert_conversation_summary）。"""
    for name in dir(protocol):
        if name.startswith("_"):
            continue
        declared = getattr(protocol, name)
        if not callable(declared):
            continue
        implementation = getattr(ConversationRepository, name, None)
        assert implementation is not None, f"{name} 未在 ConversationRepository 实现"
        assert _shape(implementation) == _shape(declared), f"{name} 签名与端口声明不一致"


def test_usage_telemetry_adapter_persist_delegates_to_storage():
    from src.infrastructure.agent_runtime.usage_telemetry_provider import UsageTelemetryAdapter

    with patch("src.storage.persist_llm_usage") as mock_persist:
        UsageTelemetryAdapter().persist({"total_tokens": 5}, "openai/test-model")

    mock_persist.assert_called_once_with(
        {"total_tokens": 5}, "openai/test-model", call_type="agent"
    )
