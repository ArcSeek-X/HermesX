# -*- coding: utf-8 -*-
"""AnalyzerLLMPort 适配器：收纳 GeminiAnalyzer 的 litellm SDK 外部调用原语。

对应端口契约 ``src/application/analysis/analyzer_runtime_ports.py``（T5f
``system_config_runtime.py`` 同型）。本模块是 analyzer §4.3 拆分后全仓唯一
直接构造 ``Router`` / 直调 ``litellm.completion`` / 使用 Hermes 无代理客户端
的运行时位置（``src/infrastructure/generation/`` 与 ``src/agent/llm_adapter`` 的既有
自有链路不受影响）。

monkey-patch 兼容语义（T5e-0b 拍板）：``litellm.Router`` / ``litellm.completion``
按调用时刻解析共享模块属性；``open_hermes_no_proxy_client`` /
``register_fallback_model_pricing`` 按调用时刻从源模块惰性解析——既有测试对
``litellm.completion`` 属性面的 patch（patch 的是共享 litellm 模块对象）经此
链路继续生效；对旧 ``src.application.analysis.analyzer`` 命名空间名的 patch 串在 A2 片按矩阵 re-point。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import litellm

logger = logging.getLogger(__name__)


class AnalyzerLLMAdapter:
    """``AnalyzerLLMPort`` 的 litellm SDK 实现（无状态，可幂等多次装配）。"""

    def build_router(self, *, model_list: List[Dict[str, Any]]) -> Optional[Any]:
        """构造 litellm Router；签名不兼容（TypeError）时返回 None（原兜底分支）。"""
        if not model_list:
            return None
        try:
            return litellm.Router(
                model_list=model_list,
                routing_strategy="simple-shuffle",
                num_retries=2,
            )
        except TypeError:
            logger.debug("Analyzer LLM: Router constructor signature not compatible; fallback to direct mode")
            return None

    def completion_direct(self, **kwargs: Any) -> Any:
        """裸 ``litellm.completion`` 直调（调用时刻解析属性，保持 patch 语义）。"""
        return litellm.completion(**kwargs)

    def completion_no_proxy(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float,
        call_kwargs: Dict[str, Any],
    ) -> Any:
        """Hermes 无代理客户端成对调用（contextmanager 开/还原与补全不可拆）。"""
        from src.infrastructure.generation.hermes import open_hermes_no_proxy_client

        hermes_kwargs = dict(call_kwargs)
        with open_hermes_no_proxy_client(api_key=api_key, base_url=base_url, timeout=timeout) as client:
            hermes_kwargs["client"] = client
            return litellm.completion(**hermes_kwargs)

    def register_fallback_pricing(self, models: List[str]) -> None:
        """fallback wire 模型零价注册（源模块函数，调用时刻惰性解析）。"""
        from src.infrastructure.agent_runtime.llm_adapter import register_fallback_model_pricing

        register_fallback_model_pricing(models)
