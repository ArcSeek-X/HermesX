# -*- coding: utf-8 -*-
"""生成链路端口适配器包（R2-A4 由单文件 ``adapters.py`` 按端口拆分）。

适配器只做「契约 → 实现」转接，不承载业务逻辑；实现模块位于同级
``src/infrastructure/generation/``。方法体内以**模块对象**方式引用实现
（``from src.infrastructure.generation import usage as usage_module``），
保留测试对实现模块属性的 monkey-patch 语义（T5e-0b 拍板先例）。
"""

from __future__ import annotations

from src.infrastructure.generation.adapters.port_backend_factory import (
    GenerationBackendFactoryAdapter,
)
from src.infrastructure.generation.adapters.port_provider_cache import ProviderCacheAdapter
from src.infrastructure.generation.adapters.port_runtime import GenerationRuntimeAdapter
from src.infrastructure.generation.adapters.port_usage import GenerationUsageAdapter

__all__ = [
    "GenerationBackendFactoryAdapter",
    "GenerationRuntimeAdapter",
    "GenerationUsageAdapter",
    "ProviderCacheAdapter",
]
