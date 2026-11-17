# -*- coding: utf-8 -*-
"""
@file: auth.py
@description: 管理鉴权中间件：启用 ADMIN_AUTH 时保护 /api/v1/* 路由，未启用时透传；
    由 api.app.create_app 通过 add_auth_middleware 注册，先于业务端点执行。
@author: Lensgcx (GaoCangxiong)

Auth middleware: protect /api/v1/* when admin auth is enabled.

The middleware is registered unconditionally; whether it enforces sessions is
decided per request via is_auth_enabled(), so a runtime configuration reload
takes effect without rebuilding the FastAPI application.

管理鉴权中间件：启用 ADMIN_AUTH 时保护 /api/v1/* 路由，对未放行的路径校验凭证，
未启用时直接透传请求。
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth import COOKIE_NAME, is_auth_enabled, verify_session

# 模块级日志器，用于记录鉴权相关的可观测事件，不参与请求中断决策。
logger = logging.getLogger(__name__)

# 无需会话即可访问的路径白名单。登录入口必须可匿名调用，否则无法取得会话；
# status 供前端判断登录态，health 供探活，docs/redoc/openapi.json 供文档访问。
# 使用 frozenset 保证运行期不可变，避免请求处理中意外放宽鉴权范围。
EXEMPT_PATHS = frozenset({
    "/api/v1/auth/login",   # 登录入口：获取会话 Cookie 的唯一途径
    "/api/v1/auth/status",  # 登录态查询：未登录时也要能拿到明确状态
    "/api/health",          # 兼容旧探活路径
    "/api/v1/health",       # v1 探活路径
    "/health",              # 根探活路径
    "/docs",                # Swagger UI 文档
    "/redoc",               # ReDoc 文档
    "/openapi.json",        # OpenAPI 描述文件
})


def _path_exempt(path: str) -> bool:
    """Check if path is exempt from auth.

    判断路径是否命中白名单；统一去掉尾部斜杠，避免 ``/docs`` 与 ``/docs/``
    出现不同的鉴权结果。

    Args:
        path: 请求 URL 的 path 部分，可带尾部斜杠；空串按根路径 ``/`` 处理。

    Returns:
        bool: 命中白名单返回 True，调用方应跳过会话校验。

    Side Effects:
        无；不修改入参，也不读取全局可变状态。
    """
    normalized = path.rstrip("/") or "/"
    return normalized in EXEMPT_PATHS


class AuthMiddleware(BaseHTTPMiddleware):
    """Require valid session for /api/v1/* when auth is enabled.

    使用场景：由 add_auth_middleware 挂到 FastAPI 应用，覆盖所有 /api/v1/* 请求；
    静态资源、根路由与白名单路径不在拦截范围内，非 API 路径同样直接放行。

    @author: Lensgcx (GaoCangxiong)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ):
        """拦截请求：鉴权未启用直接放行；对需保护的路径校验凭证，失败返回 401。

        判断按开销从低到高排列：先看总开关，再看白名单与非 API 路径，最后才校验
        会话 Cookie；未通过时直接返回 JSON 401，不再调用下游处理器。

        Args:
            request: 当前请求对象，只读其 ``url.path`` 与 ``cookies``。
            call_next: Starlette 提供的下游处理器，接收 request 并返回 Response。

        Returns:
            Response: 放行时为下游响应；会话缺失或无效时为 401 JSON 响应。

        Raises:
            不主动抛异常；下游处理器异常按 Starlette 中间件语义向上传播。

        Side Effects:
            无状态修改；仅读取会话 Cookie，并可能提前终止请求链。
        """
        if not is_auth_enabled():
            return await call_next(request)

        path = request.url.path
        if _path_exempt(path):
            return await call_next(request)

        if not path.startswith("/api/v1/"):
            return await call_next(request)

        # 仅校验 Cookie 中的签名会话，不解析请求体，避免影响非 JSON 接口。
        cookie_val = request.cookies.get(COOKIE_NAME)
        if not cookie_val or not verify_session(cookie_val):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Login required",
                },
            )

        return await call_next(request)


def add_auth_middleware(app):
    """Add auth middleware to protect API routes.

    The middleware is always registered; whether auth is enforced is determined
    at request time by is_auth_enabled() so the decision stays consistent across
    any runtime configuration reload.

    向应用注册鉴权中间件。无条件注册、把开关判断留到请求期，是为了让系统配置在
    运行期切换 ADMIN_AUTH 后立即生效，无需重建应用或重启进程。

    Args:
        app: FastAPI 应用实例，注册后中间件对其全部请求生效。

    Returns:
        None: 原地修改应用，不返回新实例。

    Side Effects:
        调用 ``app.add_middleware`` 修改中间件栈；注册顺序决定实际执行顺序。
    """
    app.add_middleware(AuthMiddleware)
