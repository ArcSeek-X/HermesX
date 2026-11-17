# -*- coding: utf-8 -*-
"""Agent 会话用例的装配。

仓储实现在此绑定为 ``ConversationRepository``；``api`` 只通过依赖注入拿到装配好的
:class:`~src.application.agent.service.AgentConversationService`，不接触 ``src.storage``
或 ORM 模型。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from src.application.agent import AgentConversationService
from src.infrastructure.persistence.repositories.conversation_repo import (
    ConversationRepository,
)
from src.storage import DatabaseManager

if TYPE_CHECKING:
    from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter

logger = logging.getLogger(__name__)


def build_agent_llm_adapter(config=None) -> LLMToolAdapter:
    """装配 Agent LLM 工具适配器（基础设施侧 ``LLMToolAdapter``）。

    ``api`` / ``bot`` 驱动需要构造 Agent 编排时经此工厂获取适配器，而不直连
    ``src.infrastructure``（驱动层禁入基础设施）。返回的实例结构化满足
    :class:`~src.application.agent.llm_ports.AgentLLMPort`。

    具体类在函数体内延迟导入，使调用方仍可在
    ``src.infrastructure.agent_runtime.llm_adapter.LLMToolAdapter`` 处 patch 到本工厂构造行为。
    """
    from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter

    return LLMToolAdapter(config)


def build_agent_conversation_service() -> AgentConversationService:
    """按当前进程的数据库单例装配 Agent 会话用例。

    每次调用返回新实例而不缓存：``DatabaseManager.reset_instance()`` 之后新建的用例
    会绑定到新的管理器，不会残留已释放的引擎引用。
    """
    return AgentConversationService(
        repository=ConversationRepository(DatabaseManager.get_instance()),
    )


_market_data_configured = False


def configure_market_data() -> None:
    """装配 MarketDataPort（幂等）：将适配器注入 data_tools / market_tools 的模块级 seam。"""
    global _market_data_configured
    if _market_data_configured:
        return
    from src.application.agent.tools.data_tools import set_market_data_port as set_dt_port
    from src.application.agent.tools.market_tools import set_market_data_port as set_mt_port
    from src.infrastructure.agent_runtime.market_data_provider import DataFetcherManagerAdapter

    adapter = DataFetcherManagerAdapter.get_instance()
    set_dt_port(adapter)
    set_mt_port(adapter)
    _market_data_configured = True


_usage_telemetry_configured = False


def configure_usage_telemetry() -> None:
    """装配 UsageTelemetryPort（幂等）：将适配器注入 runner / chat_context 的模块级 seam。"""
    global _usage_telemetry_configured
    if _usage_telemetry_configured:
        return
    from src.application.agent.chat_context import set_usage_telemetry_port as set_cc_port
    from src.application.agent.runner import set_usage_telemetry_port as set_runner_port
    from src.infrastructure.agent_runtime.usage_telemetry_provider import UsageTelemetryAdapter

    adapter = UsageTelemetryAdapter()
    set_runner_port(adapter)
    set_cc_port(adapter)
    _usage_telemetry_configured = True


def configure_agent_memory() -> None:
    """装配 AgentMemory 历史读取用例的历史仓储默认端口（幂等）。

    进程启动时调用一次（CLI 入口 / API lifespan）；``set_history_repo`` 幂等，重复调用只会
    重新指向同一个适配器。以 ``DatabaseManager`` 门面作
    :class:`~src.application.history.ports.HistoryRepositoryPort` 适配器，与迁移前用例内
    部 ``get_db()`` 取全局单例的语义逐字等价（``get_stock_history`` 只读 get_analysis_history）。
    """
    from src.application.agent.memory import set_history_repo

    set_history_repo(DatabaseManager.get_instance())


def configure_provider_trace() -> None:
    """装配 provider_trace 默认 db_factory seam（幂等）。

    进程启动时调用一次（CLI 入口 / API lifespan）。以 ``DatabaseManager.get_instance`` 作默认
    工厂，与迁移前 ``persist_provider_trace_turns`` 内 ``db_factory is None`` 回退到
    ``from src.storage import get_db`` 的语义逐字等价（``get_db()`` 即返回
    ``DatabaseManager.get_instance()`` 单例），供未显式传入 ``db_factory`` 的调用方
    （如 ``chat_executor`` / ``executor``）复用；显式传入 ``db_factory`` 的调用方会覆盖默认工厂、不受影响。
    """
    from src.application.agent.provider_trace import set_default_db_factory

    set_default_db_factory(DatabaseManager.get_instance)


def configure_tools_db() -> None:
    """装配 agent tools（search_tools / data_tools）的 _get_db 工厂 seam（幂等）。

    两件 tools 模块级 ``_get_db()`` 原以 ``from src.storage import get_db`` 懒加载取库；
    W4.2 依赖倒置收敛改由本函数装配 ``DatabaseManager.get_instance`` 作默认工厂（与
    ``get_db()`` 逐字等价、返回同一单例），由 ``main`` 进程级块与 ``api_lifespan`` 双入口
    调用。tools 写路径包在 try/except 内可 fail-open，读路径依赖装配齐全（生产两入口均装配）。
    """
    from src.application.agent.tools import data_tools, search_tools

    data_tools.set_db_factory(DatabaseManager.get_instance)
    search_tools.set_db_factory(DatabaseManager.get_instance)


def configure_agent_conversation() -> None:
    """装配 agent 会话层的对话消息端口与上下文端口（幂等）。

    进程启动时调用一次（CLI 入口 / API lifespan）。以同一个
    :class:`ConversationRepository` 包装 ``DatabaseManager`` 单例，同时满足
    :class:`~src.application.agent.ports.ConversationMessagePort` 与
    :class:`~src.application.agent.ports.ChatContextPort`，与迁移前用例内部
    ``get_db()`` 取全局单例的语义逐字等价（方法签名与默认值均一致）。
    """
    from src.application.agent.chat_context import set_chat_context_port
    from src.application.agent.conversation import set_conversation_port

    repository = ConversationRepository(DatabaseManager.get_instance())
    set_conversation_port(repository)
    set_chat_context_port(repository)


# ---------------------------------------------------------------------------
# Agent executor builders
#
# These construct infrastructure adapters (LLMToolAdapter / LiteLLMAgentBackend /
# CodexAgentBackend / ToolSurface), so they live in bootstrap rather than in
# ``src.application.agent.factory`` (which must stay free of infrastructure
# imports). Skill/tool resolution and the orchestrator build helper are reused
# from ``application.factory`` via lazy in-function imports so callers can still
# ``patch`` those seams on the application module. api/bot drive these builders
# instead of importing ``src.infrastructure`` directly.
# ---------------------------------------------------------------------------
def build_agent_executor(config=None, skills: Optional[List[str]] = None):
    """Build and return a configured AgentExecutor (or future orchestrator).

    When ``AGENT_ARCH=multi``, this returns an orchestrator that manages
    multiple specialised agents. Otherwise it returns the legacy single-agent
    executor.
    """
    from src.config import AGENT_MAX_STEPS_DEFAULT, get_config
    from src.application.agent.factory import (
        _build_orchestrator,
        _coerce_config_int,
        get_tool_registry,
        resolve_skill_prompt_state,
    )

    if config is None:
        config = get_config()

    arch = getattr(config, "agent_arch", "single")

    from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter

    registry = get_tool_registry()
    prompt_state = resolve_skill_prompt_state(config, skills=skills)
    skill_manager = prompt_state.skill_manager
    logger.info(
        "[AgentFactory] Resolved skill prompt state: skills=%s (arch=%s, explicit=%s, legacy_default_prompt=%s)",
        prompt_state.skills_to_activate,
        arch,
        prompt_state.explicit_skill_selection,
        prompt_state.use_legacy_default_prompt,
    )

    llm_adapter = LLMToolAdapter(config)

    if arch == "multi":
        return _build_orchestrator(
            config,
            registry,
            llm_adapter,
            skill_manager,
            technical_skill_policy=prompt_state.technical_skill_policy,
        )

    from src.application.agent.executor import AgentExecutor
    # Intentionally do not mutate config routing fields here. We only coerce
    # execution params (max_steps/timeout_seconds) from config values; provider,
    # model, base URL and channel routes stay unchanged and are consumed by
    # downstream adapter logic as-is.
    return AgentExecutor(
        tool_registry=registry,
        llm_adapter=llm_adapter,
        skill_instructions=prompt_state.skill_instructions,
        default_skill_policy=prompt_state.default_skill_policy,
        use_legacy_default_prompt=prompt_state.use_legacy_default_prompt,
        max_steps=_coerce_config_int(
            getattr(config, "agent_max_steps", AGENT_MAX_STEPS_DEFAULT),
            AGENT_MAX_STEPS_DEFAULT,
            field_name="agent_max_steps",
        ),
        timeout_seconds=_coerce_config_int(
            getattr(config, "agent_orchestrator_timeout_s", 0),
            0,
            field_name="agent_orchestrator_timeout_s",
        ),
    )


def build_agent_chat_executor(config=None, skills: Optional[List[str]] = None):
    """Build the backend-neutral executor used only by Agent Chat endpoints."""
    from src.config import AGENT_MAX_STEPS_DEFAULT, get_config
    from src.application.agent.factory import (
        _coerce_config_int,
        get_tool_registry,
        resolve_skill_prompt_state,
    )

    if config is None:
        config = get_config()

    from src.application.agent.agent_backend import (
        AgentBackendConfigError,
        resolve_agent_backend_id,
    )
    from src.infrastructure.agent_runtime.litellm_agent_backend import LiteLLMAgentBackend
    from src.application.agent.chat_executor import AgentChatExecutor

    backend_id = resolve_agent_backend_id(config)
    arch = str(getattr(config, "agent_arch", "single") or "single").strip().lower()
    if backend_id == "codex_app_server" and arch != "single":
        raise AgentBackendConfigError(
            "unsupported_agent_arch",
            "Codex Agent currently supports single-agent Chat only",
        )
    if backend_id == "litellm" and arch == "multi":
        return build_agent_executor(config, skills=skills)

    registry = get_tool_registry()
    prompt_state = resolve_skill_prompt_state(config, skills=skills)
    if backend_id == "litellm":
        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter

        context_llm_adapter = LLMToolAdapter(config)
        backend = LiteLLMAgentBackend(registry, context_llm_adapter)
    else:
        from src.infrastructure.agent_runtime.codex_agent_backend import CodexAgentBackend
        from src.infrastructure.agent_runtime.tool_surface import ToolSurface

        context_llm_adapter = None
        backend = CodexAgentBackend(ToolSurface(registry), config)

    return AgentChatExecutor(
        backend=backend,
        config=config,
        context_llm_adapter=context_llm_adapter,
        skill_instructions=prompt_state.skill_instructions,
        default_skill_policy=prompt_state.default_skill_policy,
        use_legacy_default_prompt=prompt_state.use_legacy_default_prompt,
        max_steps=_coerce_config_int(
            getattr(config, "agent_max_steps", AGENT_MAX_STEPS_DEFAULT),
            AGENT_MAX_STEPS_DEFAULT,
            field_name="agent_max_steps",
        ),
        timeout_seconds=_coerce_config_int(
            getattr(config, "agent_orchestrator_timeout_s", 0),
            0,
            field_name="agent_orchestrator_timeout_s",
        ),
    )


# Keep legacy alias so any external callers using the old name still work.
build_executor = build_agent_executor
