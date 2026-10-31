# -*- coding: utf-8 -*-
"""图片识别（Vision）LLM 调用的端口契约（W5.5）。

``image_stock_extractor`` 历史上在应用层直接 ``import litellm`` 并发起多模态请求：
模型解析、Key 选择、请求装载、HTTP 调用、重试退避与结果解析全部落在同一模块里，
导致「识别用例」与「第三方 Vision 调用」无法分别测试与替换。

本端口只收敛**最后一步**：把已组装好的多模态请求发给模型并取回原始文本。模型选择、
Key 轮询、Prompt、重试退避与结果解析仍留在应用层用例中——它们属于识别业务的可观察
行为（配置优先级、重试语义、审计日志），而不是厂商适配细节。

实现见 ``src.infrastructure.generation.vision_litellm.LitellmVisionAdapter``；未显式
装配时由用例层惰性创建默认适配器（``set_vision_completion_port`` 可替换）。
"""

from __future__ import annotations

from typing import Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class VisionCompletionPort(Protocol):
    """多模态补全能力：单次请求，返回模型原始文本。"""

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
        """把多模态请求发给 ``model`` 并返回首条候选文本。

        Raises:
            ValueError: 模型返回空响应时。
        """


# —— Vision 端口的 bootstrap seam（W5.5）——
#
# application 不得 import ``src.infrastructure``；默认实现改由下面这对 hook 取得：
# 具体实现（``LitellmVisionAdapter``）由入口（``main.py`` / ``api_lifecycle`` /
# 测试 conftest）经 ``src.bootstrap.analysis.configure_vision_completion_port()`` 注册。
# 与取数/持久化端口一致，未注册时直接抛错，把漏装配暴露在启动期而不是静默失败。
_vision_completion_port: Optional[VisionCompletionPort] = None


def set_vision_completion_port(port: Optional[VisionCompletionPort]) -> None:
    """注册 Vision 调用端口（入口装配用，幂等；传 None 可重置）。"""
    global _vision_completion_port
    _vision_completion_port = port


def get_vision_completion_port() -> VisionCompletionPort:
    """取默认 Vision 端口；未装配时抛错（不静默降级为空结果）。"""
    if _vision_completion_port is None:
        raise RuntimeError(
            "VisionCompletionPort 未装配：请在启动链路调用 "
            "src.bootstrap.analysis.configure_vision_completion_port()（CLI 见 "
            "main.py，API 见 src.bootstrap.api_lifecycle，测试见 tests/conftest.py）"
        )
    return _vision_completion_port
