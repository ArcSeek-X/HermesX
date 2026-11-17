"""limit_pool 轻量请求/结果与 Source 契约；不创建默认源或运行资源。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from data_provider.common.base import DataSource

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
