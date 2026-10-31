# -*- coding: utf-8 -*-
"""FastAPI application lifespan shared by ``server.py``, ``webui.py`` and
``main.py --serve``.

The lifespan owns process-level resources only: the runtime scheduler, the
shared system-config service and best-effort cache warmups. It is attached to
the ASGI app by ``api.app.create_app``; importing that module must not start any
of these resources.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, Any, Dict

from starlette.concurrency import run_in_threadpool

from src.application.runtime.runtime_scheduler import (
    CLI_SCHEDULER_OWNER_ENV,
    RUNTIME_SCHEDULER_ARGS_ENV,
    RUNTIME_SCHEDULER_FORCE_ENABLED_ENV,
    RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV,
    RUNTIME_SCHEDULER_SUPPRESS_START_ENV,
    RuntimeSchedulerService,
)
from src.application.quote.stock_index_remote_service import (
    refresh_remote_stock_index_cache,
    settings_from_config,
)
from src.application.runtime.system_config_service import SystemConfigService
from src.bootstrap.history import configure_history_loader
from src.bootstrap.runtime import configure_task_service
from src.bootstrap.alphasift import configure_alphasift_runtime
from src.bootstrap.system_config import configure_system_config_runtime
from src.bootstrap.analyzer import configure_analyzer_runtime
from src.bootstrap.generation import configure_generation_runtime
from src.bootstrap.intelligence import (
    configure_intelligence_repository,
    configure_news_source,
    configure_search,
)
from src.bootstrap.market import configure_market_hotspot, configure_market_review
from src.bootstrap.decision import (
    configure_decision_repositories,
    configure_signal_scanner,
)
from src.bootstrap.quote import (
    configure_intraday_timeline_bridge,
    configure_market_snapshot,
    configure_name_to_code_resolver,
    configure_stock_repository,
)
from src.bootstrap.portfolio import (
    configure_portfolio_repository,
    configure_portfolio_risk_belong_boards,
    configure_portfolio_service_realtime,
)
from src.bootstrap.notification import (
    configure_image_render_port,
    configure_notification_send_port,
)
from src.bootstrap.analysis import (
    configure_analysis_pipeline_persistence,
    configure_stock_data_port,
    configure_vision_completion_port,
)
from src.bootstrap.agent import (
    configure_agent_conversation,
    configure_agent_memory,
    configure_market_data,
    configure_provider_trace,
    configure_usage_telemetry,
    configure_tools_db,
)

if TYPE_CHECKING:  # pragma: no cover - typing only, keeps bootstrap framework-free
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUTHY_VALUES


def _load_runtime_scheduler_args() -> Dict[str, Any]:
    raw_value = os.getenv(RUNTIME_SCHEDULER_ARGS_ENV)
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        logger.warning("Invalid %s payload; runtime scheduler uses default args", RUNTIME_SCHEDULER_ARGS_ENV)
        return {}
    if not isinstance(parsed, dict):
        logger.warning("%s payload is not an object; runtime scheduler uses default args", RUNTIME_SCHEDULER_ARGS_ENV)
        return {}
    return parsed


async def _refresh_stock_index_cache_in_background(reason: str) -> None:
    try:
        from src.config import get_config

        settings = settings_from_config(get_config())
        result = await run_in_threadpool(refresh_remote_stock_index_cache, settings)
        if result.refreshed:
            logger.info("[stock-index] background refresh completed (%s): %s", reason, result.cache_path)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - index refresh must stay best-effort.
        logger.warning("[stock-index] background refresh failed (%s): %s", reason, exc)


def schedule_stock_index_background_refresh(app: "FastAPI", reason: str) -> None:
    """Refresh the stock autocomplete index without blocking the caller."""
    task = getattr(app.state, "stock_index_refresh_task", None)
    if task is not None and not task.done():
        return

    app.state.stock_index_refresh_task = asyncio.create_task(
        _refresh_stock_index_cache_in_background(reason)
    )


async def _warm_market_cards_cache_in_background() -> None:
    """Warm the /market/index card cache so the first page hit is not cold."""
    try:
        from data_provider.sector.market_cards_source import warm_market_cards_cache

        await run_in_threadpool(warm_market_cards_cache)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - warmup must stay best-effort.
        logger.warning("[market-cards] background warmup failed: %s", exc)


def _schedule_market_cards_warmup(app: "FastAPI") -> None:
    """Schedule startup warmup of the aggregated market card cache."""
    task = getattr(app.state, "market_cards_warmup_task", None)
    if task is not None and not task.done():
        return

    app.state.market_cards_warmup_task = asyncio.create_task(
        _warm_market_cards_cache_in_background()
    )


@asynccontextmanager
async def app_lifespan(app: "FastAPI"):
    """Initialize and release shared services for the app lifecycle."""
    runtime_owns_schedule = not _env_truthy(CLI_SCHEDULER_OWNER_ENV)
    runtime_force_enabled = _env_truthy(RUNTIME_SCHEDULER_FORCE_ENABLED_ENV)
    runtime_suppress_start = _env_truthy(RUNTIME_SCHEDULER_SUPPRESS_START_ENV)
    runtime_run_immediately_override = os.getenv(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV)
    if runtime_suppress_start or not runtime_owns_schedule:
        runtime_run_immediately = False
    elif runtime_run_immediately_override is None:
        from src.config import get_config

        runtime_run_immediately = bool(getattr(get_config(), "schedule_run_immediately", False))
    else:
        runtime_run_immediately = runtime_run_immediately_override.strip().lower() in _TRUTHY_VALUES
    runtime_scheduler_args = _load_runtime_scheduler_args()
    os.environ.pop(RUNTIME_SCHEDULER_FORCE_ENABLED_ENV, None)
    os.environ.pop(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV, None)
    os.environ.pop(RUNTIME_SCHEDULER_SUPPRESS_START_ENV, None)
    os.environ.pop(RUNTIME_SCHEDULER_ARGS_ENV, None)
    runtime_scheduler_service = RuntimeSchedulerService(
        owns_schedule=runtime_owns_schedule,
        force_enabled=runtime_force_enabled,
        run_immediately_in_background=True,
        schedule_args_overrides=runtime_scheduler_args,
    )
    app.state.runtime_scheduler_service = runtime_scheduler_service
    if not runtime_suppress_start:
        app.state.runtime_scheduler_service.reconcile_from_config(
            run_immediately=runtime_run_immediately,
        )
    app.state.system_config_service = SystemConfigService(
        runtime_scheduler=app.state.runtime_scheduler_service,
    )
    configure_history_loader()
    configure_task_service()
    configure_market_hotspot()
    configure_market_review()
    configure_signal_scanner()
    configure_decision_repositories()
    configure_name_to_code_resolver()
    configure_intraday_timeline_bridge()
    configure_market_snapshot()
    configure_stock_repository()
    configure_news_source()
    configure_intelligence_repository()
    configure_search()
    configure_alphasift_runtime()
    configure_system_config_runtime()
    configure_analyzer_runtime()
    configure_generation_runtime()
    configure_portfolio_repository()
    configure_portfolio_risk_belong_boards()
    configure_portfolio_service_realtime()
    configure_notification_send_port()
    configure_image_render_port()
    configure_stock_data_port()
    # W4.2：与取数端口同批装配个股分析持久化端口（幂等，主流程必需能力）。
    configure_analysis_pipeline_persistence()
    # W5.5：装配图片识别（Vision）LLM 调用端口（幂等，未装配时识别接口显式报错）。
    configure_vision_completion_port()
    configure_market_data()
    configure_usage_telemetry()
    configure_agent_memory()
    configure_provider_trace()
    configure_tools_db()
    configure_agent_conversation()
    schedule_stock_index_background_refresh(app, "startup")
    _schedule_market_cards_warmup(app)
    try:
        yield
    finally:
        refresh_task = getattr(app.state, "stock_index_refresh_task", None)
        if refresh_task is not None and not refresh_task.done():
            refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await refresh_task
        warmup_task = getattr(app.state, "market_cards_warmup_task", None)
        if warmup_task is not None and not warmup_task.done():
            warmup_task.cancel()
            with suppress(asyncio.CancelledError):
                await warmup_task
        if hasattr(app.state, "system_config_service"):
            delattr(app.state, "system_config_service")
        runtime_scheduler = getattr(app.state, "runtime_scheduler_service", None)
        if runtime_scheduler is not None:
            runtime_scheduler.stop()
            delattr(app.state, "runtime_scheduler_service")
