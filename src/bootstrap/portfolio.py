# -*- coding: utf-8 -*-
"""持仓用例的装配。

持仓风险用例（PortfolioRiskService）做行业集中度分块时需要"个股所属板块"这一外部
取数能力；该能力复用 ``data_provider`` 的 ``DataFetcherManager.get_belong_boards``（经
适配器 :class:`~src.infrastructure.providers.portfolio_belong_boards_provider.DataProviderPortfolioBelongBoards`
收敛到 :class:`~src.application.portfolio.ports.BelongBoardsPort`），用例侧只按端口协议
调用，不直接依赖 ``data_provider``。
"""

from __future__ import annotations


def configure_portfolio_repository() -> None:
    """装配持仓仓储端口工厂（PP-4 持久化收口）。

    将 infra 具体实现 :class:`~src.infrastructure.persistence.repositories.portfolio_repository.PortfolioRepository`
    注册为应用层 seam 工厂（注册类本身作零参/单参可调用，每次现建绑定当下
    ``DatabaseManager`` 单例、适配 ``reset_instance()``，与 PP-1 intelligence 同型）。
    ``set_portfolio_repository_factory`` 幂等：仅非 None 覆盖。
    """
    from src.application.portfolio.ports import set_portfolio_repository_factory
    from src.infrastructure.persistence.repositories.portfolio_repository import (
        PortfolioRepository,
    )

    set_portfolio_repository_factory(PortfolioRepository)


def configure_portfolio_risk_belong_boards() -> None:
    """装配持仓风险用例的板块归属取数默认端口。

    进程启动时调用一次（API lifespan / CLI 入口）；``set_belong_boards_port`` 幂等，
    重复调用只会重新指向同一适配器。未装配时优雅降级：板块归属端口缺失 → 返回空
    列表，与迁移前 ``DataFetcherManager`` 初始化失败按"无板块信息"降级语义一致。
    """
    from src.infrastructure.providers.portfolio_belong_boards_provider import (
        DataProviderPortfolioBelongBoards,
    )
    from src.application.portfolio.portfolio_risk_service import set_belong_boards_port

    set_belong_boards_port(DataProviderPortfolioBelongBoards())


def configure_portfolio_service_realtime() -> None:
    """装配持仓快照用例的实时行情取数默认端口。

    进程启动时调用一次（API lifespan / CLI 入口）；``set_realtime_port`` 幂等，
    重复调用只会重新指向同一适配器。未装配时优雅降级：实时价取数→ ``(None, None)``、
    批量预热→ no-op，与迁移前 ``DataFetcherManager`` 不可用 / 异常时按无实时价降级语义一致。
    """
    from src.infrastructure.providers.portfolio_realtime_provider import (
        DataProviderPortfolioRealtimeQuote,
    )
    from src.application.portfolio.portfolio_service import set_realtime_port

    set_realtime_port(DataProviderPortfolioRealtimeQuote())
