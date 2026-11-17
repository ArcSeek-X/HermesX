# -*- coding: utf-8 -*-
"""LiteLLM generation backend wrapper.

将 LiteLLM 补全调用封装为统一 GenerationBackend 实现，负责 provider 推断、
流式与响应校验回调的透传，以及生成结果与用量归一化。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from src.application.generation.ports import (
    GenerationBackend,
    GenerationCapabilities,
    GenerationResult,
)


LiteLLMCallable = Callable[..., Tuple[str, str, Dict[str, Any]]]


def _provider_from_model(model: str) -> str:
    """从模型名推断 provider：含 '/' 取前缀，否则视为 openai；空串返回空串。"""
    if not model:
        return ""
    if "/" in model:
        return model.split("/", 1)[0]
    return "openai"


class LiteLLMGenerationBackend(GenerationBackend):
    """Thin adapter around the existing LiteLLM analyzer call path."""

    backend_id = "litellm"
    capabilities = GenerationCapabilities(
        supports_json=True,
        supports_tools=True,
        supports_stream=True,
        supports_vision=False,
        supports_health_check=False,
        supports_smoke_test=False,
    )

    def __init__(self, completion_callable: LiteLLMCallable):
        """构造后端：注入实际执行补全的可调用对象。"""
        self._completion_callable = completion_callable

    def generate(
        self,
        prompt: str,
        generation_config: Dict[str, Any],
        *,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_progress_callback: Optional[Callable[[int], None]] = None,
        response_validator: Optional[Callable[[str], None]] = None,
        audit_context: Optional[Dict[str, Any]] = None,
    ) -> GenerationResult:
        """执行一次生成：透传统一配置与可选的系统提示、流式进度、响应校验及审计上下文，返回归一化结果。"""
        text, model, usage = self._completion_callable(
            prompt,
            generation_config,
            system_prompt=system_prompt,
            stream=stream,
            stream_progress_callback=stream_progress_callback,
            response_validator=response_validator,
            audit_context=audit_context,
        )
        provider = str((usage or {}).get("provider") or _provider_from_model(model))
        return GenerationResult(
            text=text,
            model=model,
            provider=provider,
            backend=self.backend_id,
            usage=usage or {},
            raw=None,
            diagnostics={},
        )
