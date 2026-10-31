# -*- coding: utf-8 -*-
"""Environment bootstrap shared by CLI, API and WebUI entry points.

``bootstrap_environment`` is idempotent and intentionally limited to loading
``.env`` plus the optional local proxy configuration. Database creation,
scheduler startup and network calls belong to the entry-point lifecycle, not to
module import.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_PUBLIC_BIND_HOSTS = frozenset({"0.0.0.0", "::", "[::]", "*"})
_bootstrapped = False


def bootstrap_environment() -> None:
    """Load ``.env`` and apply optional proxy settings exactly once per process."""
    global _bootstrapped
    if _bootstrapped:
        return

    from src.config import setup_env

    setup_env()
    _apply_proxy_settings()
    _bootstrapped = True


def _apply_proxy_settings() -> None:
    """Apply ``USE_PROXY`` settings, skipping CI and non-local environments."""
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
    """Return True when ``host`` binds to a non-loopback interface."""
    return (host or "").strip().lower() in _PUBLIC_BIND_HOSTS


def warn_if_public_webui_without_auth(host: str) -> None:
    """Warn when the Web UI is exposed publicly while admin auth is disabled."""
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
