# -*- coding: utf-8 -*-
"""市场用例（大盘、板块、市场热点与情绪榜单）。

按 ``ARCHITECTURE_TARGET.md`` §3 的业务域划分，涨跌停池归入市场情绪 / 热点榜单，
板块树、市场快照与板块资金流归入板块与市场结构，两者都落在 ``application/market/``；
``market_light`` 大盘快照用例已按同一域加入（``market_light.py``，函数式模块）；
``market_hotspot`` 仍待后续，均不按端点名新建平行包。

对外只暴露用例与错误类型；端口在 ``ports``，适配器在
``src.infrastructure.providers.{limit_pool_provider,sector_provider}``。
"""

from src.application.market.limit_pool import (
    LIMIT_DOWN,
    LIMIT_UP,
    VALID_LIMIT_POOL_TYPES,
    LimitPoolService,
)
from src.application.market.ports import LimitPoolProviderPort, SectorProviderPort
from src.application.market.sector import SectorService, SectorSnapshotUnavailableError

__all__ = [
    "LIMIT_DOWN",
    "LIMIT_UP",
    "VALID_LIMIT_POOL_TYPES",
    "LimitPoolProviderPort",
    "LimitPoolService",
    "SectorProviderPort",
    "SectorService",
    "SectorSnapshotUnavailableError",
]
