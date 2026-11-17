# -*- coding: utf-8 -*-
"""
@file: base.py
@description: 机构数据能力抽象，统一机构持仓 / 买卖超结果契约。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from data_provider.common.base import DataSource, DataSourceManager


@dataclass
class InstitutionalRequest:
    """机构数据请求。"""

    stock_code: str
    date: Optional[str] = None


@dataclass
class InstitutionalResult:
    """机构数据结果。"""

    stock_code: str
    payload: Dict[str, Any]
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class InstitutionalDataSource(DataSource[InstitutionalRequest, InstitutionalResult]):
    """机构数据 source 公共抽象。"""


class InstitutionalDataSourceManager(DataSourceManager[InstitutionalRequest, InstitutionalResult]):
    """机构数据 Manager。"""

    def get_institutional_data(self, request: InstitutionalRequest) -> InstitutionalResult:
        """获取首个有效的机构数据结果。"""
        return self.fetch_first(request)

    def build_cache_key(self, request: InstitutionalRequest) -> Optional[str]:
        """按股票代码与日期构造缓存键。"""
        return f"institutional:{request.stock_code}:{request.date or ''}"

    def is_valid_result(self, result: Optional[InstitutionalResult]) -> bool:
        """机构数据结果至少要有 payload。"""
        return result is not None and bool(result.payload)
