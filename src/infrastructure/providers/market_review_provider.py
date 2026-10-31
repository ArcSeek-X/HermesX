# -*- coding: utf-8 -*-
"""大盘复盘取数适配器：实现 :class:`MarketReviewDataPort`。

``MarketAnalyzer`` 需要指数行情、涨跌统计与行业 / 概念排行三类能力。迁移前该用例
直接构造 ``DataFetcherManager``；现由本适配器承接 ``data_provider`` 依赖，由
``src.bootstrap.market.configure_market_review`` 在进程启动时把本类注册为默认工厂，
使 ``src/application/`` 不直接 import 数据源包。

两点刻意的保持一致：

- **不复用** ``DataSectorRankingProvider``：后者走 ``data_provider.sector.base``，
  与 ``DataFetcherManager`` 的选源优先级、健康冷却与 TTL 缓存不同；本适配器直连
  manager，保持与原实现逐字一致的取数路径与返回形状。
- 每个适配器实例持有独立 manager（与原实现「每个 ``MarketAnalyzer`` 一个
  manager」一致，避免跨用例共享实例内部状态）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from data_provider.base import DataFetcherManager


class DataProviderMarketReviewProvider:
    """通过 ``DataFetcherManager`` 获取大盘复盘所需的行情与榜单。"""

    def __init__(self) -> None:
        self._manager = DataFetcherManager()

    def get_main_indices(self, region: str = "cn") -> List[Dict[str, Any]]:
        return self._manager.get_main_indices(region=region)

    def get_market_stats(self, *, purpose: str = "unspecified") -> Dict[str, Any]:
        return self._manager.get_market_stats(purpose=purpose)

    def get_sector_rankings(
        self, limit: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        return self._manager.get_sector_rankings(limit)

    def get_concept_rankings(
        self, limit: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        return self._manager.get_concept_rankings(limit)
