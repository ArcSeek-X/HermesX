# -*- coding: utf-8 -*-
"""
@file: errors.py
@description: API v1 错误响应的统一构造入口：端点抛错、中间件直接返回响应都在此构造，
    保证 error / message / detail 三段结构与全局异常处理器输出一致。
@author: Lensgcx (GaoCangxiong)

Shared helpers for API error responses.

Helpers used by endpoint, middleware and exception-handler layers to build HTTP
error payloads with a stable shape: an ``error`` machine-readable code, a
``message`` for display, and an optional ``detail`` carrying validation or
diagnostic information.

统一构造 API 错误响应体与异常，保证各端点返回结构一致（error / message / 可选 detail）。
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse


def error_body(error: str, message: str, *, detail: Any = None) -> dict[str, Any]:
    """构造统一错误响应体：含 error 与 message，detail 非空时附加。

    所有错误出口共用此形状，前端才能按固定字段解析；detail 省略而非置空，
    避免把「无附加信息」与「附加信息为空」混为一谈。

    Args:
        error: 机器可识别的错误码（如 ``validation_error``），调用方保证非空。
        message: 面向用户的错误描述，调用方保证非空。
        detail: 可选的附加诊断信息（校验错误列表、上下文等）；``None`` 时不写入该键。

    Returns:
        dict[str, Any]: 至少含 ``error``、``message``；``detail`` 仅在非 ``None`` 时出现。

    Side Effects:
        无；每次返回新字典，不修改入参。
    """
    # detail 只在有诊断价值时出现，保持错误体最小化。
    body: dict[str, Any] = {
        "error": error,
        "message": message,
    }
    if detail is not None:
        body["detail"] = detail
    return body


def api_error(status_code: int, error: str, message: str, *, detail: Any = None) -> HTTPException:
    """构造携带统一错误体的 FastAPI HTTPException，供端点直接抛出。

    Args:
        status_code: HTTP 状态码，由调用方按业务语义选择（如 400/404/409）。
        error: 机器可识别的错误码，写入响应体 ``error`` 字段。
        message: 面向用户的错误描述，写入响应体 ``message`` 字段。
        detail: 可选附加诊断信息，透传给 ``error_body``。

    Returns:
        HTTPException: detail 为 dict 的异常对象，由全局异常处理器原样序列化。

    Side Effects:
        仅构造异常对象，不抛异常、不记录日志；抛出动作由调用方完成。
    """
    return HTTPException(
        status_code=status_code,
        detail=error_body(error, message, detail=detail),
    )


def error_json_response(status_code: int, error: str, message: str, *, detail: Any = None) -> JSONResponse:
    """构造携带统一错误体的 JSONResponse，用于不经过异常机制的出口。

    中间件等路径需要直接返回响应而非抛异常，此函数保证它们与端点错误同构。

    Args:
        status_code: HTTP 状态码，由调用方按业务语义选择。
        error: 机器可识别的错误码。
        message: 面向用户的错误描述。
        detail: 可选附加诊断信息，透传给 ``error_body``。

    Returns:
        JSONResponse: 已序列化统一错误体的响应对象。

    Side Effects:
        无；仅构造响应对象。
    """
    return JSONResponse(
        status_code=status_code,
        content=error_body(error, message, detail=detail),
    )
