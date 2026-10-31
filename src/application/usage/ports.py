# -*- coding: utf-8 -*-
"""LLM 用量用例的端口定义。

实现方：``src.infrastructure.persistence.repositories.llm_usage_repo.LLMUsageRepository``
（结构匹配，无需额外适配器）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Protocol


class UsageRepositoryPort(Protocol):
    """``llm_usage`` 的只读聚合能力。"""

    def get_llm_usage_summary(
        self,
        from_dt: datetime,
        to_dt: datetime,
    ) -> Dict[str, Any]:
        """返回时间窗内的总量、按调用类型与按模型的聚合结果。"""

    def get_llm_usage_records(
        self,
        from_dt: datetime,
        to_dt: datetime,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """返回时间窗内最近的调用明细，按 ``called_at`` 倒序。"""
