# -*- coding: utf-8 -*-
"""Agent 工具层的行情取数端口。

端口定义 9 个方法，覆盖 ``DataFetcherManager`` 在 ``data_tools.py`` 与
``market_tools.py`` 中的实际调用面。返回纯数据形状（``dict`` / ``list[dict]`` /
``str`` / ``None``），不暴露 ``data_provider`` 的 dataclass。

实现方：:class:`~src.infrastructure.agent_runtime.market_data_provider.DataFetcherManagerAdapter`
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Tuple


class MarketDataPort(Protocol):
    """Agent 工具所需的行情/数据取数能力。"""

    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """取实时行情快照，返回字段字典（code/name/price/change_pct/volume/…/source）；
        所有数据源失败返回 ``None``。"""

    def get_chip_distribution(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """取筹码分布数据，返回字段字典（code/date/source/profit_ratio/avg_cost/…）；
        无数据返回 ``None``。"""

    def get_fundamental_context(self, stock_code: str) -> Dict[str, Any]:
        """取基本面统一上下文（valuation/boards/…）；异常由调用方处理。"""

    def build_failed_fundamental_context(self, stock_code: str, reason: str) -> Dict[str, Any]:
        """构建基本面失败的降级上下文（用于异常路径填充）。"""

    def get_belong_boards(self, stock_code: str) -> List[Dict[str, Any]]:
        """取个股所属板块列表。"""

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """取股票名称，无数据返回 ``None``。"""

    def get_capital_flow_context(self, stock_code: str) -> Dict[str, Any]:
        """取主力资金流向上下文（status/data 结构）。"""

    def get_main_indices(self, region: str = "cn") -> List[Dict[str, Any]]:
        """取主要市场指数行情（上证/深证/沪深300 或 S&P/Nasdaq/Dow）。"""

    def get_sector_rankings(self, n: int = 10) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """取板块涨跌幅排行，返回 (top_sectors, bottom_sectors)；无数据 ``None``。"""
