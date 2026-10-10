# -*- coding: utf-8 -*-
"""
===================================
StockSDK 基础信息源
===================================
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from data_provider.stock_info.base import StockInfoResult, StockInfoSource
from data_provider.stocksdk_bridge import (
    StockSdkBridgeError,
    get_stocksdk_client,
    resolve_stocksdk_symbol,
)

logger = logging.getLogger(__name__)


class StockSdkStockInfoSource(StockInfoSource):
    """StockSDK 股票基础信息实现。"""

    source_id = "stocksdk"

    def fetch(self, stock_code: str) -> Optional[StockInfoResult]:
        client = get_stocksdk_client()
        if not client.is_available():
            return None

        try:
            quote = client.fetch_quote(stock_code)
        except StockSdkBridgeError as exc:
            logger.warning("[StockSdkStockInfoSource] bridge failed: %s", exc)
            return None
        if not isinstance(quote, dict):
            return None

        symbol = resolve_stocksdk_symbol(stock_code)
        current_price = _to_float(quote.get("price") or quote.get("currentPrice"))
        if current_price is None:
            return None

        volume = _to_float(quote.get("volume"))
        amount = _to_float(quote.get("amount"))
        total_market_cap = _to_float(
            quote.get("totalMarketCap") or quote.get("marketCap") or quote.get("total_market_cap")
        )
        circulating_market_cap = _to_float(
            quote.get("circulatingMarketCap") or quote.get("circulating_market_cap")
        )
        if symbol.market == "cn":
            volume = volume * 100 if volume is not None else None
            amount = amount * 10000 if amount is not None else None
            total_market_cap = total_market_cap * 1e8 if total_market_cap is not None else None
            circulating_market_cap = (
                circulating_market_cap * 1e8 if circulating_market_cap is not None else None
            )

        return StockInfoResult(
            stock_code=stock_code,
            stock_name=_normalize_name(quote.get("name")),
            current_price=current_price,
            change=_to_float(quote.get("change") or quote.get("changeAmount")),
            change_percent=_to_float(quote.get("changePercent") or quote.get("change_percent")),
            open=_to_float(quote.get("open")),
            prev_close=_to_float(quote.get("prevClose") or quote.get("preClose")),
            high=_to_float(quote.get("high")),
            low=_to_float(quote.get("low")),
            volume=volume,
            amount=amount,
            turnover_rate=_to_float(quote.get("turnoverRate") or quote.get("turnover_rate")),
            amplitude=_to_float(quote.get("amplitude")),
            pe_ratio_ttm=_to_float(quote.get("peDynamic") or quote.get("pe") or quote.get("peTtm")),
            total_market_cap=total_market_cap,
            source=self.source_id,
            metadata={
                "market": symbol.market,
                "circulating_market_cap": circulating_market_cap,
            },
        )


def _normalize_name(value: object) -> Optional[str]:
    if value in (None, "", "-"):
        return None
    return str(value).strip() or None


def _to_float(value: Any) -> Optional[float]:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
