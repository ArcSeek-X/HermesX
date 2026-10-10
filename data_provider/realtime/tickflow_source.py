# -*- coding: utf-8 -*-
"""
@file: tickflow_source.py
@description: 实时行情 tickflow source，复用既有 TickFlowFetcher 实时行情通道。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Optional

from data_provider.realtime.base import RealtimeSource
from data_provider.realtime_types import UnifiedRealtimeQuote
from data_provider.tickflow_fetcher import TickFlowFetcher
from src.config import get_config


class TickflowRealtimeSource(RealtimeSource):
    """复用 TickFlowFetcher 的实时行情 source。"""

    source_id = "tickflow"

    def __init__(self) -> None:
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
