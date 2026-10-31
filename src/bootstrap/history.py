# -*- coding: utf-8 -*-
"""分析历史用例的装配。

用例需要「历史读写」与「股票代码归一化」两个能力：前者由 ``DatabaseManager``
（内部已委托给 ``persistence.repositories``）提供，后者由 ``data_provider.base``
经 ``src.infrastructure.indexing`` 适配；``api`` 只通过依赖注入拿到装配好的
:class:`~src.application.history.service.HistoryQueryService`。
"""

from __future__ import annotations

from src.application.history import HistoryQueryService
from src.infrastructure.indexing.stock_code_normalizer import (
    DataProviderStockCodeNormalizer,
)
from src.storage import DatabaseManager


def build_history_query_service() -> HistoryQueryService:
    """按当前进程的数据库单例装配分析历史用例。

    每次调用返回无状态用例对象而不缓存：``DatabaseManager.reset_instance()`` 之后
    新建的用例会绑定到新的管理器，不会残留已释放的引擎引用。
    """
    return HistoryQueryService(
        repository=DatabaseManager.get_instance(),
        code_normalizer=DataProviderStockCodeNormalizer(),
    )


def configure_history_loader() -> None:
    """装配 ``history_loader`` 日线取数的网络回退端口。

    进程启动时调用一次（API lifespan / CLI 入口）；``set_history_daily_bar_fetcher``
    幂等，重复调用只会重新指向同一适配器。未装配时 loader 的网络回退优雅降级为
    ``(None, "none")``（DB-first 主路仍可用）。
    """
    from src.infrastructure.providers.history_daily_bar import (
        DataProviderHistoryDailyBarFetcher,
    )
    from src.application.history.loader import (
        set_history_daily_bar_fetcher,
        set_history_kline_repo,
    )
    from src.application.history.comparison import set_history_repo

    set_history_daily_bar_fetcher(DataProviderHistoryDailyBarFetcher())
    # 装配历史域「DB 直连」两处 seam：loader 的 K 线 DB 主路与 comparison 的信号对比取数，
    # 均以 DatabaseManager 门面作端口适配器（bootstrap→storage 合法）；setter 幂等。
    _db = DatabaseManager.get_instance()
    set_history_kline_repo(_db)
    set_history_repo(_db)
