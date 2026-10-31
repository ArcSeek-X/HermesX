# -*- coding: utf-8 -*-
"""全市场快照适配器：把 ``data_provider`` 的三个快照源转成应用端口形状。

``data_provider/`` 原位保留为数据源能力包（ADR-001），本适配器只做「取全市场
快照」这一用例所需的三源封装（东财 clist 直连 / 腾讯批量行情 / akshare 高覆盖
兜底）；回退链编排、日志与空判定仍在应用层用例（``eod_picker_service``），与
迁移前的职责划分逐字一致。``AkshareFetcher`` 模块级单例（共享其全市场快照缓存）
属数据源实现细节，随本适配器收纳。

实现端口：:class:`~src.application.quote.ports.MarketSnapshotPort`
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class DataProviderMarketSnapshotSource:
    """:class:`MarketSnapshotPort` 的 ``data_provider`` 实现。

    失败语义与迁移前一致：``data_provider`` 各源函数的异常原样上抛，由用例按
    回退链决定降级；返回值即上游 ``pandas.DataFrame``（或 ``None``），本层不做
    字段加工。
    """

    def __init__(self) -> None:
        self._akshare_fetcher: Any = None
        self._fetcher_lock = threading.Lock()

    def fetch_eastmoney_snapshot(self) -> Any:
        """东财 clist 直连全市场快照（惰性导入，异常上抛由用例回退）。"""
        from data_provider.eastmoney_quote_snapshot import fetch_eastmoney_market_snapshot

        return fetch_eastmoney_market_snapshot()

    def fetch_tencent_snapshot(self) -> Any:
        """腾讯批量行情全市场快照（惰性导入，异常上抛由用例回退）。"""
        from data_provider.tencent_quote_snapshot import fetch_tencent_market_snapshot

        return fetch_tencent_market_snapshot()

    def fetch_akshare_snapshot(self) -> Any:
        """akshare 高覆盖兜底快照；复用单例以共享其模块级快照缓存。"""
        fetcher = self._get_akshare_fetcher()
        return fetcher.get_realtime_quote_snapshot()

    def _get_akshare_fetcher(self) -> Any:
        """复用 AkshareFetcher 的单例（与迁移前模块级 ``_fetcher`` 语义一致）。"""
        if self._akshare_fetcher is None:
            with self._fetcher_lock:
                if self._akshare_fetcher is None:
                    from data_provider.akshare_fetcher import AkshareFetcher

                    self._akshare_fetcher = AkshareFetcher()
        return self._akshare_fetcher
