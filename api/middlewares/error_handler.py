# -*- coding: utf-8 -*-
"""
@file: error_handler.py
@description: 全局异常处理：捕获未处理异常、统一错误响应格式并记录日志；由
    api.app.create_app 调用 add_error_handlers 装配，中间件类也可单独挂载。
@author: Lensgcx (GaoCangxiong)

===================================
全局异常处理中间件
===================================

职责：
1. 捕获未处理的异常
2. 统一错误响应格式
3. 记录错误日志
"""

import logging
import traceback
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# 模块级日志器；DEBUG 级别开关同时决定是否把异常详情下发给客户端。
logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常处理中间件。

    捕获所有未被下游处理器或异常处理器接管的异常，转换为统一的 500 JSON 响应，
    避免把堆栈和内部信息直接暴露给客户端；与 add_error_handlers 的兜底处理器互补。

    使用场景：由 api.app 按需 ``add_middleware(ErrorHandlerMiddleware)`` 挂载；
    未挂载时，FastAPI 的 ``@app.exception_handler(Exception)`` 仍提供同样形状的兜底。

    @author: Lensgcx (GaoCangxiong)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """处理请求并捕获下游未处理异常。

        Args:
            request: 当前请求对象，异常日志中记录其路径与方法。
            call_next: Starlette 提供的下游处理器，返回 Response。

        Returns:
            Response: 正常时为下游响应；异常时为 500 JSON 响应。

        Raises:
            不主动抛出；仅捕获 ``Exception``，不拦截 ``BaseException`` 系列
            （如取消信号），以免破坏 ASGI 生命周期。

        Side Effects:
            异常时写一条 ERROR 级日志（含堆栈）；不修改请求状态。
        """
        try:
            response = await call_next(request)
            return response

        except Exception as e:
            # 记录错误日志：堆栈只进日志，响应体仅在 DEBUG 模式下带异常文本。
            logger.error(
                f"未处理的异常: {e}\n"
                f"请求路径: {request.url.path}\n"
                f"请求方法: {request.method}\n"
                f"堆栈: {traceback.format_exc()}"
            )

            # 返回统一格式的错误响应；detail 对生产环境隐藏内部异常信息。
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": "服务器内部错误，请稍后重试",
                    # 仅在 DEBUG 开启时下发异常文本，便于本地定位。
                    "detail": str(e) if logger.isEnabledFor(logging.DEBUG) else None
                }
            )


def add_error_handlers(app) -> None:
    """为 FastAPI 应用注册各类异常的全局处理器。

    三类处理器分别对应端点主动抛出的 HTTPException、请求体/参数校验失败、
    以及所有未预期异常；三者输出都与 api.v1.errors.error_body 约定同构。

    Args:
        app: FastAPI 应用实例，处理器注册在其 exception_handlers 上。

    Returns:
        None: 原地修改应用。

    Side Effects:
        修改 ``app.exception_handlers``；后注册的处理器覆盖同类型已有处理器。
    """
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """把 HTTPException 归一为统一错误体。

        Args:
            request: 当前请求对象，此处不读取，仅满足处理器签名。
            exc: 端点抛出的 HTTP 异常，其 detail 可能是字符串或已组装的错误体 dict。

        Returns:
            JSONResponse: 保留原状态码；detail 已是统一格式时原样透出，
            否则包装为 ``error="http_error"`` 并放入 message。

        Side Effects:
            无。
        """
        # 如果 detail 已经是 ErrorResponse 格式的 dict，直接使用。
        # 端点通过 api_error() 抛错时走这条分支，避免二次包装导致字段错位。
        if isinstance(exc.detail, dict) and "error" in exc.detail and "message" in exc.detail:
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail
            )
        # 否则将 detail 包装成 ErrorResponse 格式。
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": str(exc.detail) if exc.detail else "HTTP Error",
                "detail": None
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """把请求校验失败转换为 422 统一错误体。

        Args:
            request: 当前请求对象，此处不读取，仅满足处理器签名。
            exc: Pydantic/FastAPI 产生的校验异常，errors() 给出逐字段原因。

        Returns:
            JSONResponse: 固定 422，``detail`` 为原始校验错误列表。

        Side Effects:
            无。
        """
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "请求参数验证失败",
                "detail": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """兜底处理所有未预期异常，返回不含内部细节的 500 响应。

        Args:
            request: 当前请求对象，异常日志中记录其路径。
            exc: 未被其他处理器接管的异常。

        Returns:
            JSONResponse: 固定 500，``detail`` 恒为 ``None``。

        Side Effects:
            写一条含堆栈的 ERROR 级日志。
        """
        logger.error(
            f"未处理的异常: {exc}\n"
            f"请求路径: {request.url.path}\n"
            f"堆栈: {traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "服务器内部错误",
                "detail": None
            }
        )
