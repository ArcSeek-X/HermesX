# -*- coding: utf-8 -*-
"""
@file: base.py
@description: 基本面能力抽象，统一财报 / 估值类结果契约。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

from data_provider.common.base import DataSource, DataSourceManager


@dataclass
class FundamentalsRequest:
    """基本面请求。"""

    stock_code: str
    budget_seconds: float = 4.0


@dataclass
class FundamentalsResult:
    """基本面结果。"""

    stock_code: str
    payload: Dict[str, Any]
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class FundamentalsDataSource(DataSource[FundamentalsRequest, FundamentalsResult]):
    """基本面能力 source 公共抽象。"""


class FundamentalsDataSourceManager(DataSourceManager[FundamentalsRequest, FundamentalsResult]):
    """基本面能力 Manager。"""

    def get_fundamentals(self, request: FundamentalsRequest) -> FundamentalsResult:
        """获取首个有效的基本面结果。"""
        return self.fetch_first(request)

    def build_cache_key(self, request: FundamentalsRequest) -> Optional[str]:
        """按股票代码构造缓存键。"""
        return f"fundamentals:{request.stock_code}"

    def is_valid_result(self, result: Optional[FundamentalsResult]) -> bool:
        """基本面结果至少要包含有效 payload。"""
        return result is not None and bool(result.payload)


DEFAULT_SOURCE_ORDER = ("tushare",)


def _build_sources() -> Dict[str, FundamentalsDataSource]:
    """构造基本面能力默认 source 注册表。"""
    from data_provider.fundamentals.tushare_source import TushareFundamentalsSource

    return {"tushare": TushareFundamentalsSource()}


_MANAGER = FundamentalsDataSourceManager(
    sources=_build_sources(),
    default_source_order=DEFAULT_SOURCE_ORDER,
    data_source_key="fundamentals_data_source",
    source_priority_key="fundamentals_source_priority",
    fallback_enabled_key="fundamentals_fallback_enabled",
    cache_ttl_seconds=60,
    health_cooldown_seconds=10,
)


def get_fundamental_context(stock_code: str, budget_seconds: float = 4.0) -> FundamentalsResult:
    """按配置顺序获取个股基本面上下文。"""
    return _MANAGER.get_fundamentals(
        FundamentalsRequest(stock_code=stock_code, budget_seconds=budget_seconds)
    )


def resolve_fundamentals_source_order() -> Iterable[str]:
    """返回当前配置生效的基本面 source 顺序。"""
    return _MANAGER.resolve_source_order()
