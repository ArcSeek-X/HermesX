# -*- coding: utf-8 -*-
"""Schemas for LLM usage tracking API.

LLM 用量追踪接口的 Pydantic 请求/响应模型，含按调用类型与模型的分项汇总、单次调用记录及看板响应。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CallTypeBreakdown(BaseModel):
    """按调用类型（analysis / agent / market_review）汇总的用量与 token 数。"""

    call_type: str = Field(..., description="'analysis' | 'agent' | 'market_review'")
    calls: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int


class ModelBreakdown(BaseModel):
    """按模型汇总的调用次数与 prompt/completion token 数。"""

    model: str
    calls: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int
    max_total_tokens: int = 0


class UsageCallRecord(BaseModel):
    """单次 LLM 调用的明细记录（时间、类型、模型、token 与耗时等）。"""

    id: int
    called_at: str = Field(..., description="ISO datetime string")
    call_type: str
    model: str
    stock_code: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class UsageSummaryResponse(BaseModel):
    """用量汇总响应：统计周期、日期区间、总调用次数与分项明细。"""

    period: str = Field(..., description="'today' | 'month' | 'all'")
    from_date: str = Field(..., description="ISO date string")
    to_date: str = Field(..., description="ISO date string")
    total_calls: int
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int
    by_call_type: List[CallTypeBreakdown]
    by_model: List[ModelBreakdown]


class UsageDashboardResponse(UsageSummaryResponse):
    """用量看板响应：在汇总基础上附带最近的调用明细列表。"""

    recent_calls: List[UsageCallRecord]
