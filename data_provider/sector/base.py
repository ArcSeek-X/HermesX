# -*- coding: utf-8 -*-
"""
@file: base.py
@description: 板块能力抽象，统一板块排行类结果契约。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from data_provider.common.base import DataSource, DataSourceManager


@dataclass
class SectorRankingRequest:
    """板块排行请求。"""

    limit: int = 5
    ranking_type: str = "sector"


@dataclass
class SectorRankingResult:
    """板块排行结果。"""

    top_sectors: List[Dict[str, Any]]
    bottom_sectors: List[Dict[str, Any]]
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SectorDataSource(DataSource[SectorRankingRequest, SectorRankingResult]):
    """板块能力 source 公共抽象。"""


class SectorDataSourceManager(DataSourceManager[SectorRankingRequest, SectorRankingResult]):
    """板块能力 Manager。"""

    def get_sector_rankings(self, request: SectorRankingRequest) -> SectorRankingResult:
        """获取首个有效的板块排行结果。"""
        return self.fetch_first(request)

    def build_cache_key(self, request: SectorRankingRequest) -> Optional[str]:
        """按 top N 构造缓存键。"""
        return f"{request.ranking_type}_rankings:{max(int(request.limit), 1)}"

    def is_valid_result(self, result: Optional[SectorRankingResult]) -> bool:
        """板块结果至少要有一侧非空。"""
        return result is not None and bool(result.top_sectors or result.bottom_sectors)


DEFAULT_SOURCE_ORDER = ("eastmoney",)


def _build_sources() -> Dict[str, SectorDataSource]:
    """构造板块能力默认 source 注册表。"""
    from data_provider.sector.eastmoney_source import EastMoneySectorSource

    return {"eastmoney": EastMoneySectorSource()}


_MANAGER = SectorDataSourceManager(
    sources=_build_sources(),
    default_source_order=DEFAULT_SOURCE_ORDER,
    data_source_key="sector_data_source",
    source_priority_key="sector_source_priority",
    fallback_enabled_key="sector_fallback_enabled",
    cache_ttl_seconds=30,
    health_cooldown_seconds=10,
)


def get_sector_rankings(limit: int = 5) -> SectorRankingResult:
    """获取行业板块排行。"""
    return _MANAGER.get_sector_rankings(SectorRankingRequest(limit=limit, ranking_type="sector"))


def get_concept_rankings(limit: int = 5) -> SectorRankingResult:
    """获取概念板块排行。"""
    return _MANAGER.get_sector_rankings(SectorRankingRequest(limit=limit, ranking_type="concept"))


def resolve_sector_source_order() -> Iterable[str]:
    """返回当前配置生效的板块 source 顺序。"""
    return _MANAGER.resolve_source_order()
