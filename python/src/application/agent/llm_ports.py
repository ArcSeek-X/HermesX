# -*- coding: utf-8 -*-
"""Agent 编排层的 LLM 调用端口。

端口覆盖 ``LLMToolAdapter`` 在 ``runner`` / ``research`` / ``base_agent`` /
``orchestrator`` / ``executor`` 中的实际调用面：工具/文本/统一补全三条路径，以及
可用性与主 provider 两个只读属性。返回 ``Any``（实为基础设施侧 ``LLMResponse``），
消费方按属性做鸭子类型访问，端口不暴露 ``litellm`` 的响应 dataclass。

实现方：:class:`~src.infrastructure.agent_runtime.llm_adapter.LLMToolAdapter`，
由 ``factory`` 构造后经构造函数/函数参数注入到用例（不在 application 内构造）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class AgentLLMPort(Protocol):
    """Agent 用例所需的 LLM 补全能力。"""

    def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[dict],
        provider: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """发送消息 + 工具声明，返回规范化响应（content 或 tool_calls）。"""

    def call_text(
        self,
        messages: List[Dict[str, Any]],
        *,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """经由共享路由栈发送纯文本补全。"""

    def call_completion(
        self,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[dict]] = None,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """工具与纯文本调用共用的补全路径。"""

    @property
    def is_available(self) -> bool:
        """litellm 已配置且至少存在一个 API key 时为 True。"""

    @property
    def primary_provider(self) -> str:
        """从主模型前缀解析出的 provider 名称。"""
