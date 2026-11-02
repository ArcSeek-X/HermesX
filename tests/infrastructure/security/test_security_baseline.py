# -*- coding: utf-8 -*-
"""W7.1 认证 / Cookie / CORS 安全不变量守卫。

`ARCHITECTURE_TARGET.md` §9.2-5 要求「对公网/桌面两种运行场景的认证、Cookie、
CORS 与修改类请求防护……须在相关切片开始前记录」。本文件把当前**已实现且被认可**
的语义钉成不变量，防止后续重构悄悄放宽：

1. 会话 Cookie 三标志（HttpOnly / SameSite=Lax / Secure 按请求协议判定）；
2. 会话签名密钥 32 字节、文件 0600、长度异常自动重建；签名校验走常数时间比较；
3. 会话令牌三段式 + 过期即失效，篡改签名即失效；
4. 认证中间件只豁免白名单，`/api/v1/*` 其余路径一律要求有效会话；
5. CORS 不允许「`*` + 携带凭证」同时成立；客户端 IP 取 XFF 最右值，防止伪造左值绕过限流。

这些用例只锁定现状语义，不引入新的安全功能。
"""

from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import os
import time

import pytest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

import src.auth as auth_module
from api.app import create_app
from api.middlewares import auth as auth_middleware_module
from api.v1.endpoints.auth import _cookie_params


def _make_request(path: str = "/", scheme: str = "https", headers=None) -> Request:
    raw_headers = [
        (key.lower().encode(), value.encode()) for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": raw_headers,
            "scheme": scheme,
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 50000),
        }
    )


@pytest.fixture()
def isolated_auth_state(monkeypatch, tmp_path):
    """隔离 auth 模块的进程内缓存与数据目录，退出时恢复。"""
    secret_before = auth_module._session_secret
    enabled_before = auth_module._auth_enabled
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "stock_analysis.db"))
    monkeypatch.setattr(auth_module, "_session_secret", None)
    monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
    yield tmp_path
    auth_module._session_secret = secret_before
    auth_module._auth_enabled = enabled_before


# --------------------------------------------------------------------------
# Cookie 标志
# --------------------------------------------------------------------------


def test_cookie_flags_are_httponly_lax_and_secure_on_https(monkeypatch):
    monkeypatch.delenv("TRUST_X_FORWARDED_FOR", raising=False)
    monkeypatch.delenv("ADMIN_SESSION_MAX_AGE_HOURS", raising=False)

    params = _cookie_params(_make_request(scheme="https"))

    assert params["httponly"] is True
    assert params["samesite"] == "lax"
    assert params["secure"] is True
    assert params["path"] == "/"
    assert params["max_age"] == auth_module.SESSION_MAX_AGE_HOURS_DEFAULT * 3600


def test_cookie_secure_follows_request_scheme_on_plain_http(monkeypatch):
    monkeypatch.delenv("TRUST_X_FORWARDED_FOR", raising=False)

    params = _cookie_params(_make_request(scheme="http"))

    # 桌面端本地 HTTP 场景必须仍可登录，故 Secure 由协议决定而非写死 True。
    assert params["secure"] is False


def test_cookie_secure_uses_forwarded_proto_behind_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUST_X_FORWARDED_FOR", "true")

    behind_tls = _cookie_params(
        _make_request(scheme="http", headers={"X-Forwarded-Proto": "https"})
    )
    behind_plain = _cookie_params(
        _make_request(scheme="http", headers={"X-Forwarded-Proto": "http"})
    )

    assert behind_tls["secure"] is True
    assert behind_plain["secure"] is False


def test_cookie_max_age_falls_back_on_invalid_env(monkeypatch):
    monkeypatch.setenv("ADMIN_SESSION_MAX_AGE_HOURS", "not-a-number")

    params = _cookie_params(_make_request())

    assert params["max_age"] == auth_module.SESSION_MAX_AGE_HOURS_DEFAULT * 3600


# --------------------------------------------------------------------------
# 会话密钥与令牌
# --------------------------------------------------------------------------


def test_session_secret_is_32_bytes_with_owner_only_permissions(isolated_auth_state):
    secret = auth_module._load_session_secret()

    assert isinstance(secret, bytes) and len(secret) == 32
    secret_path = isolated_auth_state / ".session_secret"
    assert secret_path.exists()
    assert oct(secret_path.stat().st_mode)[-3:] == "600"


def test_session_secret_with_wrong_length_is_regenerated(isolated_auth_state):
    secret_path = isolated_auth_state / ".session_secret"
    isolated_auth_state.mkdir(parents=True, exist_ok=True)
    secret_path.write_bytes(b"too-short")
    auth_module._session_secret = None

    regenerated = auth_module._load_session_secret()

    assert regenerated is not None and len(regenerated) == 32
    assert secret_path.read_bytes() == regenerated
    assert secret_path.read_bytes() != b"too-short"


