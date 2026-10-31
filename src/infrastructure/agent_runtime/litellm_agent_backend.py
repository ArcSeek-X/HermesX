# -*- coding: utf-8 -*-
"""LiteLLM-backed Agent Chat execution backend.

Infrastructure-side implementation of the backend-neutral
:class:`~src.application.agent.agent_backend.AgentBackend` contract. It wraps the
application-owned ``run_agent_loop`` with the infrastructure ``LLMToolAdapter``,
so the concrete adapter dependency lives here rather than pulling an
``application → infrastructure`` import back into the contract module.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.application.agent.agent_backend import (
    AgentBackend,
    AgentRunRequest,
    AgentRunResult,
)
from src.application.agent.runner import run_agent_loop
from src.application.agent.tools.registry import ToolRegistry
from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter


class LiteLLMAgentBackend(AgentBackend):
    """Thin wrapper around the existing HRS-owned ``run_agent_loop``."""

    backend_id = "litellm"
    runtime_owns_loop = False

    def __init__(self, tool_registry: ToolRegistry, llm_adapter: LLMToolAdapter) -> None:
        self.tool_registry = tool_registry
        self.llm_adapter = llm_adapter

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": request.system_prompt},
            *request.history_messages,
            {"role": "user", "content": request.user_message},
        ]
        loop_result = run_agent_loop(
            messages=messages,
            tool_registry=self.tool_registry,
            llm_adapter=self.llm_adapter,
            max_steps=request.max_steps,
            progress_callback=request.progress_callback,
            max_wall_clock_seconds=request.max_wall_clock_seconds,
            stock_scope=request.stock_scope,
        )
        usage = {"total_tokens": loop_result.total_tokens} if loop_result.total_tokens > 0 else None
        error_code = None
        if not loop_result.success and "timed out" in str(loop_result.error or "").lower():
            error_code = "timeout"
        elif not loop_result.success:
            error_code = "unknown_backend_error"
        return AgentRunResult(
            success=loop_result.success,
            final_answer=loop_result.content,
            tool_calls_log=loop_result.tool_calls_log,
            model=loop_result.model,
            backend=self.backend_id,
            usage=usage,
            diagnostics={"provider": loop_result.provider},
            error_code=error_code,
            error_message=loop_result.error,
            messages=loop_result.messages,
            total_steps=loop_result.total_steps,
        )
