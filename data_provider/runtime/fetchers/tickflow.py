# -*- coding: utf-8 -*-
"""
TickFlow data source adapter.

TickFlow is optional and fail-open in this project. The fetcher supports
general A-share daily K-lines/realtime quotes, keeps the existing market review
capability, and exposes advanced TickFlow-only helpers for future consumers.

TickFlow 数据源适配器。TickFlow 在本项目中为可选且 fail-open；
该抓取器支持通用 A 股日线/实时报价，保留既有市场回顾能力，并暴露仅供 TickFlow 的高级辅助函数。
"""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from threading import RLock
from time import monotonic
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    import exchange_calendars as xcals
except ImportError:  # pragma: no cover - optional dependency in lightweight installs.
    xcals = None

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - defensive fallback for old runtimes.
    ZoneInfo = None  # type: ignore

from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.common.errors import DataFetchError
from src.domain.market.stock_codes import is_bse_code, is_kc_cy_stock, is_st_stock, normalize_stock_code
from data_provider.realtime.types import RealtimeSource, UnifiedRealtimeQuote, safe_int


from data_provider.kline.daily_tickflow_source import TickFlowDailySource
from data_provider.clients import tickflow as protocol
from data_provider.kline import daily_tickflow_source as daily_protocol
from data_provider.realtime import tickflow_source as realtime_protocol
from data_provider.kline.daily_tickflow_source import _MIN_DAILY_KLINE_COUNT
from data_provider.kline.daily_tickflow_source import _MAX_DAILY_KLINE_COUNT
from data_provider.kline.daily_tickflow_source import _DAILY_KLINE_COUNT_MULTIPLIER
from data_provider.kline.daily_tickflow_source import _DAILY_KLINE_COUNT_BUFFER
from data_provider.clients.tickflow import _SUPPORTED_KLINE_ADJUSTS


logger = logging.getLogger("data_provider.tickflow_fetcher")

_CN_MAIN_INDEX_QUOTES = (
    ("000001.SH", "000001", "\u4e0a\u8bc1\u6307\u6570"),
    ("399001.SZ", "399001", "\u6df1\u8bc1\u6210\u6307"),
    ("399006.SZ", "399006", "\u521b\u4e1a\u677f\u6307"),
    ("000688.SH", "000688", "\u79d1\u521b50"),
    ("000016.SH", "000016", "\u4e0a\u8bc150"),
    ("000300.SH", "000300", "\u6caa\u6df1300"),
)
_CN_UNIVERSE_ID = "CN_Equity_A"
_MAX_SYMBOLS_PER_QUOTE_REQUEST = 5
_CAPABILITY_NEGATIVE_CACHE_TTL_SECONDS = 900
_SECTOR_RANKINGS_CACHE_TTL_SECONDS = 300
_MAX_DAILY_PREFETCH_LOOKBACK_DAYS = 730


from data_provider.clients.tickflow import _parse_env_int


