# -*- coding: utf-8 -*-
"""
===================================
API 依赖注入模块
===================================

职责：
1. 作为 API 依赖项的统一出口：数据库会话、配置、服务与用例
2. 会话/数据库句柄的装配在 ``src.bootstrap.database``，本模块只转出
"""

from fastapi import Request

from src.application.agent import AgentConversationService
from src.application.history import HistoryQueryService
from src.application.market import LimitPoolService, SectorService
from src.application.quote import QuoteService
from src.application.usage import UsageService
from src.application.watchlist import WatchlistService
from src.bootstrap.agent import build_agent_conversation_service
from src.bootstrap.backtest import build_backtest_service
from src.bootstrap.database import get_db, get_database_manager  # noqa: F401（对外转出）
from src.bootstrap.history import build_history_query_service
from src.bootstrap.market import build_limit_pool_service, build_sector_service
from src.bootstrap.quote import build_quote_service
from src.bootstrap.usage import build_usage_service
from src.bootstrap.watchlist import build_watchlist_service
from src.config import get_config, Config
from src.application.backtest.service import BacktestService
from src.application.runtime.system_config_service import SystemConfigService
from src.application.runtime.runtime_scheduler import RuntimeSchedulerService

# ``get_db`` / ``get_database_manager`` 从 ``src.bootstrap.database`` 原样导出（不做
# 包装），保证 ``Depends(...)`` 与 ``dependency_overrides[...]`` 拿到的是同一个函数对象。


def get_config_dep() -> Config:
    """
    获取配置依赖
    
    Returns:
        Config: 配置单例对象
    """
    return get_config()


def get_system_config_service(request: Request) -> SystemConfigService:
    """Get app-lifecycle shared SystemConfigService instance."""
    service = getattr(request.app.state, "system_config_service", None)
    if service is None:
        service = SystemConfigService()
        request.app.state.system_config_service = service
    return service


def get_runtime_scheduler_service(request: Request) -> RuntimeSchedulerService:
    """Get app-lifecycle shared RuntimeSchedulerService instance."""
    service = getattr(request.app.state, "runtime_scheduler_service", None)
    if service is None:
        service = RuntimeSchedulerService()
        request.app.state.runtime_scheduler_service = service
    return service


def get_watchlist_service() -> WatchlistService:
    """获取按当前数据库单例装配的自选股用例。

    用例无状态，按请求装配即可；不在 ``app.state`` 缓存，避免
    ``DatabaseManager.reset_instance()`` 后仍持有旧管理器。
    """
    return build_watchlist_service()


def get_usage_service() -> UsageService:
    """获取按当前数据库单例装配的 LLM 用量用例。

    与自选股用例一致：无状态、按请求装配，不缓存到 ``app.state``。
    """
    return build_usage_service()


def get_history_query_service() -> HistoryQueryService:
    """获取按当前数据库单例装配的分析历史用例。

    与自选股/用量用例一致：无状态、按请求装配，不缓存到 ``app.state``。
    """
    return build_history_query_service()


def get_limit_pool_service() -> LimitPoolService:
    """获取涨跌停榜单用例。

    用例无状态、不持有数据库句柄，按请求装配即可；选源与缓存状态在
    ``data_provider`` 的 Manager 单例里，不受重建影响。
    """
    return build_limit_pool_service()


def get_sector_service() -> SectorService:
    """获取板块与市场快照用例（行业树、市场概览、板块资金流）。

    用例无状态、不持有数据库句柄，按请求装配即可；多来源优先级与各来源缓存
    在 ``data_provider/sector/``，可在用例层直接复用，无需端点参与选源。
    """
    return build_sector_service()


def get_quote_service() -> QuoteService:
    """获取行情用例（K 线 / 代码搜索 / 基础信息）。

    用例无状态、不持有数据库句柄，按请求装配即可；可选数据源与缓存状态在
    ``data_provider`` 的各自 Manager 单例里，不受重建影响。端点持有短 TTL
    响应缓存（K 线 60s / 信息 30s / 搜索 300s），不在用例里重建。
    """
    return build_quote_service()


def get_backtest_service() -> BacktestService:
    """获取按当前数据库单例装配的回测服务。

    与其他用例一致：按请求装配，不缓存到 ``app.state``，避免
    ``DatabaseManager.reset_instance()`` 后仍持有旧管理器。
    """
    return build_backtest_service()


def get_agent_conversation_service() -> AgentConversationService:
    """获取按当前数据库单例装配的 Agent 会话用例。

    与其他用例一致：按请求装配，不缓存到 ``app.state``，避免
    ``DatabaseManager.reset_instance()`` 后仍持有旧管理器。
    """
    return build_agent_conversation_service()
