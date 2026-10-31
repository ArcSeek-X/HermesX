# -*- coding: utf-8 -*-
"""AgentBackend contract, backend selection and the run request/result DTOs.

The LiteLLM-specific wrapper lives in
:mod:`src.infrastructure.agent_runtime.litellm_agent_backend` (it depends on the
infrastructure ``LLMToolAdapter``); this module keeps only the backend-neutral
contract so ``src/application`` stays free of infrastructure imports.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.application.agent.stock_scope import StockScope


AGENT_BACKEND_ERROR_CODES = frozenset(
    {
        "command_not_found",
        "login_required",
        "capability_unsupported",
        "unsupported_agent_arch",
        "approval_required",
        "timeout",
        "cancelled",
        "protocol_error",
        "output_too_large",
        "resource_limit_exceeded",
        "tool_roundtrip_failed",
        "resource_cleanup_failed",
        "invalid_timeout",
        "unknown_backend_error",
    }
)
AGENT_BACKEND_IDS = frozenset({"auto", "litellm", "codex_app_server"})


class AgentBackendConfigError(ValueError):
    """Structured Agent backend selection error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def resolve_agent_backend_id(config: Any) -> str:
    """Resolve Chat backend; ``auto`` deliberately remains LiteLLM."""
    requested = str(getattr(config, "agent_backend", "auto") or "auto").strip().lower()
    if requested not in AGENT_BACKEND_IDS:
        raise AgentBackendConfigError(
            "capability_unsupported",
            f"Unsupported AGENT_BACKEND: {requested}",
        )
    return "litellm" if requested == "auto" else requested


@dataclass(frozen=True)
class AgentRunRequest:
    system_prompt: str
    history_messages: List[Dict[str, Any]]
    user_message: str
    session_id: str
    stock_scope: Optional[StockScope]
    max_steps: int
    max_wall_clock_seconds: Optional[float]
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    cancel_event: Optional[threading.Event] = None


@dataclass
class AgentRunResult:
    success: bool = False
    final_answer: str = ""
    tool_calls_log: List[Dict[str, Any]] = field(default_factory=list)
    model: str = ""
    backend: str = ""
    usage: Optional[Dict[str, Any]] = None
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    total_steps: int = 0


class AgentBackend(ABC):
    """One execution backend for Agent Chat."""

    backend_id: str
    runtime_owns_loop: bool

    @abstractmethod
    def run(self, request: AgentRunRequest) -> AgentRunResult:
        """Run one Agent turn and return the normalized result."""
