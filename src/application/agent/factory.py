# -*- coding: utf-8 -*-
"""
Skill/tool resolution helpers shared by Agent entrypoints.

This application-layer module owns the side-effect-light pieces of Agent
assembly: the cached ``ToolRegistry`` / ``SkillManager`` prototypes and skill
prompt resolution. The concrete executor builders that instantiate infrastructure
adapters (``LLMToolAdapter`` / ``LiteLLMAgentBackend`` / ``CodexAgentBackend``)
live in :mod:`src.bootstrap.agent`, since constructing those adapters is a
bootstrap (wiring) concern and must not appear in ``src.application``.

Performance notes
-----------------
* ``ToolRegistry`` is built once and cached at module level — tool
  registrations are immutable after setup so the object is safe to share
  across every request.
* ``SkillManager`` is expensive to create (loads YAML files from disk).
  A prototype is built on first use and cheap ``deepcopy`` clones are
  returned for each request, preserving thread-safety (``activate()``
  mutates internal state).

Usage::

    from src.application.agent.factory import resolve_skill_prompt_state

    state = resolve_skill_prompt_state(config, skills=["bull_trend", "shrink_pullback"])
"""

import copy
import logging
from dataclasses import dataclass
from typing import List, Optional

from src.config import AGENT_MAX_STEPS_DEFAULT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level caches
# ---------------------------------------------------------------------------
_TOOL_REGISTRY = None
_SKILL_MANAGER_PROTOTYPE = None
# Sentinel used as initial value so None (i.e. no custom dir) compares as "changed"
# on the very first call, forcing a build rather than accidentally skipping it.
_SENTINEL = object()
# Track which custom_dir the prototype was built with so we can invalidate
# the cache if AGENT_SKILL_DIR changes at runtime (e.g. via config reload).
_SKILL_MANAGER_CUSTOM_DIR: object = _SENTINEL


@dataclass
class SkillPromptState:
    """Resolved skill activation + prompt fragments for analysis entrypoints."""

    skill_manager: object
    skills_to_activate: List[str]
    explicit_skill_selection: bool
    use_legacy_default_prompt: bool
    skill_instructions: str
    default_skill_policy: str
    technical_skill_policy: str


def _coerce_config_int(raw_value: object, default: int, *, field_name: str | None = None) -> int:
    """Coerce optional numeric config values to int with a fallback default.

    This protects test doubles and incomplete config objects from propagating
    mock-like values (e.g., MagicMock attributes) into strict numeric paths.

    This function is side-effect free: it only returns a parsed int fallback value
    and intentionally never mutates source config attributes.
    """

    try:
        return int(raw_value)
    except (TypeError, ValueError, OverflowError):
        if field_name:
            logger.warning(
                "[AgentFactory] Invalid value for %s: %r, fallback to default %s",
                field_name,
                raw_value,
                default,
            )
        return default


def _normalize_skill_ids(
    skill_ids: Optional[List[str]],
    *,
    available_skill_ids: set[str],
) -> tuple[List[str], List[str]]:
    """Return validated skill ids plus unknown ids, preserving input order."""
    normalized: List[str] = []
    unknown: List[str] = []

    for skill_id in skill_ids or []:
        if not isinstance(skill_id, str):
            continue
        cleaned = skill_id.strip()
        if not cleaned:
            continue
        if cleaned == "all":
            if "all" not in normalized:
                normalized.append("all")
            continue
        if cleaned in available_skill_ids:
            if cleaned not in normalized:
                normalized.append(cleaned)
            continue
        if cleaned not in unknown:
            unknown.append(cleaned)

    return normalized, unknown


