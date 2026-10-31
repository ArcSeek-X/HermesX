# -*- coding: utf-8 -*-
"""LLM usage tracking endpoint.

传输层：只做 Query 校验、调用用例、把结果映射成响应模型。
时间窗语义与读模型组装在 ``src.application.usage.UsageService``。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_usage_service
from api.v1.schemas.usage import UsageDashboardResponse, UsageSummaryResponse
from src.application.usage import UsageService

router = APIRouter()


@router.get(
    "/summary",
    response_model=UsageSummaryResponse,
    summary="LLM token usage summary",
    description="Aggregate token consumption by period, call type, and model.",
)
def get_usage_summary(
    period: str = Query("month", description="'today' | 'month' | 'all'"),
    service: UsageService = Depends(get_usage_service),
) -> UsageSummaryResponse:
    return UsageSummaryResponse(**service.get_summary(period))


@router.get(
    "/dashboard",
    response_model=UsageDashboardResponse,
    summary="LLM token usage monitoring dashboard",
    description="Return token totals, model breakdowns, and recent LLM call records.",
)
def get_usage_dashboard(
    period: str = Query("month", description="'today' | 'month' | 'all'"),
    limit: int = Query(50, ge=1, le=200, description="Recent call records to include"),
    service: UsageService = Depends(get_usage_service),
) -> UsageDashboardResponse:
    return UsageDashboardResponse(**service.get_dashboard(period, limit))
