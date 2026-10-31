# -*- coding: utf-8 -*-
"""板块排行取数适配器：实现 :class:`SectorRankingPort`。

市场热点用例（:mod:`src.application.market.market_hotspot`）需要行业 / 概念板块
排行能力。具体 ``data_provider.sector`` 依赖收敛在本适配器，由
``src.bootstrap.market`` 在进程启动时注入为用例的默认端口实现，使应用侧不直接
import 数据源包。返回 ``(top_sectors, bottom_sectors)`` 二元组，与原
``_SectorRankingGateway`` 契约逐字一致。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from data_provider.sector import base as sector_base


class DataSectorRankingProvider:
    """通过 ``data_provider.sector.base`` 获取板块 / 概念排行。"""

    def get_sector_rankings(self, limit: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        result = sector_base.get_sector_rankings(limit)
        return result.top_sectors, result.bottom_sectors

    def get_concept_rankings(self, limit: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        result = sector_base.get_concept_rankings(limit)
        return result.top_sectors, result.bottom_sectors
