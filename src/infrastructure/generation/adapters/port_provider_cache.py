# -*- coding: utf-8 -*-
"""``ProviderCachePort`` 实现（转接 ``provider_cache``）。

``usage`` 与 ``provider_cache`` 存在双向惰性 import，两者必须同包同层落位
（R2 §5.5 硬约束）；本适配器与 ``port_usage`` 同属适配器包即满足。
"""

from __future__ import annotations

from typing import Any, Dict


class ProviderCacheAdapter:
    """prompt cache 路由上下文与遥测投影（薄转接，无策略）。"""

    def apply_hints(self, call_kwargs: Dict[str, Any], route_context: Any, config: Any) -> Any:
        from src.infrastructure.generation import provider_cache

        return provider_cache.apply_prompt_cache_hints(call_kwargs, route_context, config)

    def build_route_context(
        self,
        *,
        model: str,
        provider: Any,
        call_kwargs: Dict[str, Any],
        model_list: Any,
        call_type: str,
    ) -> Any:
        from src.infrastructure.generation import provider_cache

        return provider_cache.build_provider_cache_route_context(
            model=model,
            provider=provider,
            call_kwargs=call_kwargs,
            model_list=model_list,
            call_type=call_type,
        )

    def filter_telemetry(self, usage: Dict[str, Any], config: Any) -> Dict[str, Any]:
        from src.infrastructure.generation import provider_cache

        return provider_cache.filter_prompt_cache_telemetry(usage, config)
