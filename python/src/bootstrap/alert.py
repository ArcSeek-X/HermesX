# -*- coding: utf-8 -*-
"""告警服务/后台轮询装配（自顶向下 DI）。

``build_alert_service()`` 从 ``DatabaseManager`` 单例装配仓储，并注入
``DataProviderAlertDailyBarFetcher``（实现 ``DailyBarFetcherPort``）。
``build_alert_worker()`` 为调度/后台轮询装配 ``AlertWorker``，并将带取数端口的
service 自上向下注入，避免 ``src/application/`` 反向依赖 ``src.bootstrap``。
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from src.application.alert.service import AlertService
from src.application.alert.worker import AlertWorker
from src.storage import DatabaseManager


def configure_alert_realtime_quote() -> None:
    """装配 ``EventMonitor`` 的实时行情端口（幂等）。

    将实现 ``RealtimeQuotePort`` 的 ``DataProviderRealtimeQuote`` 写入
    ``src.application.alert.events`` 的模块级 seam，使价格/涨跌幅告警
    可经 ``data_provider`` 多源 fallback 取实时快照，而应用层不直接
    依赖 ``data_provider``。调度与 API 均经由 ``build_alert_service`` 装配。
    """
    from src.application.alert.events import set_realtime_quote_port
    from src.infrastructure.providers.alert_realtime_quote import (
        DataProviderRealtimeQuote,
    )

    set_realtime_quote_port(DataProviderRealtimeQuote())


def build_alert_service() -> AlertService:
    """装配带日线取数端口的 AlertService 实例。

    每次调用返回新实例（与 DatabaseManager.reset_instance() 配合时不残留旧引擎）。
    ``api/v1/endpoints/alerts.py`` 的 10 个生产构造点均应经由本工厂获取实例，
    而非直接 ``AlertService()``（后者 ``daily_bar_fetcher`` 将为 None）。
    """
    from src.infrastructure.providers.alert_daily_bar import (
        DataProviderAlertDailyBarFetcher,
    )
    from src.infrastructure.persistence.repositories.alert_repository import (
        AlertRepository,
    )

    configure_alert_realtime_quote()
    db = DatabaseManager.get_instance()
    return AlertService(
        daily_bar_fetcher=DataProviderAlertDailyBarFetcher(),
        repository=AlertRepository(db),
        history_repo=db,
    )


def build_alert_worker(
    *,
    config_provider: Optional[Callable[[], Any]] = None,
) -> AlertWorker:
    """装配带注入 service 的 AlertWorker（调度/后台轮询入口）。

    ``AlertWorker`` 的 ``service`` 为必传依赖；本工厂在调用 ``build_alert_service()``
    后注入，使 ``main.py`` / ``runtime_scheduler`` 不直接接触 ``AlertService`` 装配细节。
    """
    return AlertWorker(
        config_provider=config_provider,
        service=build_alert_service(),
    )
