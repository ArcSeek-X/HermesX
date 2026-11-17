# -*- coding: utf-8 -*-
"""
@file: alerts.py
@description: 告警端点：规则的增删改查、启用/停用、试运行，以及触发记录与通知记录的分页查询；由 api.v1.router 挂到 /api/v1/alerts，业务规则在告警服务层。
@author: Lensgcx (GaoCangxiong)

Alert API endpoints (Issue #1202 P1 MVP).

告警规则的增删改查与启用/停用/测试端点，以及触发记录、通知记录的分页查询。
统一把服务层异常映射为 400/404/500 的标准错误响应。
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.alerts import (
    AlertDeleteResponse,
    AlertNotificationListResponse,
    AlertRuleCreateRequest,
    AlertRuleItem,
    AlertRuleListResponse,
    AlertRuleTestResponse,
    AlertRuleUpdateRequest,
    AlertTriggerListResponse,
)
from api.v1.schemas.common import ErrorResponse
from src.application.alert.service import (
    AlertNotFoundError,
    AlertServiceError,
    UnsupportedAlertTypeError,
)
from src.bootstrap.alert import build_alert_service

# 模块级日志器，记录告警服务层异常及其堆栈。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/alerts。
router = APIRouter()


def _bad_request(exc: Exception, *, error: str = "validation_error") -> HTTPException:
    """把参数/校验异常转换为 400 错误响应。

    Args:
        exc: 服务层抛出的参数或校验异常。
        error: 写入响应体的机器可识别错误码。

    Returns:
        HTTPException: 400 错误对象。

    Side Effects:
        无；仅构造异常对象。
    """
    return HTTPException(
        status_code=400,
        detail={"error": error, "message": str(exc)},
    )


def _not_found(exc: Exception) -> HTTPException:
    """把「资源不存在」异常转换为 404 错误响应。

    Args:
        exc: 服务层抛出的资源不存在异常。

    Returns:
        HTTPException: 404 错误对象。
    """
    return HTTPException(
        status_code=404,
        detail={"error": "not_found", "message": str(exc)},
    )


def _internal_error(message: str, exc: Exception) -> HTTPException:
    """记录异常日志并返回不泄露内部细节的 500 错误响应。

    Args:
        message: 写入日志的上下文说明。
        exc: 原始异常对象，堆栈只进日志。

    Returns:
        HTTPException: 500 错误对象。

    Side Effects:
        写一条带堆栈的 ERROR 级日志。
    """
    logger.error("%s: %s", message, exc, exc_info=True)
    return HTTPException(
        status_code=500,
        detail={"error": "internal_error", "message": f"{message}: {str(exc)}"},
    )


@router.post(
    "/rules",
    response_model=AlertRuleItem,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Create alert rule",
)
def create_rule(request: AlertRuleCreateRequest) -> AlertRuleItem:
    """创建一条告警规则并返回创建后的规则详情。

    Args:
        request: 规则创建请求体。

    Returns:
        AlertRuleItem: 落库后的完整规则。

    Raises:
        HTTPException: 参数/校验错误 400、服务异常 500。

    Side Effects:
        写入告警规则记录。
    """
    service = build_alert_service()
    try:
        return AlertRuleItem(**service.create_rule(request.model_dump()))
    except UnsupportedAlertTypeError as exc:
        raise _bad_request(exc, error=exc.error_code)
    except AlertServiceError as exc:
        raise _bad_request(exc, error=exc.error_code)
    except Exception as exc:
        raise _internal_error("Create alert rule failed", exc)


@router.get(
    "/rules",
    response_model=AlertRuleListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List alert rules",
)
def list_rules(
    enabled: Optional[bool] = Query(None, description="Optional enabled filter"),
    alert_type: Optional[str] = Query(None, description="Optional alert type filter"),
    target_scope: Optional[str] = Query(None, description="Optional target scope filter"),
    target: Optional[str] = Query(None, description="Optional target filter"),
    source: Optional[str] = Query(None, description="Optional source filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AlertRuleListResponse:
    """分页查询告警规则，支持启用状态、类型、目标范围、目标与来源过滤。

    Args:
        enabled: 启用状态过滤；None 表示不过滤。
        alert_type: 告警类型过滤。
        target_scope: 求值范围过滤。
        target: 求值目标过滤。
        source: 规则来源过滤。
        page: 页码，从 1 开始。
        page_size: 每页条数。

    Returns:
        AlertRuleListResponse: 当前页规则与总数。

    Raises:
        HTTPException: 查询异常 500。
    """
    service = build_alert_service()
    try:
        return AlertRuleListResponse(
            **service.list_rules(
                enabled=enabled,
                alert_type=alert_type,
                target_scope=target_scope,
                target=target,
                source=source,
                page=page,
                page_size=page_size,
            )
        )
    except Exception as exc:
        raise _internal_error("List alert rules failed", exc)


@router.get(
    "/rules/{rule_id}",
    response_model=AlertRuleItem,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get alert rule",
)
def get_rule(rule_id: int) -> AlertRuleItem:
    """按 ID 查询单条告警规则详情。

    Args:
        rule_id: 规则主键，来自路径参数。

    Returns:
        AlertRuleItem: 规则详情。

    Raises:
        HTTPException: 规则不存在 404、查询异常 500。
    """
    service = build_alert_service()
    try:
        return AlertRuleItem(**service.get_rule(rule_id))
    except AlertNotFoundError as exc:
        raise _not_found(exc)
    except Exception as exc:
        raise _internal_error("Get alert rule failed", exc)


@router.patch(
    "/rules/{rule_id}",
    response_model=AlertRuleItem,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Update alert rule",
)
def update_rule(rule_id: int, request: AlertRuleUpdateRequest) -> AlertRuleItem:
    """按 ID 局部更新告警规则（仅提交显式设置的字段）并返回更新后详情。

    Args:
        rule_id: 规则主键，来自路径参数。
        request: 更新请求体，未设置的字段不参与更新。

    Returns:
        AlertRuleItem: 更新后的规则。

    Raises:
        HTTPException: 校验错误 400、不存在 404、服务异常 500。

    Side Effects:
        修改告警规则记录。
    """
    service = build_alert_service()
    try:
        payload = request.model_dump(exclude_unset=True)
        return AlertRuleItem(**service.update_rule(rule_id, payload))
    except AlertNotFoundError as exc:
        raise _not_found(exc)
    except UnsupportedAlertTypeError as exc:
        raise _bad_request(exc, error=exc.error_code)
    except AlertServiceError as exc:
        raise _bad_request(exc, error=exc.error_code)
    except Exception as exc:
        raise _internal_error("Update alert rule failed", exc)


@router.delete(
    "/rules/{rule_id}",
    response_model=AlertDeleteResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete alert rule",
)
def delete_rule(rule_id: int) -> AlertDeleteResponse:
    """按 ID 删除告警规则，返回删除结果。

    Args:
        rule_id: 规则主键，来自路径参数。

    Returns:
        AlertDeleteResponse: 实际删除条数。

    Raises:
        HTTPException: 不存在 404、服务异常 500。

    Side Effects:
        删除告警规则记录。
    """
    service = build_alert_service()
    try:
        if not service.delete_rule(rule_id):
            raise AlertNotFoundError(f"Alert rule not found: {rule_id}")
        return AlertDeleteResponse(deleted=1)
    except AlertNotFoundError as exc:
        raise _not_found(exc)
    except Exception as exc:
        raise _internal_error("Delete alert rule failed", exc)


@router.post(
    "/rules/{rule_id}/enable",
    response_model=AlertRuleItem,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Enable alert rule",
)
def enable_rule(rule_id: int) -> AlertRuleItem:
    """启用指定告警规则并返回更新后的规则详情。

    Args:
        rule_id: 规则主键，来自路径参数。

    Returns:
        AlertRuleItem: 启用后的规则。

    Raises:
        HTTPException: 不存在 404、服务异常 500。

    Side Effects:
        修改规则的 enabled 状态。
    """
    service = build_alert_service()
    try:
        return AlertRuleItem(**service.enable_rule(rule_id, True))
    except AlertNotFoundError as exc:
        raise _not_found(exc)
    except Exception as exc:
        raise _internal_error("Enable alert rule failed", exc)


@router.post(
    "/rules/{rule_id}/disable",
    response_model=AlertRuleItem,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Disable alert rule",
)
def disable_rule(rule_id: int) -> AlertRuleItem:
    """停用指定告警规则并返回更新后的规则详情。

    停用后规则不参与定时求值，但配置保留，可随时重新启用。

    Args:
        rule_id: 规则主键，来自路径参数。

    Returns:
        AlertRuleItem: 停用后的规则。

    Raises:
        HTTPException: 不存在 404、服务异常 500。

    Side Effects:
        修改规则的 enabled 状态。
    """
    service = build_alert_service()
    try:
        return AlertRuleItem(**service.enable_rule(rule_id, False))
    except AlertNotFoundError as exc:
        raise _not_found(exc)
    except Exception as exc:
        raise _internal_error("Disable alert rule failed", exc)


@router.post(
    "/rules/{rule_id}/test",
    response_model=AlertRuleTestResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Dry-run alert rule",
)
def test_rule(rule_id: int) -> AlertRuleTestResponse:
    """对指定规则执行一次测试触发，返回测试结果。

    试运行不产生真实通知，便于保存前验证阈值与数据可用性。

    Args:
        rule_id: 规则主键，来自路径参数。

    Returns:
        AlertRuleTestResponse: 触发结论、观测值与逐目标明细。

    Raises:
        HTTPException: 服务异常 500。
    """
    service = build_alert_service()
    try:
        return AlertRuleTestResponse(**service.test_rule(rule_id))
    except AlertNotFoundError as exc:
        raise _not_found(exc)
    except Exception as exc:
        raise _internal_error("Test alert rule failed", exc)


@router.get(
    "/triggers",
    response_model=AlertTriggerListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List alert trigger history",
)
def list_triggers(
    rule_id: Optional[int] = Query(None, description="Optional rule id filter"),
    target: Optional[str] = Query(None, description="Optional target filter"),
    status: Optional[str] = Query(None, description="Optional status filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AlertTriggerListResponse:
    """分页查询告警触发记录，支持规则 ID、目标与状态过滤。

    Args:
        rule_id: 规则 ID 过滤；None 表示不限。
        target: 触发目标过滤。
        status: 触发状态过滤。
        page: 页码，从 1 开始。
        page_size: 每页条数。

    Returns:
        AlertTriggerListResponse: 当前页触发记录与总数。

    Raises:
        HTTPException: 查询异常 500。
    """
    service = build_alert_service()
    try:
        return AlertTriggerListResponse(
            **service.list_triggers(
                rule_id=rule_id,
                target=target,
                status=status,
                page=page,
                page_size=page_size,
            )
        )
    except Exception as exc:
        raise _internal_error("List alert triggers failed", exc)


@router.get(
    "/notifications",
    response_model=AlertNotificationListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List alert notification attempts",
)
def list_notifications(
    trigger_id: Optional[int] = Query(None, description="Optional trigger id filter"),
    channel: Optional[str] = Query(None, description="Optional channel filter"),
    success: Optional[bool] = Query(None, description="Optional success filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AlertNotificationListResponse:
    """分页查询通知发送记录，支持触发 ID、通道与成功状态过滤。

    Args:
        trigger_id: 触发记录 ID 过滤；None 表示不限。
        channel: 通知渠道过滤。
        success: 投递成功状态过滤；None 表示不限。
        page: 页码，从 1 开始。
        page_size: 每页条数。

    Returns:
        AlertNotificationListResponse: 当前页投递记录与总数。

    Raises:
        HTTPException: 查询异常 500。
    """
    service = build_alert_service()
    try:
        return AlertNotificationListResponse(
            **service.list_notifications(
                trigger_id=trigger_id,
                channel=channel,
                success=success,
                page=page,
                page_size=page_size,
            )
        )
    except Exception as exc:
        raise _internal_error("List alert notifications failed", exc)
