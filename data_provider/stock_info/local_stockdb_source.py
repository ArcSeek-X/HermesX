# -*- coding: utf-8 -*-
"""
===================================
StockDB 本地基础信息源
===================================
"""

from __future__ import annotations

import logging
from typing import Optional

from data_provider.kline.transform import normalize_stockdb_daily_rows
from data_provider.stockdb_fetcher import StockDbError, get_stockdb_client
from data_provider.stock_info.base import StockInfoResult, StockInfoSource
from data_provider.stock_info.eastmoney_source import get_stock_name_from_eastmoney

logger = logging.getLogger(__name__)


class LocalStockDbStockInfoSource(StockInfoSource):
    """基于 StockDB 最近日 K 生成基础信息。"""

    source_id = "local"

    def fetch(self, stock_code: str) -> Optional[StockInfoResult]:
        client = get_stockdb_client()
        try:
            raw_rows = client.fetch_daily_bars(stock_code, limit=2)
        except StockDbError as exc:
            logger.warning("[LocalStockDbStockInfoSource] request failed: %s", exc)
            return None
        rows = normalize_stockdb_daily_rows(raw_rows if isinstance(raw_rows, list) else [])
        if not rows:
            return None
        last_row = rows[-1]
        prev_close = last_row.get("prev_close")
        if prev_close is None and len(rows) > 1:
            prev_close = rows[-2].get("close")
        current_price = last_row.get("close")
        change = current_price - prev_close if current_price is not None and prev_close is not None else None
        amplitude = (
            round((last_row["high"] - last_row["low"]) / prev_close * 100, 2)
            if last_row.get("high") is not None and last_row.get("low") is not None and prev_close not in (None, 0)
            else None
        )
        return StockInfoResult(
            stock_code=stock_code,
            stock_name=get_stock_name_from_eastmoney(stock_code),
            current_price=current_price or 0.0,
            change=change,
            change_percent=last_row.get("change_percent"),
            open=last_row.get("open"),
            prev_close=prev_close,
            high=last_row.get("high"),
            low=last_row.get("low"),
            volume=last_row.get("volume"),
            amount=last_row.get("amount"),
            turnover_rate=last_row.get("turnover_rate"),
            amplitude=amplitude,
            source=self.source_id,
        )
