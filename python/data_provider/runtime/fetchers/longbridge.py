# -*- coding: utf-8 -*-
"""
===================================
LongbridgeFetcher - 长桥兜底数据源 (Priority 5)
===================================

数据来源：长桥 OpenAPI (https://open.longbridge.com)
特点：覆盖美股 + 港股，可计算量比/换手率/PE 等 yfinance 缺失字段
定位：美股/港股最后兜底数据源

关键策略：
1. 组合 quote + static_info 接口计算 turnover_rate / pe_ratio / total_mv
2. 通过 history_candlesticks 计算 volume_ratio（近5日均量比）
3. 懒加载 QuoteContext，首次调用时才建立连接
4. static_info 进程内短缓存，减少重复请求（默认 24h，可调；见 LONGBRIDGE_STATIC_INFO_TTL_SECONDS）

凭证：优先使用 `LONGBRIDGE_OAUTH_CLIENT_ID` + SDK token 缓存（OAuth 2.0）；
Legacy API Key 三件套（`LONGBRIDGE_APP_KEY` / `LONGBRIDGE_APP_SECRET` / `LONGBRIDGE_ACCESS_TOKEN`）仍兼容。
可选：`LONGBRIDGE_STATIC_INFO_TTL_SECONDS`；SDK `language` 取自 `REPORT_LANGUAGE`，`log_path` 为 `{LOG_DIR}/longbridge_sdk.log`；
`LONGBRIDGE_HTTP_URL` / `LONGBRIDGE_QUOTE_WS_URL` / `LONGBRIDGE_TRADE_WS_URL` / `LONGBRIDGE_REGION` （见官方文档默认值）。
"""

import base64
import binascii
import json
import logging
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.realtime.types import UnifiedRealtimeQuote, RealtimeSource, safe_float
from src.domain.market.us_index_symbols import is_us_stock_code, is_us_index_code

from data_provider.kline.daily_longbridge_source import LongbridgeDailySource
from data_provider.clients import longbridge as protocol
from data_provider.clients.longbridge import (
    _DEFAULT_STATIC_INFO_TTL,
    _DEFAULT_CONNECTION_COOLDOWN_SECONDS,
    _static_info_ttl_seconds,
    _connection_cooldown_seconds,
    _REGION_URL_MAP,
    _sanitize_longbridge_env,
    _longbridge_config_kwargs,
    _clean_optional,
    _oauth_token_cache_path,
    _restore_oauth_token_cache_from_env,
    _is_valid_oauth_cache_file,
    _oauth_reauth_not_supported,
    _oauth_sdk_unavailable_error,
    _longbridge_credentials,
    _has_legacy_credentials,
    _has_oauth_credentials,
    _is_us_code,
    _is_hk_code,
    _to_longbridge_symbol,
)


logger = logging.getLogger("data_provider.longbridge_fetcher")





































