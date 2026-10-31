# -*- coding: utf-8 -*-
"""``StockDataPort`` 的生产适配器：包装 ``data_provider.DataFetcherManager``。

R3-S15b：``StockAnalysisPipeline`` 搬入 ``src/application/analysis/`` 后不得再 import
``data_provider``，取数改经本适配器承接。适配器只在构造期惰性 import 数据源包，
``data_provider`` 的选源、回退、熔断、字段标准化全部原样复用，不在此处重写。

两个行为约束与迁移前逐字一致：

- **一流水线一管理器**：迁移前 `__init__` 每次执行 `DataFetcherManager()`，各 pipeline
  实例互不共享预热缓存。工厂每次调用都新建适配器与内部管理器，不引入单例。
- **可选能力透传**：``MarketHotspotService`` 以 ``getattr(manager, name, None)`` 动态探测
  排行榜类方法（``get_concept_rankings`` / ``get_sector_rankings`` 等），这些方法不属于
  ``StockDataPort`` 的必选面，由 ``__getattr__`` 原样透传；管理器没有该方法时仍抛
  ``AttributeError``，探测语义（得到 ``None``）保持不变。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class DataFetcherManagerStockDataPort:
    """把 ``DataFetcherManager`` 的取数接口转成 ``StockDataPort``。"""

    def __init__(self) -> None:
        from data_provider import DataFetcherManager

        self._manager = DataFetcherManager()

    # —— StockDataPort 必选面（pipeline 实测 10 个调用点）——

    def get_stock_name(
        self, stock_code: str, allow_realtime: bool = True
    ) -> Optional[str]:
        return self._manager.get_stock_name(stock_code, allow_realtime)

    def get_daily_data(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30,
    ) -> Tuple[Any, str]:
        return self._manager.get_daily_data(
            stock_code,
            start_date=start_date,
            end_date=end_date,
            days=days,
        )

    def get_realtime_quote(
        self, stock_code: str, *, log_final_failure: bool = True
    ) -> Any:
        return self._manager.get_realtime_quote(
            stock_code, log_final_failure=log_final_failure
        )

    def get_chip_distribution(self, stock_code: str) -> Any:
        return self._manager.get_chip_distribution(stock_code)

    def get_fundamental_context(
        self, stock_code: str, budget_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        return self._manager.get_fundamental_context(
            stock_code, budget_seconds=budget_seconds
        )

    def build_failed_fundamental_context(
        self, stock_code: str, reason: str
    ) -> Dict[str, Any]:
        return self._manager.build_failed_fundamental_context(stock_code, reason)

    def get_belong_boards(self, stock_code: str) -> List[Dict[str, Any]]:
        return self._manager.get_belong_boards(stock_code)

    def prefetch_daily_klines(self, stock_codes: List[str], days: int = 30) -> int:
        return self._manager.prefetch_daily_klines(stock_codes, days=days)

    def prefetch_realtime_quotes(self, stock_codes: List[str]) -> int:
        return self._manager.prefetch_realtime_quotes(stock_codes)

    def prefetch_stock_names(
        self, stock_codes: List[str], use_bulk: bool = False
    ) -> None:
        return self._manager.prefetch_stock_names(stock_codes, use_bulk=use_bulk)

    # —— 可选能力透传（排行榜等动态探测入口）——

    def __getattr__(self, name: str) -> Any:
        if name == "_manager":
            # __init__ 尚未完成赋值时的防御，避免 __getattr__ 无限递归。
            raise AttributeError(name)
        return getattr(self._manager, name)
