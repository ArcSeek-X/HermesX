"""sector 轻量请求/结果与 Source 契约；不创建默认源或运行资源。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from data_provider.common.base import DataSource


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
