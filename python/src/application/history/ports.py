# -*- coding: utf-8 -*-
"""分析历史用例的端口定义。

``HistoryRepositoryPort`` 描述 ``HistoryService`` 实际读取的 9 个方法：实现方既可以是
``src.storage.DatabaseManager``（当前装配目标，内部已委托给 ``persistence.repositories``），
也可以是测试里的假对象。端口按结构匹配（``Protocol``），不要求显式继承。

``StockCodeNormalizerPort`` 承接 ``data_provider.base.normalize_stock_code``：应用层
不允许 import 数据源包，因此由 ``src.infrastructure.indexing`` 提供实现。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union


class HistoryRepositoryPort(Protocol):
    """分析历史与关联资讯的只读能力（含批量删除）。"""

    def get_analysis_history_paginated(
        self,
        code: Optional[Union[str, List[str]]] = None,
        report_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Any], int]:
        """分页查询分析历史，返回 ``(records, total)``。"""

    def get_analysis_history_by_id(self, record_id: int) -> Optional[Any]:
        """按主键精确查询单条记录。"""

    def get_latest_analysis_by_query_id(
        self,
        query_id: str,
        *,
        code: Optional[str] = None,
        report_type: Optional[str] = None,
    ) -> Optional[Any]:
        """按 ``query_id`` 查询最新一条记录（可附加代码 / 报告类型过滤）。"""

    def get_analysis_history(
        self,
        code: Optional[str] = None,
        query_id: Optional[str] = None,
        days: int = 30,
        limit: int = 50,
        exclude_query_id: Optional[str] = None,
    ) -> List[Any]:
        """按代码或 ``query_id`` 查询历史记录列表。"""

    def delete_analysis_history_records(self, record_ids: List[int]) -> int:
        """批量删除（连同派生数据），返回实际删除条数。"""

    def get_distinct_stocks_from_history(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 200,
        include_market_review: bool = False,
    ) -> List[Any]:
        """每只股票取最新一条记录（默认排除大盘复盘）。"""

    def get_news_intel_by_query_id(self, query_id: str, limit: int = 20) -> List[Any]:
        """按 ``query_id`` 查询关联新闻。"""

    def get_recent_news(self, code: str, days: int = 7, limit: int = 20) -> List[Any]:
        """查询指定股票最近 N 天的新闻。"""

    def get_latest_fundamental_snapshot(
        self,
        query_id: str,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        """取最新基本面快照 payload（缺失时返回 ``None``）。"""


class StockCodeNormalizerPort(Protocol):
    """股票代码归一化（用于个股栏去重分组）。"""

    def normalize(self, stock_code: str) -> str:
        """把 ``SH600519`` / ``600519.SH`` / ``HK00700`` 等变体归一为同一代码。"""


class HistoryDailyBarFetcherPort(Protocol):
    """日线取数网络回退端口：``load_history_df`` DB 未命中时按代码与天数窗口取历史日线。"""

    def get_daily_data(self, stock_code: str, days: int) -> Any:
        """返回 ``(pd.DataFrame, source_name)`` 元组，或抛出异常（应用层不依赖 pandas，故返回 ``Any``）。"""
