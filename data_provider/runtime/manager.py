# -*- coding: utf-8 -*-
"""
===================================
数据源基类与管理器
===================================

设计模式：策略模式 (Strategy Pattern)
- BaseFetcher: 抽象基类，定义统一接口
- DataFetcherManager: 策略管理器，实现自动切换

防封禁策略：
1. 每个 Fetcher 内置流控逻辑
2. 失败自动切换到下一个数据源
3. 指数退避重试机制
"""

import logging
import time
from threading import BoundedSemaphore, RLock, Thread
from datetime import datetime, timezone
from typing import Callable, Optional, List, Tuple, Dict, Any

import pandas as pd
import numpy as np
from src.data.stock_index_loader import get_index_stock_name
from src.data.stock_mapping import STOCK_NAME_MAP, is_meaningful_stock_name
from src.domain.market.market_symbol_utils import is_suffix_market_symbol
from data_provider.common.diagnostics import record_provider_run, record_provider_run_started
from src.domain.market.stock_codes import (  # noqa: F401  re-export: keep legacy `from data_provider.base import ...` surface
    canonical_stock_code,
    is_bse_code,
    normalize_stock_code,
)
from data_provider.fundamentals.akshare_source import AkshareFundamentalAdapter
from data_provider.fundamentals.yfinance_source import YfinanceFundamentalAdapter
from data_provider.common.health import CircuitBreaker

# 旧公开入口保持同一对象，现有调用方无需一次性切换。
from data_provider.common.errors import (  # noqa: F401
    DataFetchError,
    RateLimitError,
    DataSourceUnavailableError,
    unwrap_exception,
    summarize_exception,
)
from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS  # noqa: F401
from data_provider.kline.daily_history import (
    DailyHistoryOperations,
    DailyHistoryRequest,
    fetch_daily_history,
)

from data_provider.realtime.enrichment import (
    utc_now_iso, parse_realtime_timestamp, realtime_fetcher_token,
    enrich_realtime_quote, quote_needs_supplement, merge_quote_fields, supplement_quote,
)
from data_provider.realtime.prefetch import prefetch_realtime_quotes

from data_provider.fundamentals import aggregate as fundamental_format
from data_provider.sector import coordination as board_format
from data_provider.common import normalize as value_format

from data_provider.chip.base import _coerce_chip_metric, _is_meaningful_chip_distribution  # noqa: F401

# 配置日志
logger = logging.getLogger("data_provider.base")




from data_provider.common.symbols import _is_us_market


from data_provider.common.symbols import _is_hk_market


from data_provider.common.symbols import _is_jp_market


from data_provider.common.symbols import _is_kr_market


from data_provider.common.symbols import _is_tw_market


from src.domain.market.stock_codes import is_a_share_etf_code as _is_etf_code




from data_provider.common.symbols import _market_tag


from src.domain.market.stock_codes import is_st_stock

from src.domain.market.stock_codes import is_kc_cy_stock


