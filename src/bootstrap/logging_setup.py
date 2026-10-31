# -*- coding: utf-8 -*-
"""Logging setup shared by CLI, API and WebUI entry points."""

from __future__ import annotations

import logging
import sys
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


def setup_bootstrap_logging(debug: bool = False) -> None:
    """Initialize stderr-only logging before the config is loaded.

    File handlers are deferred until ``config.log_dir`` is known (via the
    subsequent ``setup_runtime_logging()`` call) so that healthy runs never
    create log files in a hard-coded directory.
    """
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    if not any(
        isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) is sys.stderr
        for handler in root.handlers
    ):
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        root.addHandler(handler)


def setup_runtime_logging(log_dir: str, debug: bool = False) -> bool:
    """Switch to configured logging, falling back to console on file I/O errors."""
    try:
        from src.infrastructure.observability.logging_config import setup_logging

        setup_logging(log_prefix="stock_analysis", debug=debug, log_dir=log_dir)
        return True
    except OSError as exc:
        logger.warning(
            "文件日志初始化失败，已降级为控制台日志输出；日志目录 %r 当前不可写或不可创建: %s。"
            "官方 Docker 镜像启动入口会自动修复默认挂载目录权限；若仍失败，"
            "请检查是否使用了 --user、只读挂载、rootless Docker 或 NFS 等限制写入的环境。",
            log_dir,
            exc,
        )
        return False


def setup_service_logging(
    log_prefix: str,
    *,
    use_config_level: bool = False,
    debug: bool = False,
    quiet_loggers: Iterable[str] = (),
    log_dir: Optional[str] = None,
) -> None:
    """Initialize logging for long-lived API/WebUI service processes."""
    console_level: Optional[int] = None
    if use_config_level:
        from src.config import get_config

        config = get_config()
        level_name = (config.log_level or "INFO").upper()
        console_level = getattr(logging, level_name, logging.INFO)

    kwargs = {
        "log_prefix": log_prefix,
        "console_level": console_level,
        "debug": debug,
        "extra_quiet_loggers": list(quiet_loggers),
    }
    if log_dir is not None:
        kwargs["log_dir"] = log_dir

    from src.infrastructure.observability.logging_config import setup_logging

    setup_logging(**kwargs)
