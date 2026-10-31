# -*- coding: utf-8 -*-
"""MarketDataPort 适配器：包装 ``DataFetcherManager``。

将 ``data_provider`` 的 dataclass（``UnifiedRealtimeQuote``、``ChipDistributionResult``）
在此层转为纯 dict，使 application 层不感知数据源类型。

DataFetcherManager 采用模块级惰性单例（与原 ``data_tools._get_fetcher_manager`` 行为一致）。
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DataFetcherManagerAdapter:
    """实现 :class:`~src.application.agent.market_data_ports.MarketDataPort` 协议。"""

    _singleton = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        # Lazy import to avoid pulling data_provider at module level
        from data_provider import DataFetcherManager
        self._manager = DataFetcherManager()

    @classmethod
    def get_instance(cls) -> "DataFetcherManagerAdapter":
        """Thread-safe singleton for reuse across tool calls."""
        if cls._singleton is None:
            with cls._lock:
                if cls._singleton is None:
                    cls._singleton = cls()
        return cls._singleton

    @classmethod
    def reset(cls) -> None:
        """Clear cached singleton (for runtime config reloads)."""
        with cls._lock:
            cls._singleton = None

    # ------------------------------------------------------------------
    # MarketDataPort protocol methods
    # ------------------------------------------------------------------

    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        quote = self._manager.get_realtime_quote(stock_code)
        if quote is None:
            return None
        return {
            "code": quote.code,
            "name": quote.name,
            "price": quote.price,
            "change_pct": quote.change_pct,
            "change_amount": quote.change_amount,
            "volume": quote.volume,
            "amount": quote.amount,
            "volume_ratio": quote.volume_ratio,
            "turnover_rate": quote.turnover_rate,
            "amplitude": quote.amplitude,
            "open": quote.open_price,
            "high": quote.high,
            "low": quote.low,
            "pre_close": quote.pre_close,
            "pe_ratio": quote.pe_ratio,
            "pb_ratio": quote.pb_ratio,
            "total_mv": quote.total_mv,
            "circ_mv": quote.circ_mv,
            "change_60d": quote.change_60d,
            "source": quote.source.value if hasattr(quote.source, "value") else str(quote.source),
        }

    def get_chip_distribution(self, stock_code: str) -> Optional[Dict[str, Any]]:
        chip = self._manager.get_chip_distribution(stock_code)
        if chip is None:
            return None
        return {
            "code": chip.code,
            "date": chip.date,
            "source": chip.source,
            "profit_ratio": chip.profit_ratio,
            "avg_cost": chip.avg_cost,
            "cost_90_low": chip.cost_90_low,
            "cost_90_high": chip.cost_90_high,
            "concentration_90": chip.concentration_90,
            "cost_70_low": chip.cost_70_low,
            "cost_70_high": chip.cost_70_high,
            "concentration_70": chip.concentration_70,
        }

    def get_fundamental_context(self, stock_code: str) -> Dict[str, Any]:
        return self._manager.get_fundamental_context(stock_code)

    def build_failed_fundamental_context(self, stock_code: str, reason: str) -> Dict[str, Any]:
        return self._manager.build_failed_fundamental_context(stock_code, reason)

    def get_belong_boards(self, stock_code: str) -> List[Dict[str, Any]]:
        return self._manager.get_belong_boards(stock_code)

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        return self._manager.get_stock_name(stock_code)

    def get_capital_flow_context(self, stock_code: str) -> Dict[str, Any]:
        return self._manager.get_capital_flow_context(stock_code)

    def get_main_indices(self, region: str = "cn") -> List[Dict[str, Any]]:
        return self._manager.get_main_indices(region=region) or []

    def get_sector_rankings(self, n: int = 10) -> Optional[Tuple[List[Dict], List[Dict]]]:
        return self._manager.get_sector_rankings(n=n)
