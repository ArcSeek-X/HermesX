# -*- coding: utf-8 -*-
"""本地 CLI 生成后端的配置边界纯策略。

R2-A3 起本模块是 timeout / 输出上限 / 并发上下限默认值与有效并发放大规则的
**唯一真源**。原 ``src/llm/local_cli_backend.py`` 的同对象重导出随 R2-A4 搬包进入
``src/infrastructure/generation/local_cli_backend.py``（反向 import 保持同一对象）。

为什么在 domain 而不是 ``src/config``：这些值是**执行安全边界**（子进程最长运行
时间、单次输出上限、并发闸上下限），不是用户可配置项的默认值——用户配置项的
默认值仍由 ``src/config/settings.py`` 以本模块常量初始化。``config`` 与
``application`` 均以 ``→ domain`` 方向引用，无倒置。

零 IO、零第三方依赖，符合 ``src/domain/`` 分层约束（``config`` 参数按 ``Any``
收口，不 import ``src.config``）。
"""

from __future__ import annotations

from typing import Any


DEFAULT_LOCAL_CLI_TIMEOUT_SECONDS = 300
DEFAULT_LOCAL_CLI_MAX_OUTPUT_BYTES = 1024 * 1024
DEFAULT_GENERATION_BACKEND_MAX_CONCURRENCY = 1
DEFAULT_LOCAL_CLI_BACKEND_MAX_CONCURRENCY = 1
MAX_LOCAL_CLI_TIMEOUT_SECONDS = 3600
MAX_LOCAL_CLI_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_GENERATION_BACKEND_MAX_CONCURRENCY = 16
MAX_LOCAL_CLI_BACKEND_MAX_CONCURRENCY = 4


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def effective_local_cli_concurrency(config: Any) -> int:
    """Return the effective local CLI concurrency limit.

    ``GENERATION_BACKEND_MAX_CONCURRENCY`` 是全局闸，``LOCAL_CLI_BACKEND_MAX_CONCURRENCY``
    是本地 CLI 专属闸；两者先各自按上限钳制，再取较小值作为实际并发度，最低为 1。
    """

    backend_limit = _positive_int(
        getattr(config, "generation_backend_max_concurrency", None),
        DEFAULT_GENERATION_BACKEND_MAX_CONCURRENCY,
    )
    local_limit = _positive_int(
        getattr(config, "local_cli_backend_max_concurrency", None),
        DEFAULT_LOCAL_CLI_BACKEND_MAX_CONCURRENCY,
    )
    backend_limit = min(backend_limit, MAX_GENERATION_BACKEND_MAX_CONCURRENCY)
    local_limit = min(local_limit, MAX_LOCAL_CLI_BACKEND_MAX_CONCURRENCY)
    return max(1, min(local_limit, backend_limit))
