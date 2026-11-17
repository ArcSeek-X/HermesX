# -*- coding: utf-8 -*-
"""
@file: auth.py
@description: Web 管理端认证端点：登录、登出、密码修改、认证开关与登录态查询；由 api.v1.router 挂到 /api/v1/auth，鉴权中间件对 login/status 放行，凭证与会话规则在 src.auth。
@author: Lensgcx (GaoCangxiong)

Authentication endpoints for Web admin login.

Handles session-cookie issuance, password management and the
auth-enablement toggle, with runtime configuration reload.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from api.deps import get_system_config_service
from src.auth import (
    COOKIE_NAME,
    SESSION_MAX_AGE_HOURS_DEFAULT,
    change_password,
    check_rate_limit,
    clear_rate_limit,
    create_session,
    get_client_ip,
    has_stored_password,
    is_auth_enabled,
    is_password_changeable,
    is_password_set,
    record_login_failure,
    refresh_auth_state,
    rotate_session_secret,
    set_initial_password,
    verify_password,
    verify_stored_password,
    verify_session,
)
from src.config import Config, setup_env
from src.config.env_file import ConfigManager

# 模块级日志器，记录认证配置变更失败与登录异常。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/auth。
router = APIRouter()


class LoginRequest(BaseModel):
    """Login request body.

    使用场景：登录端点接收管理员密码；模型配置拒绝额外字段，避免误传覆盖认证逻辑。

    @author: Lensgcx (GaoCangxiong)
    """

    # 拒绝未声明字段，避免登录请求携带可影响认证逻辑的多余参数。
    model_config = {"populate_by_name": True}

    # 管理员明文密码；仅在传输中出现，不落日志。
    password: str = Field(default="", description="Admin password")


class ChangePasswordRequest(BaseModel):
    """Change password request body.

    使用场景：已登录状态下修改密码；要求同时提供当前密码与两次新密码。

    @author: Lensgcx (GaoCangxiong)
    """

    # 拒绝未声明字段，保证密码修改入参严格。
    model_config = {"populate_by_name": True}

    # 当前密码，用于确认操作者身份。
    current_password: str = Field(default="", alias="currentPassword")
    # 新密码明文。
    new_password: str = Field(default="", alias="newPassword")
    # 新密码确认值，须与 new_password 一致。
    new_password_confirm: str = Field(default="", alias="newPasswordConfirm")


class AuthSettingsRequest(BaseModel):
    """Update auth enablement and initial password settings.

    使用场景：设置页开启/关闭认证，或在首次使用时设定初始密码。

    @author: Lensgcx (GaoCangxiong)
    """

    # 拒绝未声明字段，保证认证设置入参严格。
    model_config = {"populate_by_name": True}

    # 目标认证开关状态。
    auth_enabled: bool = Field(alias="authEnabled")
    # 首次启用认证时设定的初始密码。
    password: str = Field(default="")
    # 初始密码确认值。
    password_confirm: str | None = Field(default=None, alias="passwordConfirm")
    # 已有认证配置时的当前密码，用于防竞态绕过校验。
    current_password: str = Field(default="", alias="currentPassword")


def _cookie_params(request: Request) -> dict:
    """Build cookie params including Secure based on request.

    构造会话 Cookie 参数；Secure 由请求 scheme 与代理头共同决定，避免 HTTPS 部署下 Cookie 明文传输。

    Args:
        request: 当前请求对象，用于判断协议与代理链。

    Returns:
        dict: 可直接传给 Response.set_cookie 的参数字典。
    """
    secure = False
    if os.getenv("TRUST_X_FORWARDED_FOR", "false").lower() == "true":
        proto = request.headers.get("X-Forwarded-Proto", "").lower()
        secure = proto == "https"
    else:
        # Check URL scheme when not behind proxy
        # 未部署在反向代理之后时，按请求自身的 scheme 决定是否给 Cookie 加 Secure；HTTPS 下必须开启，否则会话 Cookie 可能明文传输。
        secure = request.url.scheme == "https"

    try:
        max_age_hours = int(os.getenv("ADMIN_SESSION_MAX_AGE_HOURS", str(SESSION_MAX_AGE_HOURS_DEFAULT)))
    except ValueError:
        max_age_hours = SESSION_MAX_AGE_HOURS_DEFAULT
    max_age = max_age_hours * 3600

    return {
        "httponly": True,
        "samesite": "lax",
        "secure": secure,
        "path": "/",
        "max_age": max_age,
    }


def _apply_auth_enabled(enabled: bool, request: Request | None = None) -> bool:
    """Persist auth toggle to .env and reload runtime config.

    把认证开关写入 .env 并重载运行时配置，使开关无需重启进程立即生效。

    Args:
        enabled: 目标开关状态。
        request: 当前请求对象，用于记录来源与会话校验。

    Returns:
        bool: 是否成功持久化并重载。

    Side Effects:
        修改 .env 文件与进程内运行时配置。
    """
    manager_applied = False
    if request is not None:
        try:
            service = get_system_config_service(request)
            service.apply_simple_updates(
                updates=[("ADMIN_AUTH_ENABLED", "true" if enabled else "false")],
                mask_token="******",
            )
            manager_applied = True
        except Exception as exc:
            logger.warning(
                "Failed to apply auth toggle via shared SystemConfigService, falling back: %s",
                exc,
                exc_info=True,
            )
            manager_applied = False

    if not manager_applied:
        try:
            manager = ConfigManager()
            manager.apply_updates(
                updates=[("ADMIN_AUTH_ENABLED", "true" if enabled else "false")],
                sensitive_keys=set(),
                mask_token="******",
            )
            manager_applied = True
        except Exception as exc:
            logger.error("Failed to apply auth toggle via ConfigManager: %s", exc, exc_info=True)
            manager_applied = False

    if not manager_applied:
        return False

    Config.reset_instance()
    setup_env(override=True)
    refresh_auth_state()
    return True


def _password_set_for_response(auth_enabled: bool) -> bool:
    """Avoid exposing stored-password state when auth is disabled.

    认证关闭时不向未认证请求暴露「是否已存密码」，避免泄露设置状态。

    Args:
        auth_enabled: 当前认证开关状态。

    Returns:
        bool: 仅认证开启时返回真实的密码已设置状态。
    """
    return is_password_set() if auth_enabled else False


def _set_session_cookie(response: Response, session_value: str, request: Request) -> None:
    """Attach the admin session cookie to a response.

    Args:
        response: 待写入 Cookie 的响应对象。
        session_value: 已签名的会话值。
        request: 当前请求对象，用于推导 Cookie 参数。

    Returns:
        None。

    Side Effects:
        原地修改 response 的 Set-Cookie 头。
    """
    params = _cookie_params(request)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_value,
        httponly=params["httponly"],
        samesite=params["samesite"],
        secure=params["secure"],
        path=params["path"],
        max_age=params["max_age"],
    )


def _get_auth_status_dict(request: Request | None = None) -> dict:
    """Helper to build consistent auth status response body.

    登录态查询与登录/设置响应共用此构造，避免各端点字段口径不一致。

    Args:
        request: 当前请求对象，用于校验会话 Cookie。

    Returns:
        dict: authEnabled / loggedIn / passwordSet / passwordChangeable / setupState 等状态字段。
    """
    auth_enabled = is_auth_enabled()
    logged_in = False
    if auth_enabled and request:
        cookie_val = request.cookies.get(COOKIE_NAME)
        logged_in = verify_session(cookie_val) if cookie_val else False

    # setupState determination:
    # - enabled: auth is active
    # - password_retained: auth disabled but password exists
    # - no_password: auth disabled and no password exists
    # 前端据此决定展示登录页、密码保留提示，还是首次使用的初始化设置向导。
    if auth_enabled:
        setup_state = "enabled"
    elif has_stored_password():
        setup_state = "password_retained"
    else:
        setup_state = "no_password"

    return {
        "authEnabled": auth_enabled,
        "loggedIn": logged_in,
        "passwordSet": _password_set_for_response(auth_enabled),
        "passwordChangeable": is_password_changeable() if auth_enabled else False,
        "setupState": setup_state,
    }


@router.get(
    "/status",
    summary="Get auth status",
    description="Returns whether auth is enabled and if the current request is logged in.",
)
async def auth_status(request: Request):
    """Return authEnabled, loggedIn, passwordSet, passwordChangeable, setupState without requiring auth.

    无需登录即可调用，供前端决定展示登录页还是设置页。

    Args:
        request: 当前请求对象。

    Returns:
        认证状态字典；不携带任何密码或会话内容。
    """
    return _get_auth_status_dict(request)


@router.post(
    "/settings",
    summary="Update auth settings",
    description=(
        "Enable or disable password login. When enabling without an existing password, "
        "password + passwordConfirm are required. When re-enabling with a stored password, "
        "currentPassword is required."
    ),
)
async def auth_update_settings(request: Request, body: AuthSettingsRequest):
    """Manage auth enablement from the settings page.

    开启或关闭认证、设置初始密码；开启路径强制校验当前密码与有效会话以规避竞态绕过。

    Args:
        request: 当前请求对象。
        body: 认证设置请求体。

    Returns:
        更新后的认证状态。

    Raises:
        HTTPException: 密码校验失败 400/401、请求过于频繁 429。

    Side Effects:
        可能写入 .env、重载运行时配置并设置会话 Cookie。
    """
    target_enabled = body.auth_enabled
    current_enabled = is_auth_enabled()
    stored_password_exists = has_stored_password()

    password = (body.password or "").strip()
    confirm = (body.password_confirm or "").strip()
    current_password = (body.current_password or "").strip()

    if target_enabled:
        if password or confirm:
            if stored_password_exists:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "password_already_set",
                        "message": "已存在管理员密码，请启用认证后通过修改密码功能更新",
                    },
                )
            if not password:
                return JSONResponse(
                    status_code=400,
                    content={"error": "password_required", "message": "请输入要设置的管理员密码"},
                )
            if password != confirm:
                return JSONResponse(
                    status_code=400,
                    content={"error": "password_mismatch", "message": "两次输入的密码不一致"},
                )
            if has_stored_password():
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "password_already_set",
                        "message": "已存在管理员密码，请启用认证后通过修改密码功能更新",
                    },
                )
            err = set_initial_password(password)
            if err:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_password", "message": err},
                )
        elif not stored_password_exists:
            return JSONResponse(
                status_code=400,
                content={"error": "password_required", "message": "开启密码登录前请先设置密码"},
            )
        else:
            # P1 Vulnerability Fix: Enforce current-password check independent of global cached flag
            # We must verify they actually possess a valid admin session, otherwise an attacker
            # could hit a race condition when auth becomes enabled mid-flight.
            # This triggers whenever trying to enable/keep enabled an existing auth setup.
            # 安全修复：开启或保持认证时必须校验当前密码与有效会话，不能依赖全局缓存开关；否则攻击者可能利用「认证中途被打开」的竞态窗口绕过校验。
            cookie_val = request.cookies.get(COOKIE_NAME)
            # if target_enabled is True here, they are requesting to enable or keep auth enabled
            # target_enabled 为 True 表示该请求正在开启或保持认证开启状态。
            is_valid_session = cookie_val and verify_session(cookie_val)

            if not is_valid_session:
                if not current_password:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "current_required", "message": "重新开启认证前请输入当前密码"},
                    )
                ip = get_client_ip(request)
                if not check_rate_limit(ip):
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limited",
                            "message": "Too many failed attempts. Please try again later.",
                        },
                    )
                if not verify_stored_password(current_password):
                    record_login_failure(ip)
                    return JSONResponse(
                        status_code=401,
                        content={"error": "invalid_password", "message": "当前密码错误"},
                    )
                clear_rate_limit(ip)
    else:
        if current_enabled:
            cookie_val = request.cookies.get(COOKIE_NAME)
            is_valid_session = cookie_val and verify_session(cookie_val)

            if not is_valid_session:
                if not current_password:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "current_required", "message": "关闭认证前请输入当前密码"},
                    )
                ip = get_client_ip(request)
                if not check_rate_limit(ip):
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limited",
                            "message": "Too many failed attempts. Please try again later.",
                        },
                    )
                if not verify_stored_password(current_password):
                    record_login_failure(ip)
                    return JSONResponse(
                        status_code=401,
                        content={"error": "invalid_password", "message": "当前密码错误"},
                    )
                clear_rate_limit(ip)

    if target_enabled != current_enabled:
        if not _apply_auth_enabled(target_enabled, request=request):
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "message": "Failed to update auth settings"},
            )
        if not rotate_session_secret():
            rollback_ok = _apply_auth_enabled(current_enabled, request=request)
            if not rollback_ok:
                logger.error("Failed to roll back auth state after session secret rotation failure")
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "message": "Failed to rotate session secret"},
            )
    else:
        if not _apply_auth_enabled(target_enabled, request=request):
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "message": "Failed to update auth settings"},
            )

    if target_enabled:
        session_val = create_session()
        if not session_val:
            rollback_ok = _apply_auth_enabled(current_enabled, request=request)
            if not rollback_ok:
                logger.error("Failed to roll back auth state after session creation failure")
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "message": "Failed to create session"},
            )
        # We manually set loggedIn=True because the cookie is being set in this response
        # and won't be visible in request.cookies until the NEXT request.
        # 本次响应才写入 Cookie，request.cookies 要等下一次请求才能读到，因此登录响应里显式把 loggedIn 置为 True，避免前端首帧仍显示未登录。
        content = _get_auth_status_dict(request)
        content["loggedIn"] = True
        resp = JSONResponse(content=content)
        _set_session_cookie(resp, session_val, request)
        return resp

    resp = JSONResponse(content=_get_auth_status_dict(request))
    resp.delete_cookie(key=COOKIE_NAME, path="/")
    return resp



@router.post(
    "/login",
    summary="Login",
    description="Verify password and set session cookie.",
)
async def auth_login(request: Request, body: LoginRequest):
    """Verify password and set session cookie on success. Returns 401 or 429 on failure.

    失败次数受限以抵御暴力破解；成功时把会话 Cookie 写入响应并显式回传 loggedIn=True。

    Args:
        request: 当前请求对象。
        body: 登录请求体，含明文密码。

    Returns:
        登录成功状态与会话信息。

    Raises:
        HTTPException: 密码错误 401、尝试过多 429。

    Side Effects:
        写入会话 Cookie，并可能更新失败计数。
    """
    if not is_auth_enabled():
        return JSONResponse(
            status_code=400,
            content={"error": "auth_disabled", "message": "Authentication is not configured"},
        )

    password = (body.password or "").strip()
    if not password:
        return JSONResponse(
            status_code=400,
            content={"error": "password_required", "message": "请输入密码"},
        )

    ip = get_client_ip(request)
    if not check_rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limited",
                "message": "Too many failed attempts. Please try again later.",
            },
        )

    if not verify_password(password):
        record_login_failure(ip)
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_password", "message": "密码错误"},
        )

    clear_rate_limit(ip)
    session_val = create_session()
    if not session_val:
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Failed to create session"},
        )

    resp = JSONResponse(content={"ok": True})
    _set_session_cookie(resp, session_val, request)
    return resp


@router.post(
    "/change-password",
    summary="Change password",
    description="Change password. Requires valid session.",
)
async def auth_change_password(body: ChangePasswordRequest):
    """Change password. Requires login.

    Args:
        body: 修改密码请求体，含当前密码与两次新密码。

    Returns:
        修改结果状态。

    Raises:
        HTTPException: 当前密码错误或新密码不合规时返回 4xx。

    Side Effects:
        持久化新密码哈希，并可能使既有会话失效。
    """
    if not is_password_changeable():
        return JSONResponse(
            status_code=400,
            content={"error": "not_changeable", "message": "Password cannot be changed via web"},
        )

    current = (body.current_password or "").strip()
    new_pwd = (body.new_password or "").strip()
    new_confirm = (body.new_password_confirm or "").strip()

    if not current:
        return JSONResponse(
            status_code=400,
            content={"error": "current_required", "message": "请输入当前密码"},
        )
    if new_pwd != new_confirm:
        return JSONResponse(
            status_code=400,
            content={"error": "password_mismatch", "message": "两次输入的新密码不一致"},
        )

    err = change_password(current, new_pwd)
    if err:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_password", "message": err},
        )
    return Response(status_code=204)


@router.post(
    "/logout",
    summary="Logout",
    description="Clear session cookie.",
)
async def auth_logout(request: Request):
    """Clear session cookie.

    Args:
        request: 当前请求对象，用于推导 Cookie 的删除参数。

    Returns:
        退出登录结果。

    Side Effects:
        在响应中清除管理员会话 Cookie。
    """
    if is_auth_enabled() and not rotate_session_secret():
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Failed to invalidate session"},
        )
    resp = Response(status_code=204)
    resp.delete_cookie(key=COOKIE_NAME, path="/")
    return resp
