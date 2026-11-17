# -*- coding: utf-8 -*-
"""UsageTelemetryPort 适配器：委托 ``src.infrastructure.generation.usage``。

application 层的 ``runner.py`` / ``chat_context.py`` 只依赖
:class:`~src.application.agent.usage_telemetry_ports.UsageTelemetryPort`，本适配器在
infrastructure 侧委托既有纯判定函数 :func:`should_persist_usage_telemetry`，从而在不
把 provider 用量归一化机制下沉 domain 的前提下满足架构守卫。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from src.infrastructure.generation.usage import should_persist_usage_telemetry


class UsageTelemetryAdapter:
    """实现 :class:`~src.application.agent.usage_telemetry_ports.UsageTelemetryPort` 协议。"""

    def should_persist(self, usage: Optional[Mapping[str, Any]]) -> bool:
        """Return whether the usage dict should be persisted as provider telemetry."""
        return should_persist_usage_telemetry(usage)

    def persist(
        self,
        usage: Optional[Mapping[str, Any]],
        model: str,
        *,
        call_type: str = "agent",
    ) -> None:
        """将一条 LLM 用量遥测写入持久层（委托 ``src.storage``）。"""
        from src.storage import persist_llm_usage

        persist_llm_usage(dict(usage or {}), model, call_type=call_type)