def test_session_token_roundtrip_and_tamper_rejection(isolated_auth_state):
    token = auth_module.create_session()
    assert token and len(token.split(".")) == 3

    assert auth_module.verify_session(token) is True

    nonce, ts, sig = token.split(".")
    assert auth_module.verify_session(f"{nonce}.{ts}.{'0' * len(sig)}") is False
    assert auth_module.verify_session(f"{nonce}.{ts}") is False
    assert auth_module.verify_session("") is False


def test_expired_session_token_is_rejected(isolated_auth_state, monkeypatch):
    monkeypatch.delenv("ADMIN_SESSION_MAX_AGE_HOURS", raising=False)
    secret = auth_module._load_session_secret()
    stale_ts = str(int(time.time()) - (auth_module.SESSION_MAX_AGE_HOURS_DEFAULT + 1) * 3600)
    payload = f"nonce.{stale_ts}"
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    assert auth_module.verify_session(f"{payload}.{sig}") is False


def test_signature_checks_use_constant_time_comparison():
    verify_source = inspect.getsource(auth_module.verify_session)
    hash_source = inspect.getsource(auth_module._verify_password_hash)

    assert "hmac.compare_digest" in verify_source
    assert "hmac.compare_digest" in hash_source


# --------------------------------------------------------------------------
# 认证中间件
# --------------------------------------------------------------------------


def test_auth_middleware_exempts_only_whitelisted_paths():
    exempt = auth_middleware_module._path_exempt

    assert exempt("/api/v1/auth/login") is True
    assert exempt("/api/v1/auth/status") is True
    assert exempt("/api/v1/health") is True
    assert exempt("/api/health") is True

    assert exempt("/api/v1/analysis") is False
    assert exempt("/api/v1/auth/login/extra") is False
    assert exempt("/api/v1/auth/settings") is False


async def _dispatch(path: str, cookie_value: str | None = None):
    middleware = auth_middleware_module.AuthMiddleware(app=lambda scope, receive, send: None)

    async def call_next(request):
        return JSONResponse({"ok": True})

    request = _make_request(path=path)
    if cookie_value is not None:
        request.scope["headers"] = [
            (b"cookie", f"{auth_module.COOKIE_NAME}={cookie_value}".encode())
        ]
    return await middleware.dispatch(request, call_next)


def test_middleware_blocks_api_calls_without_valid_session(monkeypatch):
    import asyncio

    monkeypatch.setattr(auth_middleware_module, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth_middleware_module, "verify_session", lambda v: v == "good")

    blocked = asyncio.run(_dispatch("/api/v1/analysis"))
    forged = asyncio.run(_dispatch("/api/v1/analysis", cookie_value="bad"))
    allowed = asyncio.run(_dispatch("/api/v1/analysis", cookie_value="good"))
    exempt = asyncio.run(_dispatch("/api/v1/auth/login"))

    assert blocked.status_code == 401
    assert json.loads(blocked.body)["error"] == "unauthorized"
    assert forged.status_code == 401
    assert allowed.status_code == 200
    assert exempt.status_code == 200


def test_middleware_passes_through_when_auth_disabled(monkeypatch):
    import asyncio

    monkeypatch.setattr(auth_middleware_module, "is_auth_enabled", lambda: False)

    response = asyncio.run(_dispatch("/api/v1/analysis"))

    assert response.status_code == 200


# --------------------------------------------------------------------------
# CORS 与客户端 IP
# --------------------------------------------------------------------------


def _cors_kwargs(monkeypatch, allow_all: bool) -> dict:
    if allow_all:
        monkeypatch.setenv("CORS_ALLOW_ALL", "true")
    else:
        monkeypatch.delenv("CORS_ALLOW_ALL", raising=False)
    app = create_app()
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return middleware.kwargs
    raise AssertionError("未找到 CORSMiddleware")


def test_cors_never_combines_wildcard_origin_with_credentials(monkeypatch):
    permissive = _cors_kwargs(monkeypatch, allow_all=True)
    restricted = _cors_kwargs(monkeypatch, allow_all=False)

    assert permissive["allow_origins"] == ["*"]
    assert permissive["allow_credentials"] is False

    assert "*" not in restricted["allow_origins"]
    assert restricted["allow_credentials"] is True


def test_client_ip_uses_rightmost_forwarded_value(monkeypatch):
    monkeypatch.setenv("TRUST_X_FORWARDED_FOR", "true")
    request = _make_request(headers={"X-Forwarded-For": "1.1.1.1, 2.2.2.2"})

    # 最左值可被客户端伪造，取最右值才能保证限流桶不被绕过。
    assert auth_module.get_client_ip(request) == "2.2.2.2"


def test_client_ip_ignores_forwarded_header_when_not_trusted(monkeypatch):
    monkeypatch.delenv("TRUST_X_FORWARDED_FOR", raising=False)
    request = _make_request(headers={"X-Forwarded-For": "1.1.1.1"})

    assert auth_module.get_client_ip(request) == "127.0.0.1"
    assert os.environ.get("TRUST_X_FORWARDED_FOR") is None