def _resolve_selected_skill_ids(
    *,
    requested_skills: Optional[List[str]],
    configured_skills: Optional[List[str]],
    default_skills: List[str],
    available_skill_ids: set[str],
) -> tuple[List[str], bool]:
    """Resolve active skill ids and whether they came from a valid explicit selection."""
    selection_source = None
    raw_skill_ids = None
    if requested_skills is not None:
        selection_source = "request"
        raw_skill_ids = requested_skills
    elif configured_skills is not None:
        selection_source = "config"
        raw_skill_ids = configured_skills
    else:
        return list(default_skills), False

    selected_skill_ids, unknown_skill_ids = _normalize_skill_ids(
        raw_skill_ids,
        available_skill_ids=available_skill_ids,
    )
    if unknown_skill_ids:
        logger.warning(
            "[AgentFactory] Ignoring unknown %s skill ids: %s",
            selection_source,
            unknown_skill_ids,
        )
    if selected_skill_ids:
        return selected_skill_ids, True

    if raw_skill_ids:
        logger.warning(
            "[AgentFactory] No valid %s skills remain after validation; falling back to default skills: %s",
            selection_source,
            default_skills,
        )
    return list(default_skills), False


def _should_use_legacy_default_prompt(
    *,
    skills_to_activate: List[str],
    explicit_skill_selection: bool,
    skill_catalog: List[object],
) -> bool:
    """Keep the legacy prompt only for the implicit built-in bull_trend fallback."""
    if explicit_skill_selection or skills_to_activate != ["bull_trend"]:
        return False

    bull_trend_skill = next(
        (
            skill
            for skill in skill_catalog
            if str(getattr(skill, "name", "")).strip() == "bull_trend"
        ),
        None,
    )
    return getattr(bull_trend_skill, "source", None) == "builtin"


def get_tool_registry():
    """Return a cached ToolRegistry (built once, shared across requests)."""
    global _TOOL_REGISTRY
    if _TOOL_REGISTRY is not None:
        return _TOOL_REGISTRY

    from src.application.agent.tools.registry import ToolRegistry
    from src.application.agent.tools.data_tools import ALL_DATA_TOOLS
    from src.application.agent.tools.analysis_tools import ALL_ANALYSIS_TOOLS
    from src.application.agent.tools.search_tools import ALL_SEARCH_TOOLS
    from src.application.agent.tools.market_tools import ALL_MARKET_TOOLS
    from src.application.agent.tools.backtest_tools import ALL_BACKTEST_TOOLS

    registry = ToolRegistry()
    for tool_fn in ALL_DATA_TOOLS + ALL_ANALYSIS_TOOLS + ALL_SEARCH_TOOLS + ALL_MARKET_TOOLS + ALL_BACKTEST_TOOLS:
        registry.register(tool_fn)

    _TOOL_REGISTRY = registry
    logger.info("[AgentFactory] ToolRegistry cached (%d tools)", len(registry))
    return _TOOL_REGISTRY


def get_skill_manager(config=None):
    """Return a deepcopy-clone of the cached SkillManager prototype.

    The prototype is initialised from disk on first call; subsequent calls
    return ``copy.deepcopy(prototype)`` which is ~10× faster than re-reading
    YAML files.  Each clone is independent so ``.activate()`` calls do not
    bleed between requests.

    Cache invalidation: if ``config.agent_skill_dir`` changes at runtime
    (e.g. via the web settings reload), the prototype is rebuilt automatically.
    """
    global _SKILL_MANAGER_PROTOTYPE, _SKILL_MANAGER_CUSTOM_DIR

    if config is None:
        from src.config import get_config
        config = get_config()

    current_custom_dir = getattr(config, "agent_skill_dir", None)
    if _SKILL_MANAGER_PROTOTYPE is not None and current_custom_dir == _SKILL_MANAGER_CUSTOM_DIR:
        return copy.deepcopy(_SKILL_MANAGER_PROTOTYPE)

    from src.application.agent.skills.base import SkillManager

    if _SKILL_MANAGER_PROTOTYPE is not None:
        logger.info("[AgentFactory] SkillManager prototype invalidated (agent_skill_dir changed: %r -> %r)",
                    _SKILL_MANAGER_CUSTOM_DIR, current_custom_dir)

    skill_manager = SkillManager()
    skill_manager.load_builtin_skills()

    if current_custom_dir:
        try:
            skill_manager.load_custom_skills(current_custom_dir)
        except Exception as exc:
            logger.warning("[AgentFactory] Failed to load custom skills from %s: %s", current_custom_dir, exc)

    _SKILL_MANAGER_PROTOTYPE = skill_manager
    _SKILL_MANAGER_CUSTOM_DIR = current_custom_dir
    logger.info("[AgentFactory] SkillManager prototype cached (%d skills)", len(skill_manager.list_skills()))
    return copy.deepcopy(_SKILL_MANAGER_PROTOTYPE)


