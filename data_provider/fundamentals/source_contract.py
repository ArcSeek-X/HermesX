"""基本面请求/结果与 Source 协议；不触发默认源注册或客户端装配。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from data_provider.common.base import DataSource


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
