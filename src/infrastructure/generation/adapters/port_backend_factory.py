# -*- coding: utf-8 -*-
"""``GenerationBackendFactoryPort`` 实现（转接 ``backend_factory``）。"""

from __future__ import annotations

from typing import Any, Callable, Optional

from src.application.generation.ports import GenerationBackend


class GenerationBackendFactoryAdapter:
    """按 backend_id 构造生成后端（薄转接，无策略）。"""

    def create(
        self,
        backend_id: str,
        *,
        config: Any,
        litellm_completion_callable: Optional[Callable[..., Any]] = None,
    ) -> GenerationBackend:
        from src.infrastructure.generation import backend_factory

        return backend_factory.create_generation_backend(
            backend_id,
            config=config,
            litellm_completion_callable=litellm_completion_callable,
        )
