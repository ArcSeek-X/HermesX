# -*- coding: utf-8 -*-
"""
@file: tickflow_source.py
@description: 实时行情 tickflow source，复用既有 TickFlowFetcher 实时行情通道。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations
from typing import Optional
from data_provider.realtime.source_contract import RealtimeSource
from data_provider.realtime.types import UnifiedRealtimeQuote
from src.config import get_config
from dataclasses import dataclass
import logging
import math
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List
from src.domain.market.stock_codes import normalize_stock_code
from data_provider.realtime.types import RealtimeSource as QuoteSource


class TickflowRealtimeSource(RealtimeSource):
    """复用 TickFlowFetcher 的实时行情 source。"""

    source_id = "tickflow"

    def __init__(self) -> None:
        """构造实时行情数据源（TickFlow）。"""
        from data_provider.runtime.fetchers.tickflow import TickFlowFetcher

        config = get_config()
        self.fetcher = (
            TickFlowFetcher(
                config.tickflow_api_key,
                kline_adjust=config.tickflow_kline_adjust,
                batch_daily_enabled=config.tickflow_batch_daily_enabled,
                batch_size=config.tickflow_batch_size,
                priority=config.tickflow_priority,
            )
            if config.tickflow_api_key
            else None
        )

    def is_available(self) -> bool:
        """仅在配置 TickFlow API Key 时参与选源。"""
        return self.fetcher is not None

    def fetch(self, request: str) -> Optional[UnifiedRealtimeQuote]:
        """通过既有 TickFlowFetcher 获取实时行情。"""
        if self.fetcher is None:
            return None
        return self.fetcher.get_realtime_quote(request)


# 旧 Fetcher 与能力 Source 共用下述唯一取数实现；资源仍由原宿主持有。

logger = logging.getLogger("data_provider.tickflow_fetcher")


@dataclass(frozen=True)
class TickflowRealtimeOperations:
    """只绑定实时所需回调，复用日线/预取/名称查询的客户端和缓存。"""

    dedupe_symbols: Callable[[Iterable[str]], List[str]]
    get_client: Callable[[], Any]
    store_quotes: Callable[[Any], int]
    get_cached_quote: Callable[..., Optional[Dict[str, Any]]]
    get_realtime_cache_ttl: Callable[[], int]
    convert_quote: Callable[..., Optional[UnifiedRealtimeQuote]]
    to_tickflow_symbol: Callable[[str], Optional[str]]
    cn_lots_to_shares: Callable[..., Any]
    extract_name: Callable[[Dict[str, Any]], str]
    format_provider_timestamp: Callable[[Any], Optional[str]]
    ratio_to_percent: Callable[..., Optional[float]]
    safe_float: Callable[..., Optional[float]]
    batch_size: Callable[[], int]

    def prefetch_realtime_quotes(
        self,
        stock_codes: Iterable[str],
        *,
        batch_size: Optional[int] = None,
    ) -> int:
        """Batch-prefetch realtime quotes into the quote cache."""
        client = self.get_client()
        if client is None:
            return 0

        symbols = self.dedupe_symbols(stock_codes)
        if not symbols:
            return 0

        effective_batch_size = max(1, int(batch_size or self.batch_size()))
        cached_count = 0
        for offset in range(0, len(symbols), effective_batch_size):
            batch_symbols = symbols[offset : offset + effective_batch_size]
            try:
                quotes = client.quotes.get(symbols=batch_symbols)
            except Exception as exc:
                logger.warning("[TickFlowFetcher] batch realtime quote failed: %s", exc)
                continue
            cached_count += self.store_quotes(quotes)
        return cached_count

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """获取单只股票实时报价并转为统一结构。"""
        symbol = self.to_tickflow_symbol(stock_code)
        if not symbol:
            return None

        quote_ttl = self.get_realtime_cache_ttl()
        quote = self.get_cached_quote(symbol, quote_ttl)
        if quote is None:
            client = self.get_client()
            if client is None:
                return None
            try:
                quotes = client.quotes.get(symbols=[symbol])
            except Exception as exc:
                logger.warning(
                    "[TickFlowFetcher] realtime quote failed for %s: %s", symbol, exc
                )
                return None
            self.store_quotes(quotes)
            quote = self.get_cached_quote(symbol, quote_ttl)

        if not quote:
            return None
        return self.convert_quote(stock_code, quote)

    def quote_to_unified_quote(
        self,
        stock_code: str,
        quote: Dict[str, Any],
    ) -> Optional[UnifiedRealtimeQuote]:
        """将 TickFlow 报价归一为统一行情结构。"""
        symbol = str(
            quote.get("symbol") or self.to_tickflow_symbol(stock_code) or ""
        ).upper()
        code = normalize_stock_code(stock_code or symbol)
        current = self.safe_float(quote.get("last_price"))
        if current is None:
            current = self.safe_float(quote.get("price"))
        if current is None:
            return None

        ext = quote.get("ext") or {}
        prev_close = self.safe_float(quote.get("prev_close"))
        open_price = self.safe_float(quote.get("open"))
        high = self.safe_float(quote.get("high"))
        low = self.safe_float(quote.get("low"))
        volume = self.cn_lots_to_shares(quote.get("volume"), default=0)
        amount = self.safe_float(quote.get("amount")) or 0.0
        change_amount = self.safe_float(ext.get("change_amount"))
        if change_amount is None and prev_close is not None:
            change_amount = current - prev_close

        change_pct = self.ratio_to_percent(ext.get("change_pct"))
        if change_pct is None and prev_close and prev_close > 0:
            change_pct = (current - prev_close) / prev_close * 100.0

        timestamp = quote.get("timestamp") or quote.get("time") or quote.get("ts")
        provider_timestamp = self.format_provider_timestamp(timestamp)

        return UnifiedRealtimeQuote(
            code=code,
            name=self.extract_name(quote),
            price=current,
            change_pct=change_pct,
            change_amount=change_amount,
            volume=volume,
            amount=amount,
            open_price=open_price,
            high=high,
            low=low,
            pre_close=prev_close,
            source=QuoteSource.TICKFLOW,
            provider_timestamp=provider_timestamp,
            turnover_rate=self.ratio_to_percent(ext.get("turnover_rate")),
            amplitude=self.ratio_to_percent(ext.get("amplitude")),
        )


def round_limit_price(prev_close: float, ratio: float) -> float:
    """按涨跌停比例对昨收价做向下取整的限价。"""
    return math.floor(prev_close * (1 + ratio) * 100 + 0.5) / 100.0



def get_limit_ratio(pure_code: str, name: str, *, is_bse, is_kc_cy, is_st) -> float:
    """按市场（主板/创业板/北交所）返回涨跌停比例。"""
    if is_bse(pure_code):
        return 0.30
    if is_kc_cy(pure_code):
        return 0.20
    if is_st(name):
        return 0.05
    return 0.10



def format_provider_timestamp(value: Any) -> Optional[str]:
    """将 TickFlow 时间戳格式化为标准字符串。"""
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric <= 0:
        return None
    if numeric > 10_000_000_000:
        numeric = numeric / 1000.0
    return datetime.fromtimestamp(numeric, timezone.utc).isoformat()
