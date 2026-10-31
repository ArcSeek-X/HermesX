# -*- coding: utf-8 -*-
"""Agent 会话用例。

把原先散在 ``api/v1/endpoints/agent.py`` 与 ``bot/commands/{chat,history}.py`` 里的
``get_db()`` 直连收敛成用例调用。驱动层只负责入参透传与响应包装；``user_id`` 的
「前缀隔离 + 精确包含」语义在这里表达，避免以后每个调用方各自拼参数。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application.agent.ports import AgentConversationPort


class AgentConversationService:
    """对话会话的读取与删除。"""

    def __init__(self, repository: AgentConversationPort) -> None:
        self._repository = repository

    def list_sessions(
        self,
        *,
        limit: int = 50,
        user_id: Optional[str] = None,
        extra_session_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """按最近活跃时间倒序列出会话。

        ``user_id`` 带平台前缀（如 ``telegram_12345``）：既作为前缀过滤，也作为精确
        session_id 一并纳入，保证「该用户的会话」不会因为前缀相同而被漏掉或串号。

        ``extra_session_ids`` 供调用方追加自己的精确 id（如 Bot 需要兼容迁移前的
        legacy 会话 id）。不传时沿用「只追加 ``user_id`` 自身」的默认行为；传了则
        以调用方给出的集合为准，前缀过滤不变。
        """
        if extra_session_ids is None:
            extra_session_ids = [user_id] if user_id else None
        return self._repository.get_chat_sessions(
            limit=limit,
            session_prefix=user_id,
            extra_session_ids=list(extra_session_ids) if extra_session_ids else None,
        )

    def get_messages(self, session_id: str, *, limit: int = 100) -> List[Dict[str, Any]]:
        """读取单个会话的消息列表（供前端恢复历史）。"""
        return self._repository.get_conversation_messages(session_id, limit=limit)

    def delete_session(self, session_id: str) -> int:
        """删除单个会话的全部消息，返回删除条数（会话不存在时为 0）。"""
        return self._repository.delete_conversation_session(session_id)

    def session_exists(self, session_id: str) -> bool:
        """会话下至少有一条消息时返回 True（供 Bot 做历史兼容判定）。"""
        return self._repository.conversation_session_exists(session_id)
