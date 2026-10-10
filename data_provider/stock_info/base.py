# -*- coding: utf-8 -*-
"""
===================================
基础信息能力抽象
===================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

from data_provider.common.base import DataSource, DataSourceManager


@dataclass
class StockInfoResult:
    """统一股票基础信息结果。"""

    stock_code: str
    current_price: float
    stock_name: Optional[str] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    open: Optional[float] = None
    prev_close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    turnover_rate: Optional[float] = None
    amplitude: Optional[float] = None
    pe_ratio_ttm: Optional[float] = None
    total_market_cap: Optional[float] = None
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class StockInfoSource(DataSource[str, StockInfoResult]):
    """基础信息能力 source 公共抽象。"""


class StockInfoDataSourceManager(DataSourceManager[str, StockInfoResult]):
    """基础信息能力 Manager。"""

    def get_stock_info(self, stock_code: str) -> StockInfoResult:
        """获取首个有效的股票基础信息结果。"""
        return self.fetch_first(stock_code)

    def build_cache_key(self, stock_code: str) -> Optional[str]:
        """按股票代码构造缓存键。"""
        return f"stock_info:{stock_code}"

    def is_valid_result(self, result: Optional[StockInfoResult]) -> bool:
        """基础信息结果至少要有当前价。"""
        return result is not None and result.current_price is not None

    def finalize_result(self, result: StockInfoResult, stock_code: str) -> StockInfoResult:
        """统一补齐缺失的股票名称。"""
        from data_provider.stock_info.eastmoney_source import get_stock_name_from_eastmoney

        result.stock_name = result.stock_name or get_stock_name_from_eastmoney(stock_code) or ""
        return result


DEFAULT_SOURCE_ORDER = ("local", "eastmoney", "tencent", "stocksdk")


def _build_sources() -> Dict[str, StockInfoSource]:
    """构造基础信息能力默认 source 注册表。"""
    from data_provider.stock_info.eastmoney_source import EastMoneyStockInfoSource
    from data_provider.stock_info.local_stockdb_source import LocalStockDbStockInfoSource
    from data_provider.stock_info.stocksdk_source import StockSdkStockInfoSource
    from data_provider.stock_info.tencent_source import TencentStockInfoSource

    return {
        "local": LocalStockDbStockInfoSource(),
        "eastmoney": EastMoneyStockInfoSource(),
        "tencent": TencentStockInfoSource(),
        "stocksdk": StockSdkStockInfoSource(),
    }


_MANAGER = StockInfoDataSourceManager(
    sources=_build_sources(),
    default_source_order=DEFAULT_SOURCE_ORDER,
    data_source_key="stockinfo_data_source",
    source_priority_key="stockinfo_source_priority",
    fallback_enabled_key="stockinfo_fallback_enabled",
    cache_ttl_seconds=30,
    health_cooldown_seconds=10,
)


def get_stock_info(stock_code: str) -> StockInfoResult:
    """按配置顺序获取股票基础信息。"""
    return _MANAGER.get_stock_info(stock_code)


def resolve_stock_info_source_order() -> Iterable[str]:
    """返回当前配置生效的基础信息 source 顺序。"""
    return _MANAGER.resolve_source_order()
