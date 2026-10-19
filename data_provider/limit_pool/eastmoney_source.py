# -*- coding: utf-8 -*-
"""
@file: eastmoney_source.py
@description: 涨跌停池东财 source，复用既有 akshare 东财股池通道（不重写取数）。
@author: Lensgcx (GaoCangxiong)

按 ADR-001 §4.4「既有文件处置」，`akshare_fetcher.py` 作为物理后端保留：
`stock_zt_pool_em`（涨停股池）/ `stock_zt_pool_dtgc_em`（跌停股池）的抓取、排序与时间
标准化仍由 AkshareFetcher 承载，本文件只做「通道结果 → LimitPoolResult」的契约映射。
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from data_provider.akshare_fetcher import AkshareFetcher
from data_provider.limit_pool.base import (
    LIMIT_DOWN,
    LimitPoolDataSource,
    LimitPoolEntry,
    LimitPoolRequest,
    LimitPoolResult,
)

logger = logging.getLogger(__name__)


def _to_float(value: Any) -> Optional[float]:
    """安全转 float；不可转换返回 None。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    """安全转 int；不可转换返回 None。"""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class EastMoneyLimitPoolSource(LimitPoolDataSource):
    """复用 AkshareFetcher.get_limit_up_pool / get_limit_down_pool 的东财涨跌停池 source。"""

    source_id = "eastmoney"

    def __init__(self) -> None:
        self.fetcher = AkshareFetcher()

    def fetch(self, request: LimitPoolRequest) -> Optional[LimitPoolResult]:
        """获取东财涨停池 / 跌停池，并映射为统一契约。"""
        limit = max(int(request.limit), 1)
        pool_type = str(request.pool_type or "").strip().lower()
        is_limit_down = pool_type == LIMIT_DOWN

        try:
            if is_limit_down:
                rows = self.fetcher.get_limit_down_pool(date=request.date, n=limit)
            else:
                rows = self.fetcher.get_limit_up_pool(date=request.date, n=limit)
        except Exception as exc:  # 物理后端异常交由 Manager 聚合与回退
            logger.warning("[limit_pool][eastmoney] 取数失败: pool_type=%s error=%s", pool_type, exc)
            return None

        if not rows:
            return None

        entries = [self._to_entry(row) for row in rows if isinstance(row, Mapping)]
        entries = [entry for entry in entries if entry.code]
        if not entries:
            return None

        return LimitPoolResult(
            entries=entries,
            source=self.source_id,
            pool_type=pool_type,
            date=str(request.date or ""),
            metadata={"limit": limit},
        )

    @staticmethod
    def _to_entry(row: Mapping[str, Any]) -> LimitPoolEntry:
        """单行 → LimitPoolEntry 契约映射。"""
        return LimitPoolEntry(
            code=str(row.get("code") or "").strip(),
            name=str(row.get("name") or "").strip(),
            price=_to_float(row.get("price")),
            change_pct=_to_float(row.get("change_pct")),
            amount=_to_float(row.get("amount")),
            turnover_rate=_to_float(row.get("turnover_rate")),
            seal_amount=_to_float(row.get("seal_amount")),
            first_limit_time=str(row.get("first_limit_time") or "").strip(),
            last_limit_time=str(row.get("last_limit_time") or "").strip(),
            break_count=_to_int(row.get("break_count")),
            limit_stat=str(row.get("limit_stat") or "").strip(),
            consecutive_boards=_to_int(row.get("consecutive_boards")),
            industry=str(row.get("industry") or "").strip(),
        )
