# -*- coding: utf-8 -*-
"""
@file: backtest.py
@description: 回测端点：触发回测、查询回测结果列表、查询全市场与单股表现指标；由 api.v1.router 挂到 /api/v1/backtest，计算与持久化在 src.application.backtest.service.BacktestService。
@author: Lensgcx (GaoCangxiong)

Backtest endpoints.

Exposes synchronous evaluation runs, paginated result queries
and performance summaries scoped to the whole market or one symbol.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_backtest_service
from api.v1.schemas.backtest import (
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestResultItem,
    BacktestResultsResponse,
    PerformanceMetrics,
)
from api.v1.schemas.common import ErrorResponse
from src.application.backtest.service import BacktestService

# 模块级日志器，记录回测执行与查询失败。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/backtest。
router = APIRouter()

# 分析阶段查询取值：premarket / intraday / postmarket / unknown；unknown 覆盖旧数据无阶段字段的记录。
BacktestAnalysisPhaseQuery = Literal["premarket", "intraday", "postmarket", "unknown"]


def _validate_analysis_date_range(
    analysis_date_from: Optional[date],
    analysis_date_to: Optional[date],
) -> None:
    """校验分析日期区间合法性。

    仅在两个端点都提供时比较，单边开放区间合法；错误体采用统一 error/message 格式供前端解析。

    Args:
        analysis_date_from: 起始日期（含），可为 None。
        analysis_date_to: 结束日期（含），可为 None。

    Returns:
        None。

    Raises:
        HTTPException: 起始晚于结束时返回 400 invalid_params。
    """
    if analysis_date_from and analysis_date_to and analysis_date_from > analysis_date_to:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_params",
                "message": "analysis_date_from cannot be after analysis_date_to",
            },
        )


@router.post(
    "/run",
    response_model=BacktestRunResponse,
    responses={
        200: {"description": "回测执行完成"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="触发回测",
    description="对历史分析记录进行回测评估，并写入 backtest_results/backtest_summaries",
)
def run_backtest(
    request: BacktestRunRequest,
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestRunResponse:
    """执行回测任务。

    把请求参数透传给服务层并写入回测结果/汇总；ValueError 映射 400、HTTPException 原样透传、其余异常映射 500。

    Args:
        request: 回测运行参数（代码、窗口、日期区间、条数上限等）。
        service: 回测服务，由 Depends(get_backtest_service) 按请求装配。

    Returns:
        BacktestRunResponse: 处理/写入/完成/数据不足/错误的计数与诊断信息。

    Raises:
        HTTPException: 参数非法 400、服务异常 500。

    Side Effects:
        写入 backtest_results 与 backtest_summaries。
    """
    try:
        _validate_analysis_date_range(request.analysis_date_from, request.analysis_date_to)
        stats = service.run_backtest(
            code=request.code,
            force=request.force,
            eval_window_days=request.eval_window_days,
            min_age_days=request.min_age_days,
            analysis_date_from=request.analysis_date_from,
            analysis_date_to=request.analysis_date_to,
            limit=request.limit,
        )
        return BacktestRunResponse(**stats)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_params", "message": str(exc)},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"回测执行失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"回测执行失败: {str(exc)}"},
        )


@router.get(
    "/results",
    response_model=BacktestResultsResponse,
    responses={
        200: {"description": "回测结果列表"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取回测结果",
    description="分页获取回测结果，支持按股票代码过滤",
)
def get_backtest_results(
    code: Optional[str] = Query(None, description="股票代码筛选"),
    eval_window_days: Optional[int] = Query(None, ge=1, le=120, description="评估窗口过滤"),
    analysis_date_from: Optional[date] = Query(None, description="分析日期起始（含）"),
    analysis_date_to: Optional[date] = Query(None, description="分析日期结束（含）"),
    analysis_phase: Optional[BacktestAnalysisPhaseQuery] = Query(None, description="分析阶段过滤：premarket/intraday/postmarket/unknown"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=200, description="每页数量"),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestResultsResponse:
    """查询回测结果列表。

    所有筛选条件可组合，日期区间先经统一校验；响应中的 page/limit 回传请求值，便于前端拼装分页状态。

    Args:
        code: 股票代码过滤；None 表示不限。
        eval_window_days: 评估窗口过滤，范围 1~120。
        analysis_date_from: 分析日期起始（含）。
        analysis_date_to: 分析日期结束（含）。
        analysis_phase: 分析阶段过滤 premarket/intraday/postmarket/unknown。
        page: 页码，从 1 开始。
        limit: 每页条数，范围 1~200，默认 20。
        service: 回测服务，由 Depends(get_backtest_service) 装配。

    Returns:
        BacktestResultsResponse: 总数、当前页参数与结果列表。

    Raises:
        HTTPException: 参数/区间非法 400、查询异常 500。
    """
    try:
        _validate_analysis_date_range(analysis_date_from, analysis_date_to)
        data = service.get_recent_evaluations(
            code=code,
            eval_window_days=eval_window_days,
            limit=limit,
            page=page,
            analysis_date_from=analysis_date_from,
            analysis_date_to=analysis_date_to,
            analysis_phase=analysis_phase,
        )
        items = [BacktestResultItem(**item) for item in data.get("items", [])]
        return BacktestResultsResponse(
            total=int(data.get("total", 0)),
            page=page,
            limit=limit,
            items=items,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_params", "message": str(exc)},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"查询回测结果失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"查询回测结果失败: {str(exc)}"},
        )


@router.get(
    "/performance",
    response_model=PerformanceMetrics,
    responses={
        200: {"description": "整体回测表现"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        404: {"description": "无回测汇总", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取整体回测表现",
)
def get_overall_performance(
    eval_window_days: Optional[int] = Query(None, ge=1, le=120, description="评估窗口过滤"),
    analysis_date_from: Optional[date] = Query(None, description="分析日期起始（含）"),
    analysis_date_to: Optional[date] = Query(None, description="分析日期结束（含）"),
    analysis_phase: Optional[BacktestAnalysisPhaseQuery] = Query(None, description="分析阶段过滤：premarket/intraday/postmarket/unknown"),
    service: BacktestService = Depends(get_backtest_service),
) -> PerformanceMetrics:
    """查询整体回测表现。

    以 scope=overall 读取已落库的汇总；没有汇总时返回 404，而不是用全零指标掩盖「尚未回测」。

    Args:
        eval_window_days: 评估窗口过滤，范围 1~120。
        analysis_date_from: 分析日期起始（含）。
        analysis_date_to: 分析日期结束（含）。
        analysis_phase: 分析阶段过滤。
        service: 回测服务，由 Depends(get_backtest_service) 装配。

    Returns:
        PerformanceMetrics: 全市场范围的胜率、方向准确率与触发率等。

    Raises:
        HTTPException: 参数非法 400、无汇总 404、查询异常 500。
    """
    try:
        _validate_analysis_date_range(analysis_date_from, analysis_date_to)
        summary = service.get_summary(
            scope="overall",
            code=None,
            eval_window_days=eval_window_days,
            analysis_date_from=analysis_date_from,
            analysis_date_to=analysis_date_to,
            analysis_phase=analysis_phase,
        )
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "未找到整体回测汇总"},
            )
        return PerformanceMetrics(**summary)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_params", "message": str(exc)},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"查询整体表现失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"查询整体表现失败: {str(exc)}"},
        )


@router.get(
    "/performance/{code}",
    response_model=PerformanceMetrics,
    responses={
        200: {"description": "单股回测表现"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        404: {"description": "无回测汇总", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取单股回测表现",
)
def get_stock_performance(
    code: str,
    eval_window_days: Optional[int] = Query(None, ge=1, le=120, description="评估窗口过滤"),
    analysis_date_from: Optional[date] = Query(None, description="分析日期起始（含）"),
    analysis_date_to: Optional[date] = Query(None, description="分析日期结束（含）"),
    analysis_phase: Optional[BacktestAnalysisPhaseQuery] = Query(None, description="分析阶段过滤：premarket/intraday/postmarket/unknown"),
    service: BacktestService = Depends(get_backtest_service),
) -> PerformanceMetrics:
    """查询单只股票回测表现。

    与整体表现共用指标模型，仅 scope 与 code 不同；无汇总时 404 并在消息中带上股票代码便于定位。

    Args:
        code: 股票代码，来自路径参数。
        eval_window_days: 评估窗口过滤，范围 1~120。
        analysis_date_from: 分析日期起始（含）。
        analysis_date_to: 分析日期结束（含）。
        analysis_phase: 分析阶段过滤。
        service: 回测服务，由 Depends(get_backtest_service) 装配。

    Returns:
        PerformanceMetrics: 单股范围的回测表现指标。

    Raises:
        HTTPException: 参数非法 400、无汇总 404、查询异常 500。
    """
    try:
        _validate_analysis_date_range(analysis_date_from, analysis_date_to)
        summary = service.get_summary(
            scope="stock",
            code=code,
            eval_window_days=eval_window_days,
            analysis_date_from=analysis_date_from,
            analysis_date_to=analysis_date_to,
            analysis_phase=analysis_phase,
        )
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"未找到 {code} 的回测汇总"},
            )
        return PerformanceMetrics(**summary)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_params", "message": str(exc)},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"查询单股表现失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"查询单股表现失败: {str(exc)}"},
        )
