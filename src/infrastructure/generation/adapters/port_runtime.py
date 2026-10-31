# -*- coding: utf-8 -*-
"""``GenerationRuntimePort`` 实现（转接 ``generation_params`` / ``errors`` / ``local_cli_backend``）。"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.application.generation.ports import GenerationCapabilities, GenerationError


class GenerationRuntimeAdapter:
    """生成调用运行时：参数归一、带恢复调用、预设解析、配置探测、能力表。

    ``local_cli_backend.LocalCliGenerationBackend`` 同时承载「构造 + 配置探测」
    （``get_config_error`` 内部解析可执行文件），因此 ``config_error`` 在同一次
    构造内完成，不额外引入探测原语。
    """

    def apply_params(
        self,
        call_kwargs: Dict[str, Any],
        model: str,
        temperature: Optional[float],
        *,
        default_temperature: float = 0.7,
        model_list: Optional[list] = None,
        request_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from src.infrastructure.generation import generation_params

        return generation_params.apply_litellm_generation_params(
            call_kwargs,
            model,
            temperature,
            default_temperature=default_temperature,
            model_list=model_list,
            request_overrides=request_overrides,
        )

    def completion_with_recovery(
        self,
        call: Callable[[Dict[str, Any]], Any],
        *,
        model: str,
        call_kwargs: Dict[str, Any],
        model_list: Optional[list] = None,
        cache_recovery: bool = True,
        logger: Any = None,
        log_label: str = "[LiteLLM]",
    ) -> Any:
        from src.infrastructure.generation import errors

        return errors.call_litellm_with_param_recovery(
            call,
            model=model,
            call_kwargs=call_kwargs,
            model_list=model_list,
            cache_recovery=cache_recovery,
            logger=logger,
            log_label=log_label,
        )

    def resolve_preset(self, backend_id: str) -> Any:
        from src.infrastructure.generation import local_cli_backend

        return local_cli_backend.resolve_local_cli_preset(backend_id)

    def config_error(self, config: Any, backend_id: str) -> Optional[GenerationError]:
        from src.infrastructure.generation import local_cli_backend

        preset = local_cli_backend.resolve_local_cli_preset(backend_id)
        backend = local_cli_backend.LocalCliGenerationBackend(
            config,
            preset_id=backend_id,
            preset=preset,
        )
        return backend.get_config_error()

    def capabilities(self) -> GenerationCapabilities:
        from src.infrastructure.generation import local_cli_backend

        return local_cli_backend.LocalCliGenerationBackend.capabilities

    def thinking_extra_body(self, model: str) -> Optional[Dict[str, Any]]:
        """转接 ``llm_adapter`` 的 thinking 载荷表（延迟 import 避免拉起 litellm）。"""
        from src.infrastructure.agent_runtime.llm_adapter import (
            get_thinking_extra_body as _impl,
        )

        return _impl(model)

    def resolve_fallback_wire_models(
        self,
        model: str,
        model_list: Optional[list] = None,
    ) -> list:
        """转接 ``llm_adapter`` 的别名→wire model 展开（延迟 import）。"""
        from src.infrastructure.agent_runtime.llm_adapter import (
            resolve_fallback_litellm_wire_models as _impl,
        )

        return _impl(model, model_list)