class LongbridgeFetcher(BaseFetcher):
    """
    长桥 OpenAPI 数据源实现

    优先级: 5（最低，作为美股/港股最后兜底）
    数据来源: Longbridge OpenAPI

    通过组合多个 API 计算 yfinance 缺失的指标:
    - turnover_rate = volume / circulating_shares * 100
    - volume_ratio = today_volume / avg_5day_volume
    - pe_ratio = price / eps_ttm
    """

    name = "LongbridgeFetcher"
    priority = int(os.getenv("LONGBRIDGE_PRIORITY", "5"))

    _CONNECTION_ERRORS = ("client is closed", "context closed", "connection closed")

    def __init__(self):
        """构造长桥行情抓取器并装配依赖。"""
        self._ctx = None
        self._config = None
        self._ctx_lock = threading.Lock()
        self._available = None
        self._cooldown_until = 0.0
        # {symbol: (StaticInfo, timestamp)}
        self._static_cache: Dict[str, Any] = {}
        self._static_cache_lock = threading.Lock()

    def _is_connection_error(self, exc: Exception) -> bool:
        """判断是否为连接类错误。"""
        msg = str(exc).lower()
        return any(s in msg for s in self._CONNECTION_ERRORS)

    def _invalidate_ctx(self):
        return self._shared_client_access()._invalidate_ctx()

    def _mark_connection_cooldown(self, exc: Exception) -> None:
        return self._shared_client_access()._mark_connection_cooldown(exc)

    def is_available_for_request(self, capability: str = "") -> bool:
        return self._shared_client_access().is_available_for_request(capability)

    def _is_available(self) -> bool:
        return self._shared_client_access()._is_available()

    @staticmethod
    def has_configured_credentials(config: Any = None) -> bool:
        """Return True when runtime config can attempt Longbridge auth."""
        creds = _longbridge_credentials(config)
        return _has_legacy_credentials(creds) or _has_oauth_credentials(creds)

    def _get_ctx(self):
        return self._shared_client_access()._get_ctx()

    # ------------------------------------------------------------------
    # static_info with cache
    # ------------------------------------------------------------------

    def _get_static_info(self, symbol: str) -> Optional[Any]:
        return self._shared_client_access()._get_static_info(symbol)

    # ------------------------------------------------------------------
    # get_stock_name via static_info
    # ------------------------------------------------------------------

    def _stock_names(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.name_lookup import LongbridgeNameLookup

        return LongbridgeNameLookup(
            use_get_static_info=lambda *args, **kwargs: self._get_static_info(
                *args, **kwargs
            ),
            call_to_longbridge_symbol=lambda *args, **kwargs: _to_longbridge_symbol(
                *args, **kwargs
            ),
            log=lambda: logger,
        )

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        return self._stock_names().get_stock_name(stock_code)

    # ------------------------------------------------------------------
    # volume_ratio from history
    # ------------------------------------------------------------------

    def _ts_sort_key(self, candle: Any) -> float:
        """Monotonic sort key for a candle timestamp (UTC seconds or datetime)."""
        ts = getattr(candle, "timestamp", None)
        if ts is None:
            return 0.0
        if hasattr(ts, "timestamp"):
            return float(ts.timestamp())
        return float(int(ts))

    def _compute_volume_ratio(self, symbol: str, today_volume: int) -> Optional[float]:
        """Compute volume_ratio = today_volume / avg(recent completed daily volumes).

        Uses the most recent daily bar as \"today/incomplete\" reference window: average
        volume of the next 5 older daily bars. Avoids local `date.today()` matching, which
        breaks for US symbols when the shell runs in CN timezone.
        """
        if not today_volume or today_volume <= 0:
            return None
        ctx = self._get_ctx()
        if ctx is None:
            return None
        try:
            from longbridge.openapi import Period, AdjustType

            candles = ctx.history_candlesticks_by_offset(
                symbol,
                Period.Day,
                AdjustType.NoAdjust,
                False,
                6,
                datetime.now(),
            )
            if not candles or len(candles) < 2:
                return None

            ordered = sorted(candles, key=self._ts_sort_key, reverse=True)
            past_vols: list = []
            for c in ordered[1:6]:
                vol = int(getattr(c, "volume", 0) or 0)
                if vol > 0:
                    past_vols.append(vol)

            if not past_vols:
                return None

            avg_vol = sum(past_vols) / len(past_vols)
            if avg_vol <= 0:
                return None

            return round(today_volume / avg_vol, 2)
        except Exception as e:
            logger.debug(f"[Longbridge] 计算量比失败({symbol}): {e}")
            return None

    # ------------------------------------------------------------------
    # get_realtime_quote
    # ------------------------------------------------------------------

    def _realtime_source(self):
        """复用原实例及模块的实时资源、旧替换入口和降级路径。"""
        from data_provider.realtime.longbridge_source import (
            LongbridgeRealtimeOperations,
        )

        return LongbridgeRealtimeOperations(
            use_compute_volume_ratio=self._compute_volume_ratio,
            use_get_ctx=self._get_ctx,
            use_get_static_info=self._get_static_info,
            use_is_connection_error=self._is_connection_error,
            use_mark_connection_cooldown=self._mark_connection_cooldown,
            use_is_available_for_request=self.is_available_for_request,
            call_to_longbridge_symbol=lambda *args, **kwargs: _to_longbridge_symbol(
                *args, **kwargs
            ),
            call_safe_float=lambda *args, **kwargs: safe_float(*args, **kwargs),
        )

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_realtime_quote(stock_code)

    # ------------------------------------------------------------------
    # BaseFetcher abstract methods (historical daily data)
    # ------------------------------------------------------------------

    def _daily_history_source(self) -> LongbridgeDailySource:
        """复用原有连接、凭证、缓存与错误处理入口。"""
        return LongbridgeDailySource(
            available=self.is_available_for_request, get_context=self._get_ctx,
            connection_error=self._is_connection_error, cooldown=self._mark_connection_cooldown,
            symbol=_to_longbridge_symbol, to_float=safe_float
        )

    def _fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._daily_history_source().fetch_raw_data(stock_code, start_date, end_date)

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        return self._daily_history_source().normalize_data(df, stock_code)

    def _shared_client_access(self):
        """接线共享协议；显式复用原资源，不传递整个宿主。"""
        from data_provider.clients.longbridge import LongbridgeClientAccess

        return LongbridgeClientAccess(
            use_get_ctx=lambda *args, **kwargs: self._get_ctx(*args, **kwargs),
            use_invalidate_ctx=lambda *args, **kwargs: self._invalidate_ctx(
                *args, **kwargs
            ),
            use_is_available=lambda *args, **kwargs: self._is_available(*args, **kwargs),
            use_is_connection_error=lambda *args, **kwargs: self._is_connection_error(
                *args, **kwargs
            ),
            use_mark_connection_cooldown=lambda *args, **kwargs: self._mark_connection_cooldown(
                *args, **kwargs
            ),
            read_available=lambda: self._available,
            read_config=lambda: self._config,
            read_cooldown_until=lambda: self._cooldown_until,
            read_ctx=lambda: self._ctx,
            read_ctx_lock=lambda: self._ctx_lock,
            read_static_cache=lambda: self._static_cache,
            read_static_cache_lock=lambda: self._static_cache_lock,
            write_available=lambda value: setattr(self, "_available", value),
            write_config=lambda value: setattr(self, "_config", value),
            write_cooldown_until=lambda value: setattr(self, "_cooldown_until", value),
            write_ctx=lambda value: setattr(self, "_ctx", value),
            read_global_Optional=lambda: Optional,
            read_global_connection_cooldown_seconds=lambda: protocol._connection_cooldown_seconds,
            read_global_has_legacy_credentials=lambda: protocol._has_legacy_credentials,
            read_global_has_oauth_credentials=lambda: protocol._has_oauth_credentials,
            read_global_is_valid_oauth_cache_file=lambda: protocol._is_valid_oauth_cache_file,
            read_global_longbridge_config_kwargs=lambda: protocol._longbridge_config_kwargs,
            read_global_longbridge_credentials=lambda: protocol._longbridge_credentials,
            read_global_oauth_reauth_not_supported=lambda: protocol._oauth_reauth_not_supported,
            read_global_oauth_sdk_unavailable_error=lambda: protocol._oauth_sdk_unavailable_error,
            read_global_oauth_token_cache_path=lambda: protocol._oauth_token_cache_path,
            read_global_restore_oauth_token_cache_from_env=lambda: protocol._restore_oauth_token_cache_from_env,
            read_global_sanitize_longbridge_env=lambda: protocol._sanitize_longbridge_env,
            read_global_static_info_ttl_seconds=lambda: protocol._static_info_ttl_seconds,
            read_global_logger=lambda: logger,
            read_global_os=lambda: os,
            read_global_time=lambda: time,
        )
