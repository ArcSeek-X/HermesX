# -*- coding: utf-8 -*-
"""LLM 用量用例的装配。

仓储实现复用 ``src.infrastructure.persistence.repositories.llm_usage_repo``，
本模块只负责把当前进程的数据库单例绑定进用例。
"""

from __future__ import annotations

from src.application.usage import UsageService
from src.infrastructure.persistence.repositories.llm_usage_repo import LLMUsageRepository
from src.storage import DatabaseManager


def build_usage_service() -> UsageService:
    """按当前数据库单例装配 LLM 用量用例。

    用例无状态，每次构造都能绑定到最新的 ``DatabaseManager`` 实例。
    """
    return UsageService(LLMUsageRepository(DatabaseManager.get_instance()))
