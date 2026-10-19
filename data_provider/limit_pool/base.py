# -*- coding: utf-8 -*-
"""
@file: base.py
@description: 涨跌停池能力抽象，统一涨停池 / 跌停池结果契约。
@author: Lensgcx (GaoCangxiong)

契约说明（ADR-001 §4.4）：
- `LimitPoolEntry` 为涨跌停榜单明细的唯一契约，涨停 / 跌停同构，由 `pool_type` 区分；
  后续炸板池 / 昨日涨停池按同一契约扩展 `pool_type` 枚举即可。
- 选源 / 回退 / TTL / 健康冷却统一由 `common/base.py` 的 `DataSourceManager` 提供，
  本包不重复实现缓存与降级基建。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from data_provider.common.base import DataSource, DataSourceManager

LIMIT_UP = "limit_up"
LIMIT_DOWN = "limit_down"

VALID_POOL_TYPES = (LIMIT_UP, LIMIT_DOWN)


@dataclass
class LimitPoolEntry:
    """涨跌停榜单明细（13 字段，与前端 StockLimitUpQuote / StockLimitDownQuote 对齐）。"""

    code: str = ""
    name: str = ""
    price: Optional[float] = None
    change_pct: Optional[float] = None
    amount: Optional[float] = None
    turnover_rate: Optional[float] = None
    seal_amount: Optional[float] = None
    first_limit_time: str = ""
    last_limit_time: str = ""
    break_count: Optional[int] = None
    limit_stat: str = ""
    consecutive_boards: Optional[int] = None
    industry: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转为 API 响应的 snake_case 字典（前端经 toCamelCase 转换）。"""
        return asdict(self)


@dataclass
class LimitPoolRequest:
    """涨跌停池请求。"""

    pool_type: str = LIMIT_UP
    date: Optional[str] = None
    limit: int = 20


@dataclass
class LimitPoolResult:
    """涨跌停池结果。"""

    entries: List[LimitPoolEntry] = field(default_factory=list)
    source: str = ""
    pool_type: str = LIMIT_UP
    date: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class LimitPoolDataSource(DataSource[LimitPoolRequest, LimitPoolResult]):
    """涨跌停池 source 公共抽象。"""


class LimitPoolDataSourceManager(DataSourceManager[LimitPoolRequest, LimitPoolResult]):
    """涨跌停池 Manager。"""

    def get_limit_pool(self, request: LimitPoolRequest) -> LimitPoolResult:
        """获取首个有效的涨跌停池结果。"""
        return self.fetch_first(request)

    def build_cache_key(self, request: LimitPoolRequest) -> Optional[str]:
        """按 pool_type / date / limit 构造缓存键。"""
        normalized = request.pool_type if request.pool_type in VALID_POOL_TYPES else LIMIT_UP
        return f"limit_pool:{normalized}:{request.date or 'today'}:{max(int(request.limit), 1)}"

    def is_valid_result(self, result: Optional[LimitPoolResult]) -> bool:
        """空榜不视为有效结果：既不写入缓存，也继续尝试后续 source。"""
        return result is not None and bool(result.entries)

    def describe_request(self, request: LimitPoolRequest) -> str:
        """为日志与异常生成可读请求描述。"""
        return f"pool_type={request.pool_type} date={request.date or 'today'} limit={request.limit}"


DEFAULT_SOURCE_ORDER = ("eastmoney",)


def _build_sources() -> Dict[str, LimitPoolDataSource]:
    """构造涨跌停池默认 source 注册表。"""
    from data_provider.limit_pool.eastmoney_source import EastMoneyLimitPoolSource
    from data_provider.limit_pool.stocksdk_source import StockSdkLimitPoolSource

    return {
        "eastmoney": EastMoneyLimitPoolSource(),
        "stocksdk": StockSdkLimitPoolSource(),
    }


_MANAGER = LimitPoolDataSourceManager(
    sources=_build_sources(),
    default_source_order=DEFAULT_SOURCE_ORDER,
    data_source_key="limit_pool_data_source",
    source_priority_key="limit_pool_source_priority",
    fallback_enabled_key="limit_pool_fallback_enabled",
    cache_ttl_seconds=60,
    health_cooldown_seconds=10,
)


def get_limit_pool(
    pool_type: str = LIMIT_UP,
    date: Optional[str] = None,
    n: int = 20,
) -> LimitPoolResult:
    """获取涨跌停池；全部 source 失败时抛出 LookupError，由调用方决定降级策略。"""
    normalized = pool_type if pool_type in VALID_POOL_TYPES else LIMIT_UP
    return _MANAGER.get_limit_pool(
        LimitPoolRequest(pool_type=normalized, date=date, limit=max(int(n), 1))
    )


def resolve_limit_pool_source_order() -> Iterable[str]:
    """返回当前配置生效的涨跌停池 source 顺序。"""
    return _MANAGER.resolve_source_order()
