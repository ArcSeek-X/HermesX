# -*- coding: utf-8 -*-
"""``bot/`` 的分层接线：会话与代码归一化不再直连存储 / 数据源。

``bot/commands/{ask,chat,history}.py`` 与 ``bot/dispatcher.py`` 曾各带一条
``src.storage`` 或 ``data_provider.base`` 直连。现在链路为：Bot 命令（参数与文案）
→ ``AgentConversationService``（会话）或 ``src.application.quote.stock_code_utils``（代码归一化）
→ ``src.bootstrap`` 装配。本文同时锁定：
- 四个文件中不再出现被禁 import；
- 用例的 ``extra_session_ids`` 语义（默认 ``[user_id]``，显式传入以传入为准）；
- Bot 的 legacy 会话兼容规则仍由命令层决定，用例只做透传。
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from bot.commands.chat import ChatCommand
from bot.commands.history import HistoryCommand
from src.domain.notification.bot_message import BotMessage, ChatType
from data_provider.base import canonical_stock_code
from src.application.agent import AgentConversationService
from src.application.quote.stock_code_utils import (
    canonical_stock_code_for_analysis,
    canonical_stock_code_for_input,
)

_BOT_FILES = (
    Path(__file__).resolve().parent.parent / "bot" / "commands" / "ask.py",
    Path(__file__).resolve().parent.parent / "bot" / "commands" / "chat.py",
    Path(__file__).resolve().parent.parent / "bot" / "commands" / "history.py",
    Path(__file__).resolve().parent.parent / "bot" / "dispatcher.py",
)
_FORBIDDEN_ROOTS = (
    "src.storage",
    "src.repositories",
    "src.infrastructure",
    "data_provider",
)


def _imported_modules(path: Path) -> List[str]:
    """返回文件里出现的全部 import 目标（含 ``import a.b`` 的绝对名）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def _outer_layer_imports(path: Path) -> List[str]:
    """返回命中禁用根包的 import 目标（空列表表示分层干净）。"""
    hits: List[str] = []
    for module in _imported_modules(path):
        for root in _FORBIDDEN_ROOTS:
            if module == root or module.startswith(root + "."):
                hits.append(module)
                break
    return hits


def _message(content: str, *, group: bool = False) -> BotMessage:
    return BotMessage(
        platform="feishu",
        message_id="m1",
        user_id="u1",
        user_name="tester",
        chat_id="group-1" if group else "p2p",
        chat_type=ChatType.GROUP if group else ChatType.PRIVATE,
        content=content,
        raw_content=content,
    )


