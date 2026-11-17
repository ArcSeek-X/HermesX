# -*- coding: utf-8 -*-
"""
===================================
K 线基础能力抽象
===================================

职责：
1. 定义 K 线统一数据结构，避免端点层直接感知上游源差异。
2. 定义 K 线数据源协议，便于按 source 维度切换本地/远端实现。
3. 约束标准化返回，保证 /api/v1/kline 契约稳定。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from data_provider.common.base import DataSource, DataSourceManager


KLINE_PERIODS = (
    "1m",
    "5m",
    "15m",
    "30m",
    "60m",
    "120m",
    "5d",
    "daily",
    "weekly",
    "monthly",
    "yearly",
)

KLINE_ADJUSTMENT_TO_FQT = {
    "none": 0,
    "qfq": 1,
    "hfq": 2,
}


@dataclass
class KLineRequest:
    """K 线标准入参。"""

    stock_code: str
    period: str
    limit: int
    fqt: int = 1
    before_date: Optional[str] = None


@dataclass
class KLineResult:
    """K 线标准出参。"""

    stock_code: str
    period: str
    secid: str
    data: List[Dict[str, Any]]
    stock_name: Optional[str] = None
    prev_close: Optional[float] = None
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class KLineDataSource(DataSource[KLineRequest, KLineResult]):
    """K 线能力 source 公共抽象。"""


class KLineDataSourceManager(DataSourceManager[KLineRequest, KLineResult]):
    """K 线能力 Manager，负责统一选源、回退与结果补齐。"""

    def get_kline(self, request: KLineRequest) -> KLineResult:
        """获取首个有效的 K 线结果。"""
        if request.period not in KLINE_PERIODS:
            raise ValueError(f"Unsupported period: {request.period}")
        return self.fetch_first(request)

    def build_cache_key(self, request: KLineRequest) -> Optional[str]:
        """按代码、周期、复权、翻页游标构造缓存键。"""
        return (
            "kline:"
            f"{request.stock_code}:{request.period}:{request.fqt}:{request.limit}:{request.before_date or ''}"
        )

    def is_valid_result(self, result: Optional[KLineResult]) -> bool:
        """K 线结果至少要包含非空数据数组。"""
        return result is not None and bool(result.data)

    def finalize_result(self, result: KLineResult, request: KLineRequest) -> KLineResult:
        """统一补齐股票名称与前收价。"""
        from data_provider.stock_info.eastmoney_source import get_stock_name_from_eastmoney

        result.stock_name = result.stock_name or get_stock_name_from_eastmoney(request.stock_code) or ""
        if result.prev_close is None and result.data:
            first = result.data[0]
            result.prev_close = first.get("prev_close") or first.get("close")
        return result

    def describe_request(self, request: KLineRequest) -> str:
        """生成便于定位问题的请求描述。"""
        return f"{request.stock_code}/{request.period}"


DEFAULT_SOURCE_ORDER = ("local", "sina", "eastmoney", "tencent", "stocksdk")


def _build_sources() -> Dict[str, KLineDataSource]:
    """构造 K 线能力默认 source 注册表。"""
    from data_provider.kline.eastmoney_source import EastMoneyKLineSource
    from data_provider.kline.local_stockdb_source import LocalStockDbKLineSource
    from data_provider.kline.sina_source import SinaKLineSource
    from data_provider.kline.stocksdk_source import StockSdkKLineSource
    from data_provider.kline.tencent_source import TencentKLineSource

    return {
        "local": LocalStockDbKLineSource(),
        "sina": SinaKLineSource(),
        "eastmoney": EastMoneyKLineSource(),
        "tencent": TencentKLineSource(),
        "stocksdk": StockSdkKLineSource(),
    }


_MANAGER = KLineDataSourceManager(
    sources=_build_sources(),
    default_source_order=DEFAULT_SOURCE_ORDER,
    data_source_key="kline_data_source",
    source_priority_key="kline_source_priority",
    fallback_enabled_key="kline_fallback_enabled",
    cache_ttl_seconds=30,
    health_cooldown_seconds=10,
)


def get_kline_data(request: KLineRequest) -> KLineResult:
    """按配置顺序获取 K 线结果。"""
    return _MANAGER.get_kline(request)


def resolve_kline_source_order() -> Iterable[str]:
    """返回当前配置生效的 K 线 source 顺序。"""
    return _MANAGER.resolve_source_order()
