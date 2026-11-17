# -*- coding: utf-8 -*-
"""Environment bootstrap shared by CLI, API and WebUI entry points.

``bootstrap_environment`` is idempotent and intentionally limited to loading
``.env`` plus the optional local proxy configuration. Database creation,
scheduler startup and network calls belong to the entry-point lifecycle, not to
module import.

CLI / API / WebUI 共用的环境引导。``bootstrap_environment`` 幂等，仅加载 ``.env``
与可选本地代理配置；建库、启动调度、网络请求属于入口生命周期，不在模块导入时发生。
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_PUBLIC_BIND_HOSTS = frozenset({"0.0.0.0", "::", "[::]", "*"})
_bootstrapped = False


def bootstrap_environment() -> None:
    """Load ``.env`` and apply optional proxy settings exactly once per process.

    每个进程仅执行一次，加载 ``.env`` 并应用可选代理设置；重复调用直接返回。
    """
    global _bootstrapped
    if _bootstrapped:
        return

    from src.config import setup_env

    setup_env()
    _apply_proxy_settings()
    _bootstrapped = True


def _apply_proxy_settings() -> None:
    """Apply ``USE_PROXY`` settings, skipping CI and non-local environments.

    当 ``USE_PROXY=true``（且非 GitHub Actions CI）时，把 ``PROXY_HOST``/``PROXY_PORT``
    写入 ``http_proxy``/``https_proxy`` 环境变量；否则跳过。
    """
    if os.getenv("GITHUB_ACTIONS") == "true":
        return
    if os.getenv("USE_PROXY", "false").lower() != "true":
        return

    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url


def is_public_bind_host(host: str) -> bool:
    """Return True when ``host`` binds to a non-loopback interface.

    判断 host 是否绑定到非回环网卡（``0.0.0.0`` / ``::`` / ``*`` 等）。
    """
    return (host or "").strip().lower() in _PUBLIC_BIND_HOSTS


def warn_if_public_webui_without_auth(host: str) -> None:
    """Warn when the Web UI is exposed publicly while admin auth is disabled.

    当 WebUI 绑定到公网网卡且 ``ADMIN_AUTH_ENABLED=false`` 时打印安全告警。
    """
    if not is_public_bind_host(host):
        return

    from src.auth import is_auth_enabled

    if is_auth_enabled():
        return
    logger.warning(
        "WEBUI_HOST=%s binds the Web UI to a public interface while "
        "ADMIN_AUTH_ENABLED=false. Keep this service behind a trusted network "
        "boundary or enable admin authentication before exposing it.",
        host,
    )
