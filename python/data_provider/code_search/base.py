# -*- coding: utf-8 -*-
"""
===================================
代码搜索能力抽象
===================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from data_provider.common.base import DataSource, DataSourceManager


@dataclass
class CodeSearchResult:
    """统一搜索结果。"""

    code: str
    name: str
    market: str
    secid: str
    source: str = ""


class CodeSearchSource(DataSource[tuple[str, int], List[CodeSearchResult]]):
    """代码搜索能力 source 公共抽象。"""

    def fetch(self, request: tuple[str, int]) -> Optional[List[CodeSearchResult]]:
        """兼容 DataSource 协议，转调 search。"""
        query, limit = request
        return self.search(query, limit=limit)

    def search(self, query: str, limit: int = 10) -> Optional[List[CodeSearchResult]]:
        """返回搜索候选列表。"""
        del query, limit
        raise NotImplementedError


class CodeSearchDataSourceManager(DataSourceManager[tuple[str, int], List[CodeSearchResult]]):
    """代码搜索能力 Manager。"""

    def search(self, query: str, limit: int = 10) -> List[CodeSearchResult]:
        """按配置顺序返回首个非空结果集。"""
        return self.fetch_first((query, limit))

    def build_cache_key(self, request: tuple[str, int]) -> Optional[str]:
        """按搜索关键词和条数构造缓存键。"""
        query, limit = request
        return f"code_search:{query.strip().lower()}:{limit}"

    def is_valid_result(self, result: Optional[List[CodeSearchResult]]) -> bool:
        """只接受非空候选列表。"""
        return bool(result)


DEFAULT_SOURCE_ORDER = ("local", "eastmoney", "stocksdk")


def _build_sources() -> Dict[str, CodeSearchSource]:
    """构造代码搜索能力默认 source 注册表。"""
    from data_provider.code_search.eastmoney_source import EastMoneyCodeSearchSource
    from data_provider.code_search.local_stockdb_source import LocalStockDbCodeSearchSource
    from data_provider.code_search.stocksdk_source import StockSdkCodeSearchSource

    return {
        "local": LocalStockDbCodeSearchSource(),
        "eastmoney": EastMoneyCodeSearchSource(),
        "stocksdk": StockSdkCodeSearchSource(),
    }


_MANAGER = CodeSearchDataSourceManager(
    sources=_build_sources(),
    default_source_order=DEFAULT_SOURCE_ORDER,
    data_source_key="codesearch_data_source",
    source_priority_key="codesearch_source_priority",
    fallback_enabled_key="codesearch_fallback_enabled",
    cache_ttl_seconds=60,
    health_cooldown_seconds=10,
)


def search_codes(query: str, limit: int = 10) -> List[CodeSearchResult]:
    """按配置顺序执行股票搜索。"""
    try:
        return _MANAGER.search(query, limit=limit)
    except LookupError:
        return []


def resolve_code_search_source_order() -> Iterable[str]:
    """返回当前配置生效的代码搜索 source 顺序。"""
    return _MANAGER.resolve_source_order()
