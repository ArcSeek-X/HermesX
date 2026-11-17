# -*- coding: utf-8 -*-
"""Agent 会话用例的端口定义。

端口只描述用例真正需要的 4 个能力：会话列表、单会话消息、会话是否存在、按会话删除。
实现方是
``src.infrastructure.persistence.repositories.conversation_repo.ConversationRepository``；
端口按结构匹配（``Protocol``），不要求显式继承，测试可直接传假对象。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class AgentConversationPort(Protocol):
    """对话消息的读取与按会话删除能力。"""

    def get_chat_sessions(
        self,
        limit: int = 50,
        session_prefix: Optional[str] = None,
        extra_session_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """返回按最近活跃时间倒序的会话列表。"""

    def get_conversation_messages(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """返回指定会话的消息列表（按创建时间升序）。"""

    def conversation_session_exists(self, session_id: str) -> bool:
        """会话下至少有一条消息时返回 True。"""

    def delete_conversation_session(self, session_id: str) -> int:
        """删除指定会话的全部消息，返回删除条数。"""


class ConversationMessagePort(Protocol):
    """对话消息的读写能力（供 ``ConversationSession`` 使用）。

    实现方同样是
    ``src.infrastructure.persistence.repositories.conversation_repo.ConversationRepository``；
    端口按结构匹配，测试可直接传假对象。
    """

    def save_conversation_message(self, session_id: str, role: str, content: str) -> int:
        """追加一条消息并返回消息 id。"""

    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """返回指定会话的消息历史（按创建时间升序）。"""


class ChatContextPort(Protocol):
    """构建与压缩对话上下文所需的会话/轨迹读写能力。

    实现方同样是
    ``src.infrastructure.persistence.repositories.conversation_repo.ConversationRepository``；
    端口按结构匹配，测试可直接传假对象。读侧供可见历史与 provider 轨迹拼装，
    写侧仅用于上下文压缩摘要的落库（``upsert_conversation_summary``）。
    """

    def get_agent_provider_turns(
        self,
        session_id: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        must_roundtrip_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """返回会话的 provider 轨迹轮次。"""

    def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """返回会话的压缩摘要记录（无则为 None）。"""

    def get_visible_conversation_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """返回用户可见的会话消息（user/assistant）。"""

    def upsert_conversation_summary(
        self,
        session_id: str,
        summary: str,
        covered_message_id: int,
        source_message_count: int,
        estimated_tokens: int,
    ) -> None:
        """写入（或更新）会话的上下文压缩摘要。"""