def resolve_skill_prompt_state(config=None, skills: Optional[List[str]] = None) -> SkillPromptState:
    """Resolve active skills and prompt fragments for analyzer / agent entrypoints."""
    if config is None:
        from src.config import get_config
        config = get_config()

    from src.application.agent.skills.defaults import (
        get_default_active_skill_ids,
        get_default_technical_skill_policy,
        get_default_trading_skill_policy,
    )

    skill_manager = get_skill_manager(config)
    skill_catalog = list(skill_manager.list_skills())
    available_skill_ids = {
        str(getattr(skill, "name", "")).strip()
        for skill in skill_catalog
        if str(getattr(skill, "name", "")).strip()
    }
    configured_skills = getattr(config, "agent_skills", None)
    if configured_skills == []:
        configured_skills = None
    default_skills = get_default_active_skill_ids(
        skill_catalog,
        available_skill_ids=available_skill_ids or None,
    )
    skills_to_activate, explicit_skill_selection = _resolve_selected_skill_ids(
        requested_skills=skills,
        configured_skills=configured_skills,
        default_skills=default_skills,
        available_skill_ids=available_skill_ids,
    )

    use_legacy_default_prompt = _should_use_legacy_default_prompt(
        skills_to_activate=skills_to_activate,
        explicit_skill_selection=explicit_skill_selection,
        skill_catalog=skill_catalog,
    )

    skill_manager.activate(skills_to_activate)
    logger.info("[AgentFactory] Activated skills: %s", skills_to_activate)

    return SkillPromptState(
        skill_manager=skill_manager,
        skills_to_activate=skills_to_activate,
        explicit_skill_selection=explicit_skill_selection,
        use_legacy_default_prompt=use_legacy_default_prompt,
        skill_instructions=skill_manager.get_skill_instructions(),
        default_skill_policy=get_default_trading_skill_policy(
            explicit_skill_selection=not use_legacy_default_prompt,
        ),
        technical_skill_policy=get_default_technical_skill_policy(
            explicit_skill_selection=not use_legacy_default_prompt,
        ),
    )


def _build_orchestrator(config, registry, llm_adapter, skill_manager, *, technical_skill_policy: str = ""):
    """Build and return an :class:`AgentOrchestrator` (multi-agent mode).

    The orchestrator presents the same ``run()`` / ``chat()`` interface as
    :class:`AgentExecutor` so callers need no changes.
    """
    from src.application.agent.orchestrator import AgentOrchestrator

    mode = getattr(config, "agent_orchestrator_mode", "standard")
    logger.info("[AgentFactory] Building AgentOrchestrator (mode=%s)", mode)

    return AgentOrchestrator(
        tool_registry=registry,
        llm_adapter=llm_adapter,
        skill_instructions=skill_manager.get_skill_instructions(),
        technical_skill_policy=technical_skill_policy,
        max_steps=_coerce_config_int(
            getattr(config, "agent_max_steps", AGENT_MAX_STEPS_DEFAULT),
            AGENT_MAX_STEPS_DEFAULT,
            field_name="agent_max_steps",
        ),
        mode=mode,
        skill_manager=skill_manager,
        config=config,
    )