class TickFlowFetcher(BaseFetcher):
    """TickFlow-backed optional A-share fetcher."""

    name = "TickFlowFetcher"
    priority = 2

    def __init__(
        self,
        api_key: Optional[str],
        timeout: float = 30.0,
        *,
        kline_adjust: Optional[str] = None,
        batch_daily_enabled: Optional[bool] = None,
        batch_size: Optional[int] = None,
        priority: Optional[int] = None,
    ):
        """构造 TickFlow 抓取器：保存 api_key、超时、优先级与各类缓存/能力状态。"""
        self.api_key = (api_key or "").strip()
        self.timeout = timeout
        self.priority = self._normalize_priority(priority)
        self.kline_adjust = self._normalize_adjust(
            kline_adjust or os.getenv("TICKFLOW_KLINE_ADJUST", "none")
        )
        self.batch_daily_enabled = (
            self._parse_bool(os.getenv("TICKFLOW_BATCH_DAILY_ENABLED"), True)
            if batch_daily_enabled is None
            else bool(batch_daily_enabled)
        )
        self.batch_size = max(1, int(batch_size)) if batch_size is not None else _parse_env_int("TICKFLOW_BATCH_SIZE", 100)

        self._client = None
        self._client_lock = RLock()

        self._daily_cache: Dict[Tuple[str, str, str, str], pd.DataFrame] = {}
        self._daily_cache_lock = RLock()
        self._quote_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._quote_cache_lock = RLock()
        self._sector_rankings_cache: Optional[
            Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]
        ] = None
        self._sector_rankings_cache_lock = RLock()

        self._capability_lock = RLock()
        self._capability_supported: Dict[str, Optional[bool]] = {
            "batch_daily": None,
            "universe_quotes": None,
        }
        self._capability_checked_at: Dict[str, float] = {}

    def close(self) -> None:
        return self._shared_client_access().close()

    def __del__(self) -> None:
        """析构时尝试关闭底层客户端连接。"""
        try:
            self.close()
        except Exception:
            pass

    def _build_client(self):
        return self._shared_client_access()._build_client()

    def _get_client(self):
        return self._shared_client_access()._get_client()

    def _daily_history_source(self) -> TickFlowDailySource:
        """复用原有连接、凭证、缓存与错误处理入口。"""
        return TickFlowDailySource(
            to_tickflow_symbol=self._to_tickflow_symbol, daily_cache_key=self._daily_cache_key,
            get_daily_cache=self._get_daily_cache, get_client=self._get_client,
            daily_kline_count=self._daily_kline_count, date_to_ms=self._date_to_ms,
            adjust=lambda: self.kline_adjust, prepare_daily_frame=self._prepare_daily_frame,
            set_daily_cache=self._set_daily_cache, coerce_frame=self._coerce_frame,
            extract_date_series=self._extract_date_series, cn_lots_to_shares=self._cn_lots_to_shares,
            ratio_series_to_percent=self._ratio_series_to_percent
        )

    def _fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._daily_history_source().fetch_raw_data(stock_code, start_date, end_date)

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        return self._daily_history_source().normalize_data(df, stock_code)

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.safe_float(value)

    @staticmethod
    def _parse_bool(value: Optional[str], default: bool) -> bool:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.parse_bool(value, default)

    @staticmethod
    def _normalize_priority(value: Optional[int]) -> int:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.normalize_priority(value)

    @staticmethod
    def _normalize_adjust(value: Optional[str]) -> str:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.normalize_adjust(value)

    @classmethod
    def _ratio_to_percent(cls, value: Any) -> Optional[float]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.ratio_to_percent(value, use_safe_float=cls._safe_float)

    @classmethod
    def _ratio_series_to_percent(cls, series: pd.Series) -> pd.Series:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.ratio_series_to_percent(series)

    @classmethod
    def _cn_lots_to_shares(cls, lots: Any, default: Optional[int] = None) -> Any:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.cn_lots_to_shares(lots, default)

    @staticmethod
    def _extract_name(quote: Dict[str, Any]) -> str:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.extract_name(quote)

    @staticmethod
    def _is_permission_error(exc: Exception) -> bool:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.is_permission_error(exc)

    @classmethod
    def _is_universe_permission_error(cls, exc: Exception) -> bool:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.is_universe_permission_error(exc, use_is_permission_error=cls._is_permission_error)

    @staticmethod
    def _is_cn_equity_symbol(symbol: str) -> bool:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.is_cn_equity_symbol(symbol)

    @staticmethod
    def _round_limit_price(prev_close: float, ratio: float) -> float:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return realtime_protocol.round_limit_price(prev_close, ratio)

    @classmethod
    def _get_limit_ratio(cls, pure_code: str, name: str) -> float:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return realtime_protocol.get_limit_ratio(pure_code, name, is_bse=is_bse_code, is_kc_cy=is_kc_cy_stock, is_st=is_st_stock)

    @staticmethod
    def _coerce_frame(value: Any) -> pd.DataFrame:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.coerce_frame(value)

    @staticmethod
    def _exchange_from_code(stock_code: str) -> Optional[str]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.exchange_from_code(stock_code)

    @classmethod
    def _to_tickflow_symbol(cls, stock_code: str) -> Optional[str]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.to_tickflow_symbol(stock_code, use_exchange_from_code=cls._exchange_from_code)

    @staticmethod
    def _date_to_ms(date_str: str, *, end_of_day: bool = False) -> int:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return daily_protocol.date_to_ms(date_str, end_of_day=end_of_day, zone_info=ZoneInfo)

    @staticmethod
    def _extract_date_series(raw: pd.DataFrame) -> pd.Series:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return daily_protocol.extract_date_series(raw)

    @staticmethod
    def _daily_kline_count(start_date: str, end_date: str) -> int:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return daily_protocol.daily_kline_count(start_date, end_date)

    @classmethod
    def _prepare_daily_frame(
        cls,
        value: Any,
        *,
        symbol: str,
        start_date: str,
        end_date: str,
        count: int,
        context: str,
    ) -> pd.DataFrame:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return daily_protocol.prepare_daily_frame(value, symbol=symbol, start_date=start_date, end_date=end_date, count=count, context=context, use_coerce_frame=cls._coerce_frame, use_extract_date_series=cls._extract_date_series, use_is_daily_frame_truncated=cls._is_daily_frame_truncated)

    @classmethod
    def _is_daily_frame_truncated(
        cls,
        *,
        dates: pd.Series,
        start_date: str,
        end_date: str,
        count: int,
        returned_rows: int,
    ) -> bool:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return daily_protocol.is_daily_frame_truncated(dates=dates, start_date=start_date, end_date=end_date, count=count, returned_rows=returned_rows, use_first_trading_date_on_or_after=cls._first_trading_date_on_or_after)

    @staticmethod
    def _first_trading_date_on_or_after(start_date: datetime) -> datetime:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return daily_protocol.first_trading_date_on_or_after(start_date, calendars=xcals)

    def _daily_cache_key(
        self, symbol: str, start_date: str, end_date: str
    ) -> Tuple[str, str, str, str]:
        return self._shared_client_access()._daily_cache_key(symbol, start_date, end_date)

    def _get_daily_cache(
        self, cache_key: Tuple[str, str, str, str]
    ) -> Optional[pd.DataFrame]:
        return self._shared_client_access()._get_daily_cache(cache_key)

    def _set_daily_cache(
        self, cache_key: Tuple[str, str, str, str], df: pd.DataFrame
    ) -> None:
        return self._shared_client_access()._set_daily_cache(cache_key, df)

    def _capability_available(self, capability: str) -> bool:
        return self._shared_client_access()._capability_available(capability)

    def _mark_capability(self, capability: str, supported: bool) -> None:
        return self._shared_client_access()._mark_capability(capability, supported)

    def prefetch_daily_klines(
        self,
        stock_codes: Iterable[str],
        *,
        days: int = 30,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        return self._daily_prefetch().prefetch_daily_klines(
            stock_codes, days=days, start_date=start_date, end_date=end_date
        )

    @classmethod
    def _dedupe_symbols(cls, stock_codes: Iterable[str]) -> List[str]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return daily_protocol.dedupe_symbols(stock_codes, use_to_tickflow_symbol=cls._to_tickflow_symbol)

    @staticmethod
    def _iter_batch_frames(batch_result: Any) -> Iterable[Tuple[str, Any]]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return daily_protocol.iter_batch_frames(batch_result)

    def _realtime_source(self):
        """惰性加载实时实现；不提前构造新 SDK 或缓存。"""
        from data_provider.realtime.tickflow_source import TickflowRealtimeOperations

        return TickflowRealtimeOperations(
            dedupe_symbols=self._dedupe_symbols,
            get_client=self._get_client,
            store_quotes=self._store_quotes,
            get_cached_quote=self._get_cached_quote,
            get_realtime_cache_ttl=self._get_realtime_cache_ttl,
            convert_quote=self._quote_to_unified_quote,
            to_tickflow_symbol=self._to_tickflow_symbol,
            cn_lots_to_shares=self._cn_lots_to_shares,
            extract_name=self._extract_name,
            format_provider_timestamp=self._format_provider_timestamp,
            ratio_to_percent=self._ratio_to_percent,
            safe_float=self._safe_float,
            batch_size=lambda: self.batch_size,
        )

    def prefetch_realtime_quotes(
        self,
        stock_codes: Iterable[str],
        *,
        batch_size: Optional[int] = None,
    ) -> int:
        return self._realtime_source().prefetch_realtime_quotes(
            stock_codes, batch_size=batch_size
        )

    def _store_quotes(self, quotes: Any) -> int:
        return self._shared_client_access()._store_quotes(quotes)

    def _get_cached_quote(
        self, symbol: str, ttl_seconds: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        return self._shared_client_access()._get_cached_quote(symbol, ttl_seconds)

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_realtime_quote(stock_code)

    @staticmethod
    def _get_realtime_cache_ttl() -> int:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.get_realtime_cache_ttl()

    def _quote_to_unified_quote(
        self,
        stock_code: str,
        quote: Dict[str, Any],
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().quote_to_unified_quote(stock_code, quote)

    @staticmethod
    def _format_provider_timestamp(value: Any) -> Optional[str]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return realtime_protocol.format_provider_timestamp(value)

    def _stock_names(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.name_lookup import TickflowNameLookup

        return TickflowNameLookup(
            use_extract_instrument_name=lambda *args, **kwargs: self._extract_instrument_name(
                *args, **kwargs
            ),
            use_extract_name=lambda *args, **kwargs: self._extract_name(
                *args, **kwargs
            ),
            use_get_cached_quote=lambda *args, **kwargs: self._get_cached_quote(
                *args, **kwargs
            ),
            use_get_client=lambda *args, **kwargs: self._get_client(*args, **kwargs),
            use_store_quotes=lambda *args, **kwargs: self._store_quotes(
                *args, **kwargs
            ),
            use_to_tickflow_symbol=lambda *args, **kwargs: self._to_tickflow_symbol(
                *args, **kwargs
            ),
            log=lambda: logger,
        )

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        return self._stock_names().get_stock_name(stock_code)

    @staticmethod
    def _extract_instrument_name(instrument: Any) -> Optional[str]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.extract_instrument_name(instrument)

    def _stock_catalog(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.catalog import TickflowCatalog

        return TickflowCatalog(
            use_extract_universe_entries=lambda *args, **kwargs: self._extract_universe_entries(
                *args, **kwargs
            ),
            use_get_client=lambda *args, **kwargs: self._get_client(*args, **kwargs),
            use_is_cn_equity_symbol=lambda *args, **kwargs: self._is_cn_equity_symbol(
                *args, **kwargs
            ),
            use_is_universe_permission_error=lambda *args, **kwargs: self._is_universe_permission_error(
                *args, **kwargs
            ),
            call_normalize_stock_code=lambda *args, **kwargs: normalize_stock_code(
                *args, **kwargs
            ),
            current_cn_universe_id=lambda: _CN_UNIVERSE_ID,
            log=lambda: logger,
        )

    def get_stock_list(self) -> pd.DataFrame:
        return self._stock_catalog().get_stock_list()

    @staticmethod
    def _extract_universe_entries(universe: Any) -> List[Dict[str, str]]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.extract_universe_entries(universe)

    @staticmethod
    def _extract_universe_symbols(universe: Any) -> List[str]:
        """委托唯一协议/能力实现，保留原纯辅助覆盖点。"""
        return protocol.extract_universe_symbols(universe)

    def _market_index_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.indices import TickflowIndices

        return TickflowIndices(
            use_get_client=lambda *args, **kwargs: self._get_client(*args, **kwargs),
            use_ratio_to_percent=lambda *args, **kwargs: self._ratio_to_percent(
                *args, **kwargs
            ),
            use_safe_float=lambda *args, **kwargs: self._safe_float(*args, **kwargs),
            read_logger=lambda: logger,
            read_cn_main_index_quotes=lambda: _CN_MAIN_INDEX_QUOTES,
            read_max_symbols_per_quote_request=lambda: _MAX_SYMBOLS_PER_QUOTE_REQUEST,
        )

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_main_indices(region)

    def _market_statistics_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.statistics import TickflowStatistics

        return TickflowStatistics(
            use_capability_available=lambda *args, **kwargs: self._capability_available(
                *args, **kwargs
            ),
            use_extract_name=lambda *args, **kwargs: self._extract_name(
                *args, **kwargs
            ),
            use_get_client=lambda *args, **kwargs: self._get_client(*args, **kwargs),
            use_get_limit_ratio=lambda *args, **kwargs: self._get_limit_ratio(
                *args, **kwargs
            ),
            use_is_cn_equity_symbol=lambda *args, **kwargs: self._is_cn_equity_symbol(
                *args, **kwargs
            ),
            use_is_universe_permission_error=lambda *args, **kwargs: self._is_universe_permission_error(
                *args, **kwargs
            ),
            use_mark_capability=lambda *args, **kwargs: self._mark_capability(
                *args, **kwargs
            ),
            use_round_limit_price=lambda *args, **kwargs: self._round_limit_price(
                *args, **kwargs
            ),
            use_safe_float=lambda *args, **kwargs: self._safe_float(*args, **kwargs),
            call_normalize_stock_code=lambda *args, **kwargs: normalize_stock_code(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
            read_math=lambda: math,
            read_cn_universe_id=lambda: _CN_UNIVERSE_ID,
        )

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        return self._market_statistics_source().get_market_stats()

    def _sector_source(self):
        """按需加载能力实现，保留原缓存/SDK/诊断与动态替换入口。"""
        from data_provider.sector.tickflow_source import TickflowSectorOperations

        return TickflowSectorOperations(
            use_capability_available=lambda *args, **kwargs: self._capability_available(
                *args, **kwargs
            ),
            use_extract_universe_symbols=lambda *args, **kwargs: self._extract_universe_symbols(
                *args, **kwargs
            ),
            use_get_client=lambda *args, **kwargs: self._get_client(*args, **kwargs),
            use_is_universe_permission_error=lambda *args, **kwargs: self._is_universe_permission_error(
                *args, **kwargs
            ),
            use_mark_capability=lambda *args, **kwargs: self._mark_capability(
                *args, **kwargs
            ),
            use_ratio_to_percent=lambda *args, **kwargs: self._ratio_to_percent(
                *args, **kwargs
            ),
            use_safe_float=lambda *args, **kwargs: self._safe_float(*args, **kwargs),
            current_sector_rankings_cache=lambda: self._sector_rankings_cache,
            current_sector_rankings_cache_lock=lambda: self._sector_rankings_cache_lock,
            set_sector_rankings_cache=lambda value: setattr(
                self, "_sector_rankings_cache", value
            ),
            call_monotonic=lambda *args, **kwargs: monotonic(*args, **kwargs),
            read_logger=lambda: logger,
            read_cn_universe_id=lambda: _CN_UNIVERSE_ID,
            read_sector_rankings_cache_ttl_seconds=lambda: _SECTOR_RANKINGS_CACHE_TTL_SECONDS,
        )

    def get_sector_rankings(
        self, n: int = 5
    ) -> Optional[Tuple[List[Dict], List[Dict]]]:
        return self._sector_source().get_sector_rankings(n)

    def _daily_prefetch(self):
        """接线唯一能力实现，沿用原资源和方法扩展点。"""
        from data_provider.kline.daily_tickflow_source import TickFlowDailyPrefetch

        return TickFlowDailyPrefetch(
            use_capability_available=lambda *args, **kwargs: self._capability_available(
                *args, **kwargs
            ),
            use_daily_cache_key=lambda *args, **kwargs: self._daily_cache_key(
                *args, **kwargs
            ),
            use_daily_kline_count=lambda *args, **kwargs: self._daily_kline_count(
                *args, **kwargs
            ),
            use_date_to_ms=lambda *args, **kwargs: self._date_to_ms(*args, **kwargs),
            use_dedupe_symbols=lambda *args, **kwargs: self._dedupe_symbols(
                *args, **kwargs
            ),
            use_get_client=lambda *args, **kwargs: self._get_client(*args, **kwargs),
            use_is_permission_error=lambda *args, **kwargs: self._is_permission_error(
                *args, **kwargs
            ),
            use_iter_batch_frames=lambda *args, **kwargs: self._iter_batch_frames(
                *args, **kwargs
            ),
            use_mark_capability=lambda *args, **kwargs: self._mark_capability(
                *args, **kwargs
            ),
            use_prepare_daily_frame=lambda *args, **kwargs: self._prepare_daily_frame(
                *args, **kwargs
            ),
            use_set_daily_cache=lambda *args, **kwargs: self._set_daily_cache(
                *args, **kwargs
            ),
            read_batch_daily_enabled=lambda: self.batch_daily_enabled,
            read_batch_size=lambda: self.batch_size,
            read_kline_adjust=lambda: self.kline_adjust,
            read_global_logger=lambda: logger,
            read_global_datetime=lambda: datetime,
            read_global_timedelta=lambda: timedelta,
            read_global_MAX_DAILY_PREFETCH_LOOKBACK_DAYS=lambda: _MAX_DAILY_PREFETCH_LOOKBACK_DAYS,
        )

    def _shared_client_access(self):
        """接线共享协议；显式复用原资源，不传递整个宿主。"""
        from data_provider.clients.tickflow import TickflowClientAccess

        return TickflowClientAccess(
            use_build_client=lambda *args, **kwargs: self._build_client(*args, **kwargs),
            use_coerce_frame=lambda *args, **kwargs: self._coerce_frame(*args, **kwargs),
            read_capability_checked_at=lambda: self._capability_checked_at,
            read_capability_lock=lambda: self._capability_lock,
            read_capability_supported=lambda: self._capability_supported,
            read_client=lambda: self._client,
            read_client_lock=lambda: self._client_lock,
            read_daily_cache=lambda: self._daily_cache,
            read_daily_cache_lock=lambda: self._daily_cache_lock,
            read_quote_cache=lambda: self._quote_cache,
            read_quote_cache_lock=lambda: self._quote_cache_lock,
            read_api_key=lambda: self.api_key,
            read_kline_adjust=lambda: self.kline_adjust,
            read_timeout=lambda: self.timeout,
            write_client=lambda value: setattr(self, "_client", value),
            read_global_CAPABILITY_NEGATIVE_CACHE_TTL_SECONDS=lambda: _CAPABILITY_NEGATIVE_CACHE_TTL_SECONDS,
            read_global_logger=lambda: logger,
            read_global_monotonic=lambda: monotonic,
        )
