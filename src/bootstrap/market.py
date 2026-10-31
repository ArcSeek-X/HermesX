# -*- coding: utf-8 -*-
"""市场用例的装配。

用例只依赖取数端口，具体实现绑定到 ``data_provider/limit_pool`` 与
``data_provider/sector`` 的适配器；``api`` 只通过依赖注入拿到装配好的用例，
不接触数据源包。
"""

from __future__ import annotations

from src.application.market import LimitPoolService, SectorService
from src.application.market.ports import MarketLightSnapshotRepositoryPort
from src.infrastructure.providers.limit_pool_provider import DataProviderLimitPoolProvider
from src.infrastructure.providers.sector_provider import DataProviderSectorProvider
from src.infrastructure.persistence.repositories.analysis_history_repo import (
    AnalysisHistoryRepository,
)
from src.infrastructure.persistence.repositories.analysis_repository import (
    AnalysisRepository,
)
from src.storage import DatabaseManager


def build_limit_pool_service() -> LimitPoolService:
    """装配涨跌停榜单用例。

    用例无状态、不持有数据库句柄，按请求装配即可；数据源的选源与缓存状态在
    ``data_provider`` 的 Manager 单例里，不随用例重建而失效。
    """
    return LimitPoolService(provider=DataProviderLimitPoolProvider())


def build_sector_service() -> SectorService:
    """装配板块与市场快照用例。

    用例无状态、不持有数据库句柄，按请求装配即可；各来源的选源与缓存状态在
    ``data_provider/sector/`` 的模块级缓存里，不随用例重建而失效。
    """
    return SectorService(provider=DataProviderSectorProvider())


def build_market_light_snapshot_repository() -> MarketLightSnapshotRepositoryPort:
    """装配市场灯塔历史快照仓储端口实现。

    市场灯塔用例（:mod:`src.application.market.market_light`）只依赖端口，具体的
    :class:`AnalysisRepository` + :class:`DatabaseManager` 单例在此装配；用例无状态，
    按调用装配即可，数据库句柄仍走 ``DatabaseManager`` 全局单例，行为与原用例内部
    的默认装配逐字等价。
    """
    return AnalysisRepository(DatabaseManager.get_instance())


def configure_market_review() -> None:
    """装配大盘复盘用例的默认端口。

    进程启动时调用一次（CLI 入口 / API lifespan）；两次注册均幂等，重复调用只
    会重新指向同一实现。

    - 取数端口：注册的是**工厂**而非实例，``MarketAnalyzer`` 每次构造都新建一个
      适配器（内含独立 ``DataFetcherManager``），与迁移前「每个分析器一个 manager」
      的隔离度一致。未装配时用例降级为空概览并打一次 warning，等价于原实现
      「所有数据源失败」的路径。
    - 历史落库端口：注册返回 :class:`AnalysisHistoryRepository` 的工厂，仓储在
      每次写历史时按当前 ``DatabaseManager`` 单例现建，因而对
      ``DatabaseManager.reset_instance()``（测试切换临时库）保持敏感；未装配时
      保存路径沿用原 fail-open 语义（记录未保存并返回 0）。
    """
    from src.application.market.market_analyzer import (
        set_default_market_review_data_provider_factory,
    )
    from src.application.market.market_review import set_default_history_repo_factory
    from src.infrastructure.providers.market_review_provider import (
        DataProviderMarketReviewProvider,
    )

    set_default_market_review_data_provider_factory(DataProviderMarketReviewProvider)
    set_default_history_repo_factory(
        lambda: AnalysisHistoryRepository(DatabaseManager.get_instance())
    )


def configure_market_hotspot() -> None:
    """装配市场热点用例的板块排行默认端口。

    进程启动时调用一次（API lifespan / CLI 入口）；``set_default_sector_ranking_provider``
    幂等，重复调用只会重新指向同一适配器。热点用例主路仍由调用方直接注入
    ``fetcher_manager``（如 ``DataFetcherManager``），本装配只覆盖无注入的独立构造
    兜底；未装配时优雅降级为 ``([], [])``。
    """
    from src.infrastructure.providers.sector_ranking_provider import (
        DataSectorRankingProvider,
    )
    from src.application.market.market_hotspot import (
        set_default_sector_ranking_provider,
    )

    set_default_sector_ranking_provider(DataSectorRankingProvider())
