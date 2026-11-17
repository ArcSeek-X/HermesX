# -*- coding: utf-8 -*-
"""生成链路基础设施（R2-A3 建包，R2-A4 完成物理归位）。

R2-A4 后本包同时持有两类东西：端口适配器（``adapters/``）与原 ``src/llm/`` 的实现
文件（``backend_factory`` / ``errors`` / ``generation_params`` / ``litellm_backend`` /
``local_cli_backend`` / ``provider_cache`` / ``usage`` / ``hermes``）。``src/llm/``
目录已删除，本包是生成实现的唯一落点。
"""

from __future__ import annotations

from src.infrastructure.generation.adapters import (
    GenerationBackendFactoryAdapter,
    GenerationRuntimeAdapter,
    GenerationUsageAdapter,
    ProviderCacheAdapter,
)

__all__ = [
    "GenerationBackendFactoryAdapter",
    "GenerationRuntimeAdapter",
    "GenerationUsageAdapter",
    "ProviderCacheAdapter",
]
