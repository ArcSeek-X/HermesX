# -*- coding: utf-8 -*-
"""Shared helpers for API error responses.

统一构造 API 错误响应体与异常，保证各端点返回结构一致（error / message / 可选 detail）。
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse


def error_body(error: str, message: str, *, detail: Any = None) -> dict[str, Any]:
    """构造统一错误响应体：含 error 与 message，detail 非空时附加。"""
    body: dict[str, Any] = {
        "error": error,
        "message": message,
    }
    if detail is not None:
        body["detail"] = detail
    return body


def api_error(status_code: int, error: str, message: str, *, detail: Any = None) -> HTTPException:
    """构造带统一错误体的 FastAPI HTTPException。"""
    return HTTPException(
        status_code=status_code,
        detail=error_body(error, message, detail=detail),
    )


def error_json_response(status_code: int, error: str, message: str, *, detail: Any = None) -> JSONResponse:
    """构造带统一错误体的 JSONResponse（用于中间件等非异常路径）。"""
    return JSONResponse(
        status_code=status_code,
        content=error_body(error, message, detail=detail),
    )
