# -*- coding: utf-8 -*-
"""LLM 用量用例。

职责边界：

- 时间窗语义（``today`` / ``month`` / ``all``，北京时间）与非法取值回退到 ``month``；
- 把仓储聚合结果组装成对外的读模型（含日期区间与 ``recent_calls`` 的时间序列化）；
- 不感知 HTTP：Query 校验、Schema 过滤与响应模型由 ``api`` 层负责。

时间源通过构造参数注入，便于在测试里固定「当前时间」而不 patch 模块全局。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Tuple

from src.application.usage.ports import UsageRepositoryPort

_CST = timezone(timedelta(hours=8))  # Beijing time (UTC+8)

_VALID_PERIODS = {"today", "month", "all"}


def _beijing_now() -> datetime:
    """当前北京时间，去掉 tzinfo 以匹配库中的 naive datetime。"""
    return datetime.now(tz=_CST).replace(tzinfo=None)


class UsageService:
    """LLM token 用量的查询用例。"""

    def __init__(
        self,
        repository: UsageRepositoryPort,
        *,
        now: Callable[[], datetime] = _beijing_now,
    ) -> None:
        self._repository = repository
        self._now = now

    def get_summary(self, period: str) -> Dict[str, Any]:
        """按周期返回 token 总量与按调用类型 / 模型的聚合。"""
        normalized, from_dt, to_dt = self._resolve_period(period)
        data = self._repository.get_llm_usage_summary(from_dt, to_dt)
        return _build_summary_payload(normalized, from_dt, to_dt, data)

    def get_dashboard(self, period: str, limit: int) -> Dict[str, Any]:
        """在 summary 基础上附带最近的调用明细。"""
        normalized, from_dt, to_dt = self._resolve_period(period)
        data = self._repository.get_llm_usage_summary(from_dt, to_dt)
        records = self._repository.get_llm_usage_records(from_dt, to_dt, limit=limit)
        payload = _build_summary_payload(normalized, from_dt, to_dt, data)
        payload["recent_calls"] = [_enrich_call_record(row) for row in records]
        return payload

    def _resolve_period(self, period: str) -> Tuple[str, datetime, datetime]:
        normalized = period if period in _VALID_PERIODS else "month"
        now = self._now()
        if normalized == "today":
            from_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif normalized == "month":
            from_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # all
            from_dt = datetime(2000, 1, 1)
        return normalized, from_dt, now


def _enrich_call_record(row: Dict[str, Any]) -> Dict[str, Any]:
    """把明细行的 ``called_at`` 统一成 ISO 字符串（其余字段原样透传）。"""
    called_at = row.get("called_at")
    if isinstance(called_at, datetime):
        called_at_value = called_at.isoformat()
    else:
        called_at_value = str(called_at or "")
    return {
        **row,
        "called_at": called_at_value,
    }


def _build_summary_payload(
    period: str,
    from_dt: datetime,
    to_dt: datetime,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "period": period,
        "from_date": from_dt.date().isoformat(),
        "to_date": to_dt.date().isoformat(),
        "total_calls": data.get("total_calls", 0),
        "total_prompt_tokens": data.get("total_prompt_tokens", 0),
        "total_completion_tokens": data.get("total_completion_tokens", 0),
        "total_tokens": data.get("total_tokens", 0),
        "by_call_type": data.get("by_call_type", []),
        "by_model": data.get("by_model", []),
    }
