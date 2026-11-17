# -*- coding: utf-8 -*-
"""
@file: usage.py
@description: LLM 用量统计端点：提供汇总与看板两个只读接口；由 api.v1.router 挂到 /api/v1/usage，数据来自 src.application.usage.UsageService。
@author: Lensgcx (GaoCangxiong)

LLM usage tracking endpoint.

Exposes aggregate token consumption and a dashboard view that also
includes recent per-call records.

传输层：只做 Query 校验、调用用例、把结果映射成响应模型。
时间窗语义与读模型组装在 ``src.application.usage.UsageService``。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_usage_service
from api.v1.schemas.usage import UsageDashboardResponse, UsageSummaryResponse
from src.application.usage import UsageService

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/usage。
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
    """获取指定统计周期内的 LLM 用量汇总。

    统计区间由服务层按 period 推导并回传，前端不按本地时区自行计算。

    Args:
        period: 统计周期 today / month / all，默认 month。
        service: 用量查询用例，由 Depends(get_usage_service) 按请求装配。

    Returns:
        UsageSummaryResponse: 总量与按调用类型、按模型的分项汇总。

    Side Effects:
        仅读取用量记录，不产生写入。
    """
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
    """获取用量看板数据：汇总指标加最近调用明细。

    一次请求即可渲染看板全部区块，避免前端再发一次明细查询。

    Args:
        period: 统计周期 today / month / all，默认 month。
        limit: 返回的最近调用条数，范围 1~200，默认 50。
        service: 用量查询用例，由 Depends(get_usage_service) 按请求装配。

    Returns:
        UsageDashboardResponse: 继承汇总字段并附带 recent_calls。

    Side Effects:
        仅读取用量记录，不产生写入。
    """
    return UsageDashboardResponse(**service.get_dashboard(period, limit))
