# -*- coding: utf-8 -*-
"""生成链路端口装配（R2-A3）。

四个端口对象在进程内无状态、可幂等多次装配，因此在同一处一次性注入三个消费
模块（``Analyzer`` / ``SystemConfigService`` / ``GenerationBackendStatusService``）。
调用方：``main.py`` 的 CLI 启动链与 ``src/bootstrap/api_lifecycle.py`` 的服务
生命周期链（两者均已存在同类 ``configure_*`` 列表，追加一项即可）。
"""

from __future__ import annotations

from src.application.analysis import analyzer as analyzer_module
from src.application.runtime import generation_backend_status as status_module
from src.application.runtime import system_config_service as system_config_module
from src.infrastructure.generation.adapters import (
    GenerationBackendFactoryAdapter,
    GenerationRuntimeAdapter,
    GenerationUsageAdapter,
    ProviderCacheAdapter,
)


def configure_generation_runtime() -> None:
    """装配生成链路四端口（幂等；重复调用只覆盖同类型对象）。"""

    factory_port = GenerationBackendFactoryAdapter()
    runtime_port = GenerationRuntimeAdapter()
    usage_port = GenerationUsageAdapter()
    provider_cache_port = ProviderCacheAdapter()

    analyzer_module.set_generation_backend_factory_port(factory_port)
    analyzer_module.set_generation_runtime_port(runtime_port)
    analyzer_module.set_generation_usage_port(usage_port)
    analyzer_module.set_provider_cache_port(provider_cache_port)

    system_config_module.set_generation_runtime_port(runtime_port)
    status_module.set_generation_runtime_port(runtime_port)