class FakeConversationRepository:
    """按调用记录参数，返回固定结果的端口替身。"""

    def __init__(
        self,
        *,
        sessions: Optional[List[Dict[str, Any]]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        existing_sessions: Optional[List[str]] = None,
        deleted: int = 0,
    ) -> None:
        self.sessions = sessions or []
        self.messages = messages or []
        self.existing_sessions = set(existing_sessions or [])
        self.deleted = deleted
        self.calls: List[tuple] = []

    def get_chat_sessions(
        self,
        limit: int = 50,
        session_prefix: Optional[str] = None,
        extra_session_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        self.calls.append(("get_chat_sessions", limit, session_prefix, extra_session_ids))
        return self.sessions

    def get_conversation_messages(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        self.calls.append(("get_conversation_messages", session_id, limit))
        return self.messages

    def conversation_session_exists(self, session_id: str) -> bool:
        self.calls.append(("conversation_session_exists", session_id))
        return session_id in self.existing_sessions

    def delete_conversation_session(self, session_id: str) -> int:
        self.calls.append(("delete_conversation_session", session_id))
        return self.deleted


class BotLayeringTestCase(unittest.TestCase):
    def test_bot_modules_have_no_storage_or_provider_import(self) -> None:
        for path in _BOT_FILES:
            self.assertEqual(_outer_layer_imports(path), [], path.name)


class AgentConversationServiceExtraIdsTestCase(unittest.TestCase):
    """``extra_session_ids`` 只在调用方显式给出时才改写默认集合。"""

    def _service(self, repository: FakeConversationRepository) -> AgentConversationService:
        return AgentConversationService(repository=repository)

    def test_default_appends_user_id_as_exact_session_id(self) -> None:
        repository = FakeConversationRepository()
        self._service(repository).list_sessions(limit=20, user_id="telegram_1")

        self.assertEqual(
            repository.calls,
            [("get_chat_sessions", 20, "telegram_1", ["telegram_1"])],
        )

    def test_no_user_id_keeps_extra_ids_empty(self) -> None:
        repository = FakeConversationRepository()
        self._service(repository).list_sessions(limit=50)

        self.assertEqual(repository.calls, [("get_chat_sessions", 50, None, None)])

    def test_explicit_extra_ids_override_the_default(self) -> None:
        repository = FakeConversationRepository()
        self._service(repository).list_sessions(
            limit=10, user_id="feishu_u1:", extra_session_ids=["feishu_u1"]
        )

        self.assertEqual(
            repository.calls,
            [("get_chat_sessions", 10, "feishu_u1:", ["feishu_u1"])],
        )

    def test_empty_extra_ids_are_normalized_to_none(self) -> None:
        repository = FakeConversationRepository()
        self._service(repository).list_sessions(limit=10, user_id="feishu_u1:", extra_session_ids=[])

        self.assertEqual(repository.calls, [("get_chat_sessions", 10, "feishu_u1:", None)])

    def test_session_exists_is_forwarded(self) -> None:
        repository = FakeConversationRepository(existing_sessions=["telegram_1"])
        service = self._service(repository)

        self.assertTrue(service.session_exists("telegram_1"))
        self.assertFalse(service.session_exists("telegram_2"))
        self.assertEqual(
            repository.calls,
            [
                ("conversation_session_exists", "telegram_1"),
                ("conversation_session_exists", "telegram_2"),
            ],
        )


class HistoryCommandUseCaseTestCase(unittest.TestCase):
    """``/history`` 的三种分支改走用例后参数与文案不变。"""

    def test_list_branch_passes_prefix_and_legacy_session_id(self) -> None:
        sessions = [
            {
                "session_id": "feishu_u1:chat",
                "title": "示例会话",
                "message_count": 2,
                "last_active": "2026-10-25T10:00:00",
            }
        ]
        repository = FakeConversationRepository(sessions=sessions)
        service = AgentConversationService(repository=repository)

        with patch("bot.commands.history.build_agent_conversation_service", return_value=service):
            response = HistoryCommand().execute(_message("/history"), [])

        self.assertIn("示例会话", response.text)
        # 前缀带冒号（防串号），legacy 会话 id 作为精确 id 追加。
        self.assertEqual(
            repository.calls,
            [("get_chat_sessions", 10, "feishu_u1:", ["feishu_u1"])],
        )

    def test_list_branch_clamps_count_and_keeps_limit(self) -> None:
        repository = FakeConversationRepository(sessions=[{"session_id": "feishu_u1:chat"}])
        service = AgentConversationService(repository=repository)

        with patch("bot.commands.history.build_agent_conversation_service", return_value=service):
            HistoryCommand().execute(_message("/history 999"), ["999"])

        self.assertEqual(repository.calls[0][:2], ("get_chat_sessions", 50))

    def test_detail_branch_rejects_foreign_session(self) -> None:
        repository = FakeConversationRepository(messages=[{"role": "user", "content": "hi"}])
        service = AgentConversationService(repository=repository)

        with patch("bot.commands.history.build_agent_conversation_service", return_value=service):
            response = HistoryCommand().execute(
                _message("/history telegram_9:chat"), ["telegram_9:chat"]
            )

        self.assertIn("只能查看自己的会话记录", response.text)
        self.assertEqual(repository.calls, [])

    def test_detail_branch_reads_messages_with_20_limit(self) -> None:
        repository = FakeConversationRepository(
            messages=[{"role": "user", "content": "你好", "created_at": "2026-10-25T10:00:00"}]
        )
        service = AgentConversationService(repository=repository)

        with patch("bot.commands.history.build_agent_conversation_service", return_value=service):
            response = HistoryCommand().execute(_message("/history feishu_u1:chat"), ["feishu_u1:chat"])

        self.assertIn("你好", response.text)
        self.assertEqual(repository.calls, [("get_conversation_messages", "feishu_u1:chat", 20)])

    def test_clear_branch_deletes_current_and_legacy_when_private(self) -> None:
        repository = FakeConversationRepository(deleted=1)
        service = AgentConversationService(repository=repository)

        with patch("bot.commands.history.build_agent_conversation_service", return_value=service):
            response = HistoryCommand().execute(_message("/history clear"), ["clear"])

        self.assertIn("2 条消息", response.text)
        self.assertEqual(
            repository.calls,
            [
                ("delete_conversation_session", "feishu_u1:chat"),
                ("delete_conversation_session", "feishu_u1"),
            ],
        )

    def test_storage_unavailable_keeps_friendly_message(self) -> None:
        with patch(
            "bot.commands.history.build_agent_conversation_service",
            side_effect=RuntimeError("db down"),
        ):
            response = HistoryCommand().execute(_message("/history"), [])

        self.assertIn("存储模块不可用", response.text)


class ChatCommandUseCaseTestCase(unittest.TestCase):
    """``/chat`` 的 legacy 会话兼容判定改走用例，降级行为不变。"""

    def test_failed_service_construction_falls_back_to_scoped_session_id(self) -> None:
        executor = MagicMock()
        executor.chat.return_value = type(
            "R", (), {"success": True, "content": "ok", "error": None}
        )()

        with patch("bot.commands.chat.get_config", return_value=type("C", (), {"agent_mode": True})()), \
             patch(
                 "bot.commands.chat.build_agent_conversation_service",
                 side_effect=RuntimeError("db down"),
             ), \
             patch("src.bootstrap.agent.build_agent_executor", return_value=executor):
            response = ChatCommand().execute(_message("/chat hello"), ["hello"])

        self.assertEqual(response.text, "ok")
        # 判定失败时退回带作用域的 session id，不影响主流程。
        self.assertEqual(executor.chat.call_args.kwargs["session_id"], "feishu_u1:chat")


class CanonicalStockCodeWrapperTestCase(unittest.TestCase):
    """Bot 使用的薄包装与数据源函数、分析侧包装同源同语义。"""

    def test_input_wrapper_matches_provider_function(self) -> None:
        samples = (
            "600519",
            "600519.SH",
            "sh600519",
            "hk00700",
            "aapl",
            "AAPL.US",
            " abc ",
            "",
            None,
        )
        for raw in samples:
            self.assertEqual(canonical_stock_code_for_input(raw), canonical_stock_code(raw or ""), raw)

    def test_input_and_analysis_wrappers_agree(self) -> None:
        samples = ("600519", "600519.SH", "hk00700", "aapl", "ABC", "", None)
        for raw in samples:
            self.assertEqual(
                canonical_stock_code_for_input(raw),
                canonical_stock_code_for_analysis(raw),
                raw,
            )


if __name__ == "__main__":
    unittest.main()
