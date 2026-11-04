# -*- coding: utf-8 -*-
"""``GenerationUsagePort`` 实现（转接 ``usage``）。"""

from __future__ import annotations

from typing import Any, Dict, Optional


class GenerationUsageAdapter:
    """usage 归一、载荷提取、HMAC/审计挂载与写库判定（薄转接，无策略）。"""

    def normalize(
        self,
        usage_obj: Any,
        *,
        model: str = "",
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """规范化用量数据。"""
        from src.infrastructure.generation import usage as usage_module

        return usage_module.normalize_litellm_usage(usage_obj, model=model, provider=provider)

    def extract_payload(self, response: Any) -> Any:
        """从响应中提取用量载荷。"""
        from src.infrastructure.generation import usage as usage_module

        return usage_module.extract_usage_payload(response)

    def attach_hmacs(self, usage: Dict[str, Any], messages: Any) -> Dict[str, Any]:
        """为用量记录附加 HMAC 签名。"""
        from src.infrastructure.generation import usage as usage_module

        return usage_module.attach_message_hmacs(usage, messages)

    def attach_legacy_audit(
        self,
        usage: Dict[str, Any],
        messages: Any,
        audit_context: Any = None,
    ) -> Dict[str, Any]:
        """附加遗留审计字段。"""
        from src.infrastructure.generation import usage as usage_module

        return usage_module.attach_legacy_message_stability_audit(
            usage,
            messages,
            audit_context,
        )

    def should_persist(self, usage: Any) -> bool:
        """判断用量记录是否应持久化。"""
        from src.infrastructure.generation import usage as usage_module

        return usage_module.should_persist_usage_telemetry(usage)

    def persist(
        self,
        usage: Any,
        model: str,
        *,
        call_type: str,
        stock_code: Optional[str] = None,
    ) -> None:
        """写入一条 LLM 用量遥测（委托 ``src.storage``）。"""
        from src.storage import persist_llm_usage

        persist_llm_usage(usage, model, call_type=call_type, stock_code=stock_code)
