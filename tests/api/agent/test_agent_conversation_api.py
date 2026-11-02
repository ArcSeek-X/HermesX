# -*- coding: utf-8 -*-
"""Agent 会话路由的依赖接线与契约回归测试。

``api/v1/endpoints/agent.py`` 的三个会话路由曾各自在函数体内 ``from src.storage
import get_db`` 直连持久化层。现在它们只依赖 ``Depends(get_agent_conversation_service)``，
装配收敛到 ``src.bootstrap.agent``，用例落在 ``src.application.agent``。本文件锁定
这条契约与参数语义，避免回退。
"""

from __future__ import annotations

import asyncio
import inspect
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from api.deps import get_agent_conversation_service
from api.v1.endpoints import agent
from src.application.agent import AgentConversationService


def _run(coro):
    """在同步测试里执行端点协程。"""
    return asyncio.run(coro)


class FakeConversationRepository:
    """记录调用参数的端口替身。"""

    def __init__(
        self,
        sessions: Optional[List[Dict[str, Any]]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        deleted: int = 0,
    ) -> None:
        self.sessions = sessions or []
        self.messages = messages or []
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

    def delete_conversation_session(self, session_id: str) -> int:
        self.calls.append(("delete_conversation_session", session_id))
        return self.deleted


class AgentConversationRouteWiringTestCase(unittest.TestCase):
    def test_endpoint_module_does_not_touch_storage(self) -> None:
        source = Path(agent.__file__).read_text(encoding="utf-8")
        self.assertNotIn("src.storage", source)
        self.assertNotIn("get_db()", source)

    def test_session_routes_inject_the_conversation_service_dependency(self) -> None:
        matched = [
            route
            for route in agent.router.routes
            if hasattr(route, "endpoint")
            and route.endpoint.__name__
            in ("list_chat_sessions", "get_chat_session_messages", "delete_chat_session")
        ]
        self.assertEqual(len(matched), 3, "必须恰好存在三个会话路由")
        for route in matched:
            parameters = inspect.signature(route.endpoint).parameters
            self.assertIn(
                "service",
                parameters,
                f"{route.path} 必须通过依赖注入获取用例",
            )
            dependency = parameters["service"].default
            self.assertIs(
                getattr(dependency, "dependency", None),
                get_agent_conversation_service,
                f"{route.path} 必须依赖 api.deps.get_agent_conversation_service",
            )

    def test_bootstrap_binds_repository_to_current_database_manager(self) -> None:
        from src.bootstrap.agent import build_agent_conversation_service
        from src.infrastructure.persistence.repositories.conversation_repo import (
            ConversationRepository,
        )

        manager = MagicMock(name="DatabaseManager")
        with patch(
            "src.bootstrap.agent.DatabaseManager.get_instance",
            return_value=manager,
        ):
            service = build_agent_conversation_service()

        self.assertIsInstance(service, AgentConversationService)
        repository = service._repository
        self.assertIsInstance(repository, ConversationRepository)
        self.assertIs(repository._db, manager)


class AgentConversationEndpointTestCase(unittest.TestCase):
    def test_list_sessions_forwards_limit_and_user_scope(self) -> None:
        service = MagicMock()
        service.list_sessions.return_value = [
            {
                "session_id": "telegram_1",
                "title": "hi",
                "message_count": 2,
                "created_at": None,
                "last_active": None,
            }
        ]

        response = _run(
            agent.list_chat_sessions(limit=5, user_id="telegram_1", service=service)
        )

        service.list_sessions.assert_called_once_with(limit=5, user_id="telegram_1")
        self.assertEqual(response.sessions[0].session_id, "telegram_1")
        self.assertEqual(response.sessions[0].message_count, 2)

    def test_get_messages_echoes_session_id(self) -> None:
        service = MagicMock()
        service.get_messages.return_value = [{"id": "1", "role": "user", "content": "x"}]

        response = _run(
            agent.get_chat_session_messages(session_id="s1", limit=7, service=service)
        )

        service.get_messages.assert_called_once_with("s1", limit=7)
        self.assertEqual(response.session_id, "s1")
        self.assertEqual(len(response.messages), 1)

    def test_delete_session_returns_deleted_count(self) -> None:
        service = MagicMock()
        service.delete_session.return_value = 4

        response = _run(agent.delete_chat_session(session_id="s1", service=service))

        service.delete_session.assert_called_once_with("s1")
        self.assertEqual(response, {"deleted": 4})


class AgentConversationServiceTestCase(unittest.TestCase):
    def test_user_id_becomes_prefix_and_exact_session_id(self) -> None:
        repository = FakeConversationRepository()
        service = AgentConversationService(repository)

        service.list_sessions(limit=20, user_id="telegram_1")

        self.assertEqual(
            repository.calls,
            [("get_chat_sessions", 20, "telegram_1", ["telegram_1"])],
        )

    def test_absent_user_id_does_not_scope_sessions(self) -> None:
        repository = FakeConversationRepository()
        service = AgentConversationService(repository)

        service.list_sessions()

        self.assertEqual(repository.calls, [("get_chat_sessions", 50, None, None)])

    def test_get_messages_forwards_limit(self) -> None:
        repository = FakeConversationRepository(messages=[{"id": "1"}])
        service = AgentConversationService(repository)

        messages = service.get_messages("s1", limit=3)

        self.assertEqual(repository.calls, [("get_conversation_messages", "s1", 3)])
        self.assertEqual(messages, [{"id": "1"}])

    def test_delete_session_returns_repository_count(self) -> None:
        repository = FakeConversationRepository(deleted=2)
        service = AgentConversationService(repository)

        self.assertEqual(service.delete_session("s1"), 2)
        self.assertEqual(repository.calls, [("delete_conversation_session", "s1")])


if __name__ == "__main__":
    unittest.main()
