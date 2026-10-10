# -*- coding: utf-8 -*-
"""
===================================
StockDB 本地 K 线源
===================================
"""

from __future__ import annotations

import logging
from typing import Optional

from data_provider.common.normalize import code_to_secid
from data_provider.kline.base import KLineDataSource, KLineRequest, KLineResult
from data_provider.kline.transform import (
    apply_stockdb_adjust,
    normalize_stockdb_daily_rows,
    normalize_stockdb_minute_rows,
    resample_rows,
    trim_rows,
)
from data_provider.stockdb_fetcher import StockDbError, get_stockdb_client

logger = logging.getLogger(__name__)


class LocalStockDbKLineSource(KLineDataSource):
    """StockDB 本地源。"""

    source_id = "local"

    def fetch(self, request: KLineRequest) -> Optional[KLineResult]:
        client = get_stockdb_client()
        try:
            prev_close = None
            if request.period in {"1m", "5m", "15m", "30m", "60m", "120m"}:
                raw_rows = client.fetch_minute_bars(request.stock_code, limit=request.limit)
                rows = normalize_stockdb_minute_rows(raw_rows if isinstance(raw_rows, list) else [])
                rows = resample_rows(rows, request.period)
                latest_daily = client.fetch_daily_bars(request.stock_code, limit=1)
                latest_daily_rows = normalize_stockdb_daily_rows(latest_daily if isinstance(latest_daily, list) else [])
                if latest_daily_rows:
                    prev_close = latest_daily_rows[-1].get("prev_close")
            else:
                raw_rows = client.fetch_daily_bars(request.stock_code, limit=max(request.limit * 5, request.limit))
                rows = normalize_stockdb_daily_rows(raw_rows if isinstance(raw_rows, list) else [])
                if request.fqt in (1, 2):
                    fq = "qfq" if request.fqt == 1 else "hfq"
                    factors = client.fetch_adjust_factors(request.stock_code)
                    rows = apply_stockdb_adjust(rows, factors if isinstance(factors, list) else [], fq)
                rows = resample_rows(rows, request.period)
            rows = trim_rows(rows, request.limit, request.before_date)
            if not rows:
                return None
            prev_close = prev_close or rows[0].get("prev_close")
            if prev_close is None and len(rows) > 1:
                prev_close = rows[-2].get("close")
            return KLineResult(
                stock_code=request.stock_code,
                stock_name=None,
                period=request.period,
                secid=code_to_secid(request.stock_code),
                prev_close=prev_close,
                data=rows,
                source=self.source_id,
            )
        except StockDbError as exc:
            logger.warning("[LocalStockDbKLineSource] stockdb request failed: %s", exc)
            return None
