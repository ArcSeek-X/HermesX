# -*- coding: utf-8 -*-
"""In-process Uvicorn serving helper used by ``main.py --serve``.

This module stays driver-agnostic: the caller passes the already-imported ASGI
application. It never imports ``api`` or ``bot``.
"""

from __future__ import annotations

import logging
import socket
import threading
import time

logger = logging.getLogger(__name__)


def serve_api_in_thread(app, host: str, port: int, config) -> None:
    """Run ``app`` with Uvicorn in a daemon thread and wait for startup.

    Args:
        app: Imported ASGI application instance.
        host: Listen address.
        port: Listen port.
        config: Config object used for the Uvicorn log level.

    Raises:
        RuntimeError: The port is unavailable or the server fails to start.
    """
    import uvicorn

    probe = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError as exc:
        raise RuntimeError(f"FastAPI port is not available: {host}:{port}") from exc
    finally:
        probe.close()

    level_name = (config.log_level or "INFO").lower()
    use_config_signal_handlers = True
    uvicorn_kwargs = {
        "host": host,
        "port": port,
        "log_level": level_name,
        "log_config": None,
    }
    # Keep the heavy app import outside the startup probe window; the caller
    # imports ``api.app`` before calling this helper for the same reason.
    try:
        uvicorn_config = uvicorn.Config(
            app,
            install_signal_handlers=False,
            **uvicorn_kwargs,
        )
    except TypeError:
        # Older uvicorn versions do not accept install_signal_handlers in
        # Config; fall back and only disable signal handling via Server
        # attribute when it is a boolean flag.
        use_config_signal_handlers = False
        uvicorn_config = uvicorn.Config(
            app,
            **uvicorn_kwargs,
        )
    uvicorn_server = uvicorn.Server(config=uvicorn_config)
    if not use_config_signal_handlers:
        install_signal_handlers = getattr(uvicorn_server, "install_signal_handlers", None)
        if isinstance(install_signal_handlers, bool):
            uvicorn_server.install_signal_handlers = False

    startup_error: list[BaseException] = []

    def run_server():
        try:
            uvicorn_server.run()
        except Exception as exc:  # noqa: BLE001 - surface startup issues to caller promptly
            startup_error.append(exc)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    timeout_seconds = 3.0
    wait_deadline = time.time() + timeout_seconds
    while time.time() < wait_deadline:
        if startup_error:
            raise RuntimeError(
                f"FastAPI server failed to start: {host}:{port}; {startup_error[0]}"
            )
        if uvicorn_server.started:
            logger.info(f"FastAPI 服务已启动: http://{host}:{port}")
            return
        if not thread.is_alive():
            break
        time.sleep(0.05)

    if startup_error:
        raise RuntimeError(f"FastAPI server failed to start: {host}:{port}; {startup_error[0]}")
    if uvicorn_server.started:
        logger.info(f"FastAPI 服务已启动: http://{host}:{port}")
        return
    if not thread.is_alive():
        raise RuntimeError(f"FastAPI 服务器启动后立即退出: {host}:{port}")

    raise RuntimeError(f"FastAPI 服务在 {timeout_seconds:.1f}s 内未完成启动: {host}:{port}")
