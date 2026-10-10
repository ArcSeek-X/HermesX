# -*- coding: utf-8 -*-
"""
@file: akshare_source.py
@description: 实时行情 akshare source，复用既有 AkshareFetcher 实时行情通道。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Optional

from data_provider.akshare_fetcher import AkshareFetcher
from data_provider.realtime.base import RealtimeSource
from data_provider.realtime_types import UnifiedRealtimeQuote


class AkshareRealtimeSource(RealtimeSource):
    """复用 AkshareFetcher 的实时行情 source。

    `market_source` 指定 akshare 的行情通道（`tencent` / `sina` / `em`）；
    `source_id` 允许以「通道」为粒度注册到 Manager，使注册 id 与
    `REALTIME_SOURCE_PRIORITY` 配置词表（`tencent` / `akshare_sina` /
    `akshare_em`）保持一致。
    """

    source_id = "akshare"

    def __init__(self, market_source: str = "em", source_id: Optional[str] = None) -> None:
        self.market_source = market_source
        self.fetcher = AkshareFetcher()
        if source_id:
            self.source_id = source_id

    def fetch(self, request: str) -> Optional[UnifiedRealtimeQuote]:
        """通过既有 AkshareFetcher 获取实时行情。"""
        return self.fetcher.get_realtime_quote(request, source=self.market_source)