class DataFetcherManager:
    """
    数据源策略管理器

    职责：
    1. 管理多个数据源（按优先级排序）
    2. 自动故障切换（Failover）
    3. 提供统一的数据获取接口

    切换策略：
    - 优先使用高优先级数据源
    - 失败后自动切换到下一个
    - 所有数据源都失败时抛出异常
    """

    _DAILY_MARKET_FETCHER_SUPPORT = {
        "EfinanceFetcher": {"cn"},
        "TencentFetcher": {"cn"},
        "AkshareFetcher": {"cn", "hk"},
        "TushareFetcher": {"cn", "hk"},
        "TickFlowFetcher": {"cn"},
        "PytdxFetcher": {"cn"},
        "BaostockFetcher": {"cn"},
        "YfinanceFetcher": {"cn", "hk", "us", "jp", "kr", "tw"},
        "LongbridgeFetcher": {"hk", "us"},
        "FinnhubFetcher": {"us"},
        "AlphaVantageFetcher": {"us"},
    }
    _daily_source_health = CircuitBreaker(failure_threshold=3, cooldown_seconds=300.0)
    _CONCEPT_RANKINGS_CACHE_TTL_SECONDS = 300.0
    _CONCEPT_RANKINGS_EMPTY_CACHE_TTL_SECONDS = 30.0
    _concept_rankings_cache_lock = RLock()
    _concept_rankings_cache: Dict[int, Tuple[float, List[Dict], List[Dict]]] = {}

    def __init__(self, fetchers: Optional[List[BaseFetcher]] = None):
        """
        初始化管理器

        Args:
            fetchers: 数据源列表（可选，默认按优先级自动创建）
        """
        self._fetchers: List[BaseFetcher] = []
        self._fetchers_lock = RLock()
        self._fetchers_by_name: Dict[str, BaseFetcher] = {}
        self._fetcher_call_locks: Dict[int, RLock] = {}
        self._fetcher_call_locks_lock = RLock()
        self._stock_name_cache: Dict[str, str] = {}
        self._stock_name_cache_lock = RLock()

        if fetchers:
            # 按优先级排序
            self._fetchers = sorted(fetchers, key=lambda f: f.priority)
            self._refresh_fetcher_indexes_locked()
        else:
            # 默认数据源将在首次使用时延迟加载
            self._init_default_fetchers()
        self._fundamental_adapter = AkshareFundamentalAdapter()
        self._yfinance_fundamental_adapter = YfinanceFundamentalAdapter()
        self._tickflow_fetcher = None
        self._tickflow_api_key: Optional[str] = None
        self._tickflow_lock = RLock()
        self._fundamental_cache: Dict[str, Dict[str, Any]] = {}
        self._fundamental_cache_lock = RLock()
        self._fundamental_timeout_worker_limit = 8
        self._fundamental_timeout_slots = BoundedSemaphore(self._fundamental_timeout_worker_limit)
        self._sector_manager = None
        self._sector_manager_lock = RLock()
        self._tw_institutional_source = None
        self._tw_institutional_source_lock = RLock()

    def _ensure_concurrency_guards(self) -> None:
        """Lazily initialize thread-safety primitives for test scaffolds using __new__."""
        if not hasattr(self, "_fetchers_lock") or self._fetchers_lock is None:
            self._fetchers_lock = RLock()
        if not hasattr(self, "_fetchers_by_name") or self._fetchers_by_name is None:
            self._fetchers_by_name = {}
        if not hasattr(self, "_fetcher_call_locks") or self._fetcher_call_locks is None:
            self._fetcher_call_locks = {}
        if not hasattr(self, "_fetcher_call_locks_lock") or self._fetcher_call_locks_lock is None:
            self._fetcher_call_locks_lock = RLock()
        if not hasattr(self, "_stock_name_cache") or self._stock_name_cache is None:
            self._stock_name_cache = {}
        if not hasattr(self, "_stock_name_cache_lock") or self._stock_name_cache_lock is None:
            self._stock_name_cache_lock = RLock()

    def _get_fetchers_snapshot(self) -> List[BaseFetcher]:
        """返回当前抓取器列表快照。"""
        self._ensure_concurrency_guards()
        with self._fetchers_lock:
            return list(getattr(self, "_fetchers", []))

    def _get_sector_manager(self):
        """懒加载 ADR `data_provider/sector` 能力入口。"""
        if self._sector_manager is not None:
            return self._sector_manager
        with self._sector_manager_lock:
            if self._sector_manager is None:
                from data_provider.sector.base import SectorDataSourceManager
                from data_provider.sector.eastmoney_source import EastMoneySectorSource

                self._sector_manager = SectorDataSourceManager(
                    sources={"eastmoney": EastMoneySectorSource()},
                    default_source_order=("eastmoney",),
                    data_source_key="sector_data_source",
                    source_priority_key="sector_source_priority",
                    fallback_enabled_key="sector_fallback_enabled",
                    cache_ttl_seconds=300,
                    health_cooldown_seconds=10,
                )
        return self._sector_manager

    def _get_tw_institutional_source(self):
        """懒加载 ADR `data_provider/institutional` 台股机构 source。"""
        if self._tw_institutional_source is not None:
            return self._tw_institutional_source
        with self._tw_institutional_source_lock:
            if self._tw_institutional_source is None:
                from data_provider.institutional.tw_source import TwInstitutionalSource

                self._tw_institutional_source = TwInstitutionalSource()
        return self._tw_institutional_source

    def _refresh_fetcher_indexes_locked(self) -> None:
        """持锁状态下刷新抓取器索引。"""
        self._fetchers_by_name = {fetcher.name: fetcher for fetcher in self._fetchers}

    def _get_fetcher_by_name(self, fetcher_name: str, capability: str = "") -> Optional[BaseFetcher]:
        """按名称获取抓取器实例。"""
        self._ensure_concurrency_guards()
        with self._fetchers_lock:
            fetcher = self._fetchers_by_name.get(fetcher_name)
            if fetcher is None and self._fetchers:
                self._refresh_fetcher_indexes_locked()
                fetcher = self._fetchers_by_name.get(fetcher_name)
        if fetcher is None:
            return None
        if not self._is_fetcher_available(fetcher, capability=capability):
            return None
        return fetcher

    @staticmethod
    def _call_availability_probe(fetcher: BaseFetcher, probe_name: str, capability: str) -> Optional[bool]:
        """调用抓取器可用性探测。"""
        probe = getattr(fetcher, probe_name, None)
        if not callable(probe):
            return None
        try:
            if probe_name == "is_available_for_request":
                return bool(probe(capability))
            return bool(probe())
        except TypeError:
            return bool(probe())
        except Exception as exc:
            logger.debug(
                "[数据源可用性] %s.%s 检查失败(capability=%s): %s",
                fetcher.name,
                probe_name,
                capability or "default",
                exc,
            )
            return False

    @classmethod
    def _is_fetcher_available(cls, fetcher: BaseFetcher, capability: str = "") -> bool:
        """判断抓取器当前是否可用。"""
        for probe_name in ("is_available_for_request", "is_available", "_is_available"):
            result = cls._call_availability_probe(fetcher, probe_name, capability)
            if result is not None:
                return result
        return True

    def _get_fetcher_call_lock(self, fetcher: BaseFetcher) -> RLock:
        """返回指定抓取器的调用锁。"""
        self._ensure_concurrency_guards()
        fetcher_id = id(fetcher)
        with self._fetcher_call_locks_lock:
            lock = self._fetcher_call_locks.get(fetcher_id)
            if lock is None:
                lock = RLock()
                self._fetcher_call_locks[fetcher_id] = lock
            return lock

    def _call_fetcher_method(self, fetcher: BaseFetcher, method_name: str, *args, **kwargs):
        """Serialize shared fetcher state access through manager-owned per-instance locks."""
        method = getattr(fetcher, method_name)
        with self._get_fetcher_call_lock(fetcher):
            return method(*args, **kwargs)

    @classmethod
    def _filter_daily_fetchers_for_market(
        cls,
        fetchers: List[BaseFetcher],
        market: str,
    ) -> List[BaseFetcher]:
        """Skip built-in daily fetchers that are known not to support a market."""

        kept: List[BaseFetcher] = []
        skipped: List[str] = []
        for fetcher in fetchers:
            supported = cls._DAILY_MARKET_FETCHER_SUPPORT.get(fetcher.name)
            if supported is not None and market not in supported:
                skipped.append(fetcher.name)
            else:
                kept.append(fetcher)

        if skipped:
            logger.info(
                "[数据源路由] %s 日线跳过不支持的数据源: %s",
                market,
                ", ".join(skipped),
            )
        return kept

    @classmethod
    def _filter_fetchers_by_capability(
        cls,
        fetchers: List[BaseFetcher],
        capability: str,
    ) -> List[BaseFetcher]:
        """Skip request-time unavailable fetchers before entering route-specific loops."""
        kept: List[BaseFetcher] = []
        skipped: List[str] = []

        for fetcher in fetchers:
            if cls._is_fetcher_available(fetcher, capability=capability):
                kept.append(fetcher)
            else:
                skipped.append(fetcher.name)

        if skipped:
            logger.info(
                "[数据源路由] %s 跳过暂不可用的数据源: %s",
                capability or "request",
                ", ".join(skipped),
            )

        return kept

    @classmethod
    def _daily_health_key(cls, fetcher: BaseFetcher, market: str) -> str:
        """构造日线数据源健康状态键。"""
        return f"daily_data:{market}:{fetcher.name}"

    @classmethod
    def _is_daily_source_available(
        cls,
        fetcher: BaseFetcher,
        market: str,
    ) -> bool:
        """判断日线数据源是否可用。"""
        key = cls._daily_health_key(fetcher, market)
        if cls._daily_source_health.is_available(key):
            return True
        logger.info(
            "[数据源健康度] %s 日线跳过短期熔断的数据源: %s",
            market,
            fetcher.name,
        )
        return False

    @staticmethod
    def _daily_source_unavailable_error(fetcher: BaseFetcher) -> str:
        """构造日线数据源不可用错误。"""
        return f"[{fetcher.name}] (CircuitOpen) 数据源短期熔断"

    @classmethod
    def _record_daily_source_success(cls, fetcher: BaseFetcher, market: str) -> None:
        """记录日线数据源调用成功。"""
        cls._daily_source_health.record_success(cls._daily_health_key(fetcher, market))

    @classmethod
    def _record_daily_source_failure(cls, fetcher: BaseFetcher, market: str, error: str) -> None:
        """记录日线数据源调用失败。"""
        cls._daily_source_health.record_failure(cls._daily_health_key(fetcher, market), error=error)

    @classmethod
    def reset_daily_source_health(cls) -> None:
        """Reset daily source health state for tests/admin diagnostics."""
        cls._daily_source_health.reset()

    def _get_cached_stock_name(self, stock_code: str) -> Optional[str]:
        """读取缓存的股票名称。"""
        self._ensure_concurrency_guards()
        with self._stock_name_cache_lock:
            return self._stock_name_cache.get(stock_code)

    def _cache_stock_name(self, stock_code: str, name: Optional[str]) -> Optional[str]:
        """写入股票名称缓存。"""
        if name is None:
            return None
        self._ensure_concurrency_guards()
        with self._stock_name_cache_lock:
            self._stock_name_cache[stock_code] = name
        return name

    def _get_tickflow_fetcher(self):
        """Lazily create a TickFlow fetcher for market-review-only calls."""
        from src.config import get_config

        config = get_config()
        api_key = (getattr(config, "tickflow_api_key", None) or "").strip()

        if not hasattr(self, "_tickflow_lock") or self._tickflow_lock is None:
            self._tickflow_lock = RLock()

        with self._tickflow_lock:
            current_fetcher = getattr(self, "_tickflow_fetcher", None)
            current_key = getattr(self, "_tickflow_api_key", None)

            if not api_key:
                if current_fetcher is not None and hasattr(current_fetcher, "close"):
                    try:
                        current_fetcher.close()
                    except Exception as exc:
                        logger.debug("[TickFlowFetcher] 关闭旧实例失败: %s", exc)
                self._tickflow_fetcher = None
                self._tickflow_api_key = None
                return None

            configured_fetcher = self._get_fetcher_by_name("TickFlowFetcher")
            if configured_fetcher is not None:
                return configured_fetcher

            if current_fetcher is not None and current_key == api_key:
                return current_fetcher

            if current_fetcher is not None and hasattr(current_fetcher, "close"):
                try:
                    current_fetcher.close()
                except Exception as exc:
                    logger.debug("[TickFlowFetcher] 切换实例时关闭失败: %s", exc)

            try:
                from data_provider.tickflow_fetcher import TickFlowFetcher

                fetcher = TickFlowFetcher(
                    api_key=api_key,
                    kline_adjust=getattr(config, "tickflow_kline_adjust", "none"),
                    batch_daily_enabled=getattr(config, "tickflow_batch_daily_enabled", True),
                    batch_size=getattr(config, "tickflow_batch_size", 100),
                    priority=getattr(config, "tickflow_priority", 2),
                )
                self._tickflow_fetcher = fetcher
                self._tickflow_api_key = api_key
                return fetcher
            except Exception as exc:
                logger.warning("[TickFlowFetcher] 初始化失败: %s", exc)
                self._tickflow_fetcher = None
                self._tickflow_api_key = None
                return None

    def close(self) -> None:
        """Best-effort release of manager-owned resources."""
        if not hasattr(self, "_tickflow_lock") or self._tickflow_lock is None:
            self._tickflow_lock = RLock()

        with self._tickflow_lock:
            current_fetcher = getattr(self, "_tickflow_fetcher", None)
            self._tickflow_fetcher = None
            self._tickflow_api_key = None

        if current_fetcher is not None and hasattr(current_fetcher, "close"):
            try:
                current_fetcher.close()
            except Exception as exc:
                logger.debug("[TickFlowFetcher] 关闭管理器资源失败: %s", exc)

    def __del__(self) -> None:
        """析构时释放抓取器资源。"""
        try:
            self.close()
        except Exception:
            # Best-effort cleanup during interpreter shutdown.
            pass

    def _get_fundamental_cache_key(self, stock_code: str, budget_seconds: Optional[float] = None) -> str:
        """生成基本面缓存 key（包含预算分桶以避免低预算结果污染高预算请求）。"""
        normalized_code = normalize_stock_code(stock_code)
        if budget_seconds is None:
            return f"{normalized_code}|budget=default"
        try:
            budget = max(0.0, float(budget_seconds))
        except (TypeError, ValueError):
            budget = 0.0
        # 100ms bucket to balance cache reuse and scenario isolation.
        budget_bucket = int(round(budget * 10))
        return f"{normalized_code}|budget={budget_bucket}"

    def _prune_fundamental_cache(self, ttl_seconds: int, max_entries: int) -> None:
        """Prune expired and overflow fundamental cache items."""
        with self._fundamental_cache_lock:
            if not self._fundamental_cache:
                return

            now_ts = time.time()
            if ttl_seconds > 0:
                cache_items = list(self._fundamental_cache.items())
                expired_keys = [
                    key
                    for key, value in cache_items
                    if now_ts - float(value.get("ts", 0)) > ttl_seconds
                ]
                for key in expired_keys:
                    self._fundamental_cache.pop(key, None)

            if max_entries > 0 and len(self._fundamental_cache) > max_entries:
                overflow = len(self._fundamental_cache) - max_entries
                sorted_items = sorted(
                    list(self._fundamental_cache.items()),
                    key=lambda item: float(item[1].get("ts", 0)),
                )
                for key, _ in sorted_items[:overflow]:
                    self._fundamental_cache.pop(key, None)

    @staticmethod
    def _try_scalar_isna(value: Any, context: str) -> Optional[bool]:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return value_format.try_scalar_isna(value, context, logger=logger)

    @staticmethod
    def _is_missing_board_value(value: Any) -> bool:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return board_format.is_missing_board_value(value, use_try_scalar_isna=DataFetcherManager._try_scalar_isna)

    @staticmethod
    def _normalize_belong_boards(raw_data: Any) -> List[Dict[str, Any]]:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return board_format.normalize_belong_boards(raw_data, use_is_missing_board_value=DataFetcherManager._is_missing_board_value)

    def _init_default_fetchers(self) -> None:
        """
        初始化默认数据源列表

        优先级动态调整逻辑：
        - 如果配置了 TUSHARE_TOKEN：实例化 TushareFetcher，并按其内部逻辑提升优先级
        - 如果配置了 Longbridge OAuth 或 Legacy 凭据：实例化 LongbridgeFetcher 作为美股/港股兜底
        - 未配置的可选数据源不实例化，避免在批量拉取时反复探测无效源
        - 默认优先级：
          0. EfinanceFetcher (Priority 0) - 最高优先级
          1. AkshareFetcher (Priority 1)
          2. PytdxFetcher (Priority 2) - 通达信
          3. BaostockFetcher (Priority 3)
          4. YfinanceFetcher (Priority 4)
          5. TencentFetcher (Priority 5) - A 股最终兜底
        """
        from data_provider.runtime.fetcher_factory import build_default_fetchers

        fetchers = build_default_fetchers()
        # 初始化数据源列表
        self._ensure_concurrency_guards()
        with self._fetchers_lock:
            self._fetchers = fetchers

            # 按优先级排序（Tushare 如果配置了 Token 且初始化成功，优先级为 0）
            self._fetchers.sort(key=lambda f: f.priority)
            self._refresh_fetcher_indexes_locked()

        # 构建优先级说明
        priority_info = ", ".join([f"{f.name}(P{f.priority})" for f in self._get_fetchers_snapshot()])
        logger.info(f"已初始化 {len(self._fetchers)} 个数据源（按优先级）: {priority_info}")

    def add_fetcher(self, fetcher: BaseFetcher) -> None:
        """添加数据源并重新排序"""
        self._ensure_concurrency_guards()
        with self._fetchers_lock:
            self._fetchers.append(fetcher)
            self._fetchers.sort(key=lambda f: f.priority)
            self._refresh_fetcher_indexes_locked()

    def get_daily_data(self, stock_code: str, start_date: Optional[str]=None, end_date: Optional[str]=None, days: int=30) -> Tuple[pd.DataFrame, str]:
        return self._daily_entry().get_daily_data(stock_code, start_date, end_date, days)

    @property
    def available_fetchers(self) -> List[str]:
        """返回可用数据源名称列表"""
        return [f.name for f in self._get_fetchers_snapshot()]

    def prefetch_realtime_quotes(self, stock_codes: List[str]) -> int:
        return prefetch_realtime_quotes(
            stock_codes,
            get_fetcher=self._get_fetcher_by_name,
            invoke=self._call_fetcher_method,
            get_quote=self.get_realtime_quote,
        )

    def prefetch_daily_klines(self, stock_codes: List[str], days: int = 30) -> int:
        """Batch-prefetch TickFlow daily K-lines without changing per-stock callers."""
        fetcher = self._get_fetcher_by_name("TickFlowFetcher", capability="daily_data")
        if fetcher is None or not hasattr(fetcher, "prefetch_daily_klines"):
            return 0

        try:
            return int(
                self._call_fetcher_method(
                    fetcher,
                    "prefetch_daily_klines",
                    stock_codes,
                    days=days,
                )
                or 0
            )
        except Exception as exc:
            logger.warning("[TickFlowFetcher] daily K-line prefetch failed: %s", exc)
            return 0

    @staticmethod
    def _utc_now_iso() -> str:
        return utc_now_iso()

    @staticmethod
    def _parse_realtime_timestamp(value: Any) -> Optional[datetime]:
        return parse_realtime_timestamp(value)

    @staticmethod
    def _realtime_fetcher_token(fetcher_name: str, **kw) -> str:
        return realtime_fetcher_token(fetcher_name, **kw)

    def _enrich_realtime_quote(
        self,
        quote,
        *,
        fallback_from: Optional[str] = None,
        realtime_cache_ttl: Optional[int] = None,
    ):
        return enrich_realtime_quote(
            quote,
            fallback_from=fallback_from,
            realtime_cache_ttl=realtime_cache_ttl,
            now=self._utc_now_iso,
            parse=self._parse_realtime_timestamp,
        )

    def get_realtime_quote(self, stock_code: str, *, log_final_failure: bool=True):
        return self._realtime_coordination().get_realtime_quote(stock_code, log_final_failure=log_final_failure)

    # Fields worth supplementing from secondary sources when the primary
    # source returns None for them. Ordered by importance.
    _SUPPLEMENT_FIELDS = [
        'volume_ratio', 'turnover_rate',
        'pe_ratio', 'pb_ratio', 'total_mv', 'circ_mv',
        'amplitude',
    ]

    @classmethod
    def _quote_needs_supplement(cls, quote) -> bool:
        return quote_needs_supplement(quote, cls._SUPPLEMENT_FIELDS)

    @classmethod
    def _merge_quote_fields(cls, primary, secondary) -> list:
        return merge_quote_fields(primary, secondary, cls._SUPPLEMENT_FIELDS)

    def _longbridge_preferred(self, capability: str = "realtime_quote") -> bool:
        """Return True when Longbridge keys are configured and available.

        When True, non-A-share routing (US & HK) uses Longbridge as the
        primary data source with Yfinance/AkShare as fallback.
        """
        return self._get_fetcher_by_name(
            "LongbridgeFetcher",
            capability=capability,
        ) is not None

    def _try_fetcher_quote(self, stock_code: str, fetcher_name: str, **kw):
        return self._realtime_coordination()._try_fetcher_quote(stock_code, fetcher_name, **kw)

    def _supplement_quote(
        self, stock_code: str, primary_quote, fetcher_name: str, **kw
    ):
        return supplement_quote(
            stock_code,
            primary_quote,
            fetcher_name,
            needs=self._quote_needs_supplement,
            try_quote=self._try_fetcher_quote,
            merge=self._merge_quote_fields,
            **kw
        )

    def _supplement_from_longbridge(self, stock_code: str, primary_quote):
        """Shortcut kept for backward-compat with A-share general loop."""
        return self._supplement_quote(stock_code, primary_quote, "LongbridgeFetcher")

    def _chip_source(self):
        """按需接线筹码实现，使用原资源及 domain 规则。"""
        from data_provider.chip.base import ChipCoordination

        return ChipCoordination(
            use_call_fetcher_method=lambda *args, **kwargs: self._call_fetcher_method(
                *args, **kwargs
            ),
            use_get_fetchers_snapshot=lambda *args, **kwargs: self._get_fetchers_snapshot(
                *args, **kwargs
            ),
            call_normalize_stock_code=lambda *args, **kwargs: normalize_stock_code(
                *args, **kwargs
            ),
            call_record_provider_run=lambda *args, **kwargs: record_provider_run(
                *args, **kwargs
            ),
            call_record_provider_run_started=lambda *args, **kwargs: record_provider_run_started(
                *args, **kwargs
            ),
            call_summarize_exception=lambda *args, **kwargs: summarize_exception(
                *args, **kwargs
            ),
            call_is_meaningful_chip_distribution=lambda *args, **kwargs: _is_meaningful_chip_distribution(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
            read_time=lambda: time,
        )

    def get_chip_distribution(self, stock_code: str):
        return self._chip_source().get_chip_distribution(stock_code)

    def _stock_names(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.name_lookup import StockNameLookup

        return StockNameLookup(
            use_cache_stock_name=lambda *args, **kwargs: self._cache_stock_name(
                *args, **kwargs
            ),
            use_call_fetcher_method=lambda *args, **kwargs: self._call_fetcher_method(
                *args, **kwargs
            ),
            use_ensure_concurrency_guards=lambda *args, **kwargs: self._ensure_concurrency_guards(
                *args, **kwargs
            ),
            use_get_cached_stock_name=lambda *args, **kwargs: self._get_cached_stock_name(
                *args, **kwargs
            ),
            use_get_fetchers_snapshot=lambda *args, **kwargs: self._get_fetchers_snapshot(
                *args, **kwargs
            ),
            use_is_fetcher_available=lambda *args, **kwargs: self._is_fetcher_available(
                *args, **kwargs
            ),
            use_batch_get_stock_names=lambda *args, **kwargs: self.batch_get_stock_names(
                *args, **kwargs
            ),
            use_get_realtime_quote=lambda *args, **kwargs: self.get_realtime_quote(
                *args, **kwargs
            ),
            use_get_stock_name=lambda *args, **kwargs: self.get_stock_name(
                *args, **kwargs
            ),
            read_stock_name_cache=lambda: self._stock_name_cache,
            read_stock_name_cache_lock=lambda: self._stock_name_cache_lock,
            call_get_index_stock_name=lambda *args, **kwargs: get_index_stock_name(
                *args, **kwargs
            ),
            call_is_meaningful_stock_name=lambda *args, **kwargs: is_meaningful_stock_name(
                *args, **kwargs
            ),
            call_normalize_stock_code=lambda *args, **kwargs: normalize_stock_code(
                *args, **kwargs
            ),
            current_stock_name_map=lambda: STOCK_NAME_MAP,
            log=lambda: logger,
        )

    def get_stock_name(
        self, stock_code: str, allow_realtime: bool = True
    ) -> Optional[str]:
        return self._stock_names().get_stock_name(stock_code, allow_realtime)

    def _sector_source(self):
        """按需加载能力实现，保留原缓存/SDK/诊断与动态替换入口。"""
        from data_provider.sector.coordination import SectorCoordination

        return SectorCoordination(
            use_copy_ranking_rows=lambda *args, **kwargs: self._copy_ranking_rows(
                *args, **kwargs
            ),
            use_get_fetchers_snapshot=lambda *args, **kwargs: self._get_fetchers_snapshot(
                *args, **kwargs
            ),
            use_get_sector_manager=lambda *args, **kwargs: self._get_sector_manager(
                *args, **kwargs
            ),
            use_get_sector_rankings_with_meta=lambda *args, **kwargs: self._get_sector_rankings_with_meta(
                *args, **kwargs
            ),
            use_normalize_belong_boards=lambda *args, **kwargs: self._normalize_belong_boards(
                *args, **kwargs
            ),
            current_fetchers=lambda: self._fetchers,
            class_concept_rankings_cache_lock=lambda: self.__class__._concept_rankings_cache_lock,
            class_concept_rankings_cache_ttl_seconds=lambda: self.__class__._CONCEPT_RANKINGS_CACHE_TTL_SECONDS,
            class_concept_rankings_empty_cache_ttl_seconds=lambda: self.__class__._CONCEPT_RANKINGS_EMPTY_CACHE_TTL_SECONDS,
            class_concept_rankings_cache=lambda: self.__class__._concept_rankings_cache,
            call_market_tag=lambda *args, **kwargs: _market_tag(*args, **kwargs),
            call_normalize_stock_code=lambda *args, **kwargs: normalize_stock_code(
                *args, **kwargs
            ),
            call_record_provider_run=lambda *args, **kwargs: record_provider_run(
                *args, **kwargs
            ),
            call_record_provider_run_started=lambda *args, **kwargs: record_provider_run_started(
                *args, **kwargs
            ),
            call_summarize_exception=lambda *args, **kwargs: summarize_exception(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
            read_time=lambda: time,
        )

    def get_belong_boards(self, stock_code: str) -> List[Dict[str, Any]]:
        return self._sector_source().get_belong_boards(stock_code)

    def prefetch_stock_names(
        self, stock_codes: List[str], use_bulk: bool = False
    ) -> None:
        return self._stock_names().prefetch_stock_names(stock_codes, use_bulk)

    def batch_get_stock_names(self, stock_codes: List[str]) -> Dict[str, str]:
        return self._stock_names().batch_get_stock_names(stock_codes)

    def _market_index_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.indices import MarketIndexLookup

        return MarketIndexLookup(
            use_get_tickflow_fetcher=lambda *args, **kwargs: self._get_tickflow_fetcher(
                *args, **kwargs
            ),
            current_fetchers=lambda: self._fetchers,
            read_logger=lambda: logger,
        )

    def get_main_indices(self, region: str = "cn") -> List[Dict[str, Any]]:
        return self._market_index_source().get_main_indices(region)

    def _market_statistics_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.statistics import MarketStatisticsLookup

        return MarketStatisticsLookup(
            use_get_tickflow_fetcher=lambda *args, **kwargs: self._get_tickflow_fetcher(
                *args, **kwargs
            ),
            current_fetchers=lambda: self._fetchers,
            read_logger=lambda: logger,
            read_time=lambda: time,
        )

    def get_market_stats(self, *, purpose: str = "unspecified") -> Dict[str, Any]:
        return self._market_statistics_source().get_market_stats(purpose=purpose)

    def _run_with_timeout(
        self, task: Callable[[], Any], timeout_seconds: float, task_name: str
    ) -> Tuple[Optional[Any], Optional[str], int]:
        return self._execution_policy()._run_with_timeout(task, timeout_seconds, task_name)

    def _run_with_retry(
        self, task: Callable[[], Any], timeout_seconds: float, task_name: str
    ) -> Tuple[Optional[Any], Optional[str], int]:
        return self._execution_policy()._run_with_retry(task, timeout_seconds, task_name)

    def _get_fundamental_config(self):
        """返回基本面取数配置。"""
        from src.config import get_config
        return get_config()

    @staticmethod
    def _normalize_source_chain(
        entries: Any,
        provider: str,
        result: str,
        duration_ms: int,
    ) -> List[Dict[str, Any]]:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return fundamental_format.normalize_source_chain(entries, provider, result, duration_ms)

    @staticmethod
    def _block_status(payload: Dict[str, Any], available: bool = True) -> str:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return fundamental_format.block_status(payload, available)

    @staticmethod
    def _build_fundamental_block(
        status: str,
        payload: Optional[Dict[str, Any]] = None,
        source_chain: Optional[List[Dict[str, Any]]] = None,
        errors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return fundamental_format.build_fundamental_block(status, payload, source_chain, errors)

    @staticmethod
    def _has_meaningful_payload(payload: Any) -> bool:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return fundamental_format.has_meaningful_payload(payload, use_has_meaningful_payload=DataFetcherManager._has_meaningful_payload, use_try_scalar_isna=DataFetcherManager._try_scalar_isna)

    @staticmethod
    def _infer_block_status(payload: Any, fallback_status: str) -> str:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return fundamental_format.infer_block_status(payload, fallback_status, use_has_meaningful_payload=DataFetcherManager._has_meaningful_payload)

    @staticmethod
    def _should_cache_fundamental_context(context: Any) -> bool:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return fundamental_format.should_cache_fundamental_context(context, use_has_meaningful_payload=DataFetcherManager._has_meaningful_payload)

    def _build_market_not_supported(self, market: str, reason: str) -> Dict[str, Any]:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return fundamental_format.build_market_not_supported(market, reason, use_build_fundamental_block=self._build_fundamental_block)

    def _build_offshore_fundamental_context(
        self,
        stock_code: str,
        market: str,
        budget_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        return self._fundamental_source().build_offshore_fundamental_context(
            stock_code, market, budget_seconds
        )

    def build_failed_fundamental_context(
        self, stock_code: str, reason: str
    ) -> Dict[str, Any]:
        return self._fundamental_source().build_failed_fundamental_context(
            stock_code, reason
        )

    def _fundamental_source(self):
        """读取原资源与运行时扩展点，委托唯一基本面实现。"""
        from data_provider.fundamentals.aggregate import FundamentalAggregation

        return FundamentalAggregation(
            use_get_sector_rankings_with_meta=lambda *args, **kwargs: self._get_sector_rankings_with_meta(
                *args, **kwargs
            ),
            use_build_fundamental_block=lambda *args, **kwargs: self._build_fundamental_block(
                *args, **kwargs
            ),
            use_build_market_not_supported=lambda *args, **kwargs: self._build_market_not_supported(
                *args, **kwargs
            ),
            use_build_offshore_fundamental_context=lambda *args, **kwargs: self._build_offshore_fundamental_context(
                *args, **kwargs
            ),
            current_fundamental_adapter=lambda: self._fundamental_adapter,
            current_fundamental_cache=lambda: self._fundamental_cache,
            current_fundamental_cache_lock=lambda: self._fundamental_cache_lock,
            use_get_fundamental_cache_key=lambda *args, **kwargs: self._get_fundamental_cache_key(
                *args, **kwargs
            ),
            use_get_tw_institutional_source=lambda *args, **kwargs: self._get_tw_institutional_source(
                *args, **kwargs
            ),
            use_has_meaningful_payload=lambda *args, **kwargs: self._has_meaningful_payload(
                *args, **kwargs
            ),
            use_infer_block_status=lambda *args, **kwargs: self._infer_block_status(
                *args, **kwargs
            ),
            use_normalize_source_chain=lambda *args, **kwargs: self._normalize_source_chain(
                *args, **kwargs
            ),
            use_prune_fundamental_cache=lambda *args, **kwargs: self._prune_fundamental_cache(
                *args, **kwargs
            ),
            use_run_with_retry=lambda *args, **kwargs: self._run_with_retry(
                *args, **kwargs
            ),
            use_should_cache_fundamental_context=lambda *args, **kwargs: self._should_cache_fundamental_context(
                *args, **kwargs
            ),
            current_yfinance_fundamental_adapter=lambda: self._yfinance_fundamental_adapter,
            use_get_board_context=lambda *args, **kwargs: self.get_board_context(
                *args, **kwargs
            ),
            use_get_capital_flow_context=lambda *args, **kwargs: self.get_capital_flow_context(
                *args, **kwargs
            ),
            use_get_dragon_tiger_context=lambda *args, **kwargs: self.get_dragon_tiger_context(
                *args, **kwargs
            ),
            use_get_realtime_quote=lambda *args, **kwargs: self.get_realtime_quote(
                *args, **kwargs
            ),
            market_tag=lambda *args, **kwargs: _market_tag(*args, **kwargs),
            is_etf=lambda *args, **kwargs: _is_etf_code(*args, **kwargs),
            clock=lambda: time,
        )

    def _fundamental_flow_source(self):
        """读取原资源与运行时扩展点，委托唯一基本面实现。"""
        from data_provider.fundamentals.flow_source import FundamentalFlowOperations

        return FundamentalFlowOperations(
            use_build_fundamental_block=lambda *args, **kwargs: self._build_fundamental_block(
                *args, **kwargs
            ),
            current_fundamental_adapter=lambda: self._fundamental_adapter,
            use_normalize_source_chain=lambda *args, **kwargs: self._normalize_source_chain(
                *args, **kwargs
            ),
            use_run_with_retry=lambda *args, **kwargs: self._run_with_retry(
                *args, **kwargs
            ),
            market_tag=lambda *args, **kwargs: _market_tag(*args, **kwargs),
            is_etf=lambda *args, **kwargs: _is_etf_code(*args, **kwargs),
            clock=lambda: time,
        )

    def get_fundamental_context(
        self, stock_code: str, budget_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        return self._fundamental_source().get_fundamental_context(
            stock_code, budget_seconds
        )

    def get_capital_flow_context(
        self, stock_code: str, budget_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        return self._fundamental_flow_source().get_capital_flow_context(
            stock_code, budget_seconds
        )

    def get_dragon_tiger_context(
        self, stock_code: str, budget_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        return self._fundamental_flow_source().get_dragon_tiger_context(
            stock_code, budget_seconds
        )

    def get_board_context(
        self, stock_code: str, budget_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        return self._fundamental_source().get_board_context(stock_code, budget_seconds)

    def _get_sector_rankings_with_meta(
        self,
        n: int = 5,
    ) -> Tuple[List[Dict], List[Dict], List[Dict[str, Any]], str]:
        return self._sector_source().get_sector_rankings_with_meta(n)

    def get_sector_rankings(self, n: int = 5) -> Tuple[List[Dict], List[Dict]]:
        return self._sector_source().get_sector_rankings(n)

    @staticmethod
    def _copy_ranking_rows(rows: List[Dict]) -> List[Dict]:
        """委托能力规范化，保留原静态/实例覆盖入口。"""
        return board_format.copy_ranking_rows(rows)

    @classmethod
    def clear_concept_rankings_cache_for_tests(cls) -> None:
        """测试用：清空概念排行缓存。"""
        with cls._concept_rankings_cache_lock:
            cls._concept_rankings_cache.clear()

    def get_concept_rankings(self, n: int = 5) -> Tuple[List[Dict], List[Dict]]:
        return self._sector_source().get_concept_rankings(n)

    def get_hot_stocks(self, n: int = 10) -> List[Dict[str, Any]]:
        return self._sector_source().get_hot_stocks(n)

    def _execution_policy(self):
        """装配原执行预算，保留超时槽与旧方法扩展点。"""
        from data_provider.common.execution import BoundedExecution

        return BoundedExecution(
            read_timeout_slots=lambda: self._fundamental_timeout_slots,
            read_config=lambda: self._get_fundamental_config(),
            use_run_with_timeout=lambda *args, **kwargs: self._run_with_timeout(
                *args, **kwargs
            ),
            read_time=lambda: time,
            read_thread=lambda: Thread,
        )

    def _realtime_coordination(self):
        """接线能力协调，保留旧覆盖点与原状态所有权。"""
        from data_provider.realtime.coordination import RealtimeCoordination

        return RealtimeCoordination(
            use_call_fetcher_method=lambda *args, **kwargs: self._call_fetcher_method(*args, **kwargs),
            use_enrich_realtime_quote=lambda *args, **kwargs: self._enrich_realtime_quote(*args, **kwargs),
            use_get_fetcher_by_name=lambda *args, **kwargs: self._get_fetcher_by_name(*args, **kwargs),
            use_longbridge_preferred=lambda *args, **kwargs: self._longbridge_preferred(*args, **kwargs),
            use_merge_quote_fields=lambda *args, **kwargs: self._merge_quote_fields(*args, **kwargs),
            use_quote_needs_supplement=lambda *args, **kwargs: self._quote_needs_supplement(*args, **kwargs),
            use_realtime_fetcher_token=lambda *args, **kwargs: self._realtime_fetcher_token(*args, **kwargs),
            use_supplement_quote=lambda *args, **kwargs: self._supplement_quote(*args, **kwargs),
            use_try_fetcher_quote=lambda *args, **kwargs: self._try_fetcher_quote(*args, **kwargs),
            global_List=lambda: List,
            global_Optional=lambda: Optional,
            global_is_hk_market=lambda: _is_hk_market,
            global_is_jp_market=lambda: _is_jp_market,
            global_is_kr_market=lambda: _is_kr_market,
            global_is_tw_market=lambda: _is_tw_market,
            global_logger=lambda: logger,
            global_normalize_stock_code=lambda: normalize_stock_code,
            global_record_provider_run=lambda: record_provider_run,
            global_record_provider_run_started=lambda: record_provider_run_started,
            global_summarize_exception=lambda: summarize_exception,
            global_time=lambda: time,
        )


    def _daily_entry(self):
        """接线能力协调，保留旧覆盖点与原状态所有权。"""
        from data_provider.kline.daily_history import DailyEntryOperations

        return DailyEntryOperations(
            use_filter_daily_fetchers_for_market=lambda *args, **kwargs: self._filter_daily_fetchers_for_market(*args, **kwargs),
            use_filter_fetchers_by_capability=lambda *args, **kwargs: self._filter_fetchers_by_capability(*args, **kwargs),
            use_get_fetchers_snapshot=lambda *args, **kwargs: self._get_fetchers_snapshot(*args, **kwargs),
            read_call_fetcher_method=lambda: self._call_fetcher_method,
            read_daily_source_unavailable_error=lambda: self._daily_source_unavailable_error,
            read_is_daily_source_available=lambda: self._is_daily_source_available,
            read_longbridge_preferred=lambda: self._longbridge_preferred,
            read_record_daily_source_failure=lambda: self._record_daily_source_failure,
            read_record_daily_source_success=lambda: self._record_daily_source_success,
            global_DailyHistoryOperations=lambda: DailyHistoryOperations,
            global_DailyHistoryRequest=lambda: DailyHistoryRequest,
            global_is_hk_market=lambda: _is_hk_market,
            global_is_jp_market=lambda: _is_jp_market,
            global_is_kr_market=lambda: _is_kr_market,
            global_is_tw_market=lambda: _is_tw_market,
            global_fetch_daily_history=lambda: fetch_daily_history,
            global_normalize_stock_code=lambda: normalize_stock_code,
            global_record_provider_run=lambda: record_provider_run,
            global_record_provider_run_started=lambda: record_provider_run_started,
            global_time=lambda: time,
        )



