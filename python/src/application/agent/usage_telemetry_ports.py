# -*- coding: utf-8 -*-
"""Agent 编排层的用量遥测判定端口。

``runner.py`` 与 ``chat_context.py`` 在写入 LLM 用量前，需要判断某条 usage 是否
值得作为 provider telemetry 持久化。该判定依赖 ``src.infrastructure.generation.usage``
中深度耦合的 provider 用量归一化机制（key 集合、JSON 解析、数值校验），属于外层
序列化关注点，不宜下沉 domain，也不允许 application 直接 import infrastructure。

因此以端口 seam（H3b/S2c/S2e/A2 同型）暴露一个纯布尔判定：application 只依赖本协议，
具体实现由 infrastructure 适配器委托既有 usage 模块。

实现方：:class:`~src.infrastructure.agent_runtime.usage_telemetry_provider.UsageTelemetryAdapter`
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol


class UsageTelemetryPort(Protocol):
    """用量遥测持久化判定与写入能力。"""

    def should_persist(self, usage: Optional[Mapping[str, Any]]) -> bool:
        """Return whether the given usage dict should be persisted as provider telemetry.

        ``usage`` 为空或不含真实 provider 信号时返回 ``False``。
        """

    def persist(
        self,
        usage: Optional[Mapping[str, Any]],
        model: str,
        *,
        call_type: str = "agent",
    ) -> None:
        """将一条 LLM 用量遥测写入持久层。"""
