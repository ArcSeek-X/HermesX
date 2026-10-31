# -*- coding: utf-8 -*-
"""Vision（多模态）LLM 调用适配器（W5.5）。

分层说明：本模块只负责把**已组装好的请求**发到 litellm 并取回首条候选文本——
不读配置、不做模型选择、不做重试与结果解析。这些留在用例层
``src.application.analysis.image_stock_extractor``（端口契约见
``src.application.analysis.vision_ports.VisionCompletionPort``）。
"""

from __future__ import annotations

import sys
from typing import Dict, Optional


class _LiteLLMPlaceholder:
    """litellm 未安装/未导入时的可 patch 占位对象。"""

    completion = None


# 与迁移前同语义：保留可 patch 的模块属性，同时避免模块级硬导入 litellm。
litellm = sys.modules.get("litellm") or _LiteLLMPlaceholder()


class LitellmVisionAdapter:
    """``VisionCompletionPort`` 的 litellm 实现（所有厂商共用 OpenAI vision 格式）。"""

    def complete(
        self,
        *,
        model: str,
        api_key: Optional[str],
        mime_type: str,
        image_b64: str,
        prompt: str,
        timeout: int,
        max_tokens: int = 1024,
        api_base: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> str:
        global litellm

        data_url = f"data:{mime_type};base64,{image_b64}"
        call_kwargs: dict = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "api_key": api_key,
            "timeout": timeout,
        }
        # api_base 与自定义 header 只对 OpenAI 兼容通道生效（由用例层判定后传入）。
        if api_base:
            call_kwargs["api_base"] = api_base
        if extra_headers:
            call_kwargs["extra_headers"] = extra_headers

        if getattr(litellm, "completion", None) is None:
            import litellm as litellm_module

            litellm = litellm_module
        response = litellm.completion(**call_kwargs)
        if response and response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        raise ValueError("LiteLLM vision returned empty response")
