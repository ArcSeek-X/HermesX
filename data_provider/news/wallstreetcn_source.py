# -*- coding: utf-8 -*-
"""
@file: wallstreetcn_source.py
@description: 资讯能力 wallstreetcn source，统一承接快讯与财经日历。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from data_provider.news.base import NewsDataSource, NewsRequest, NewsResult
from data_provider.wallstreetcn_calendar_fetcher import CalendarFetchError, WallstreetcnCalendarFetcher
from data_provider.wallstreetcn_live_news_fetcher import LiveNewsFetchError, WallstreetcnLiveNewsFetcher
from src.config import get_config


class WallstreetcnNewsSource(NewsDataSource):
    """复用华尔街见闻快讯与财经日历 fetcher 的统一资讯 source。"""

    source_id = "wallstreetcn"

    def __init__(
        self,
        *,
        request_get: Optional[Callable[..., Any]] = None,
        live_base_url: Optional[str] = None,
        live_timeout: Optional[float] = None,
        calendar_base_url: Optional[str] = None,
        calendar_timeout: Optional[float] = None,
    ) -> None:
        config = get_config()
        self.live_fetcher = WallstreetcnLiveNewsFetcher(
            base_url=live_base_url or getattr(config, "wscn_live_news_base_url", "https://api-one.wallstcn.com"),
            timeout=live_timeout or getattr(config, "wscn_live_news_timeout_sec", 8.0),
            request_get=request_get,
        )
        self.calendar_fetcher = WallstreetcnCalendarFetcher(
            base_url=calendar_base_url or config.wallstreetcn_calendar_base_url,
            timeout=calendar_timeout or config.wallstreetcn_calendar_timeout,
            request_get=request_get,
        )
        self.calendar_enabled = config.wallstreetcn_calendar_enabled

    def fetch(self, request: NewsRequest) -> Optional[NewsResult]:
        """按 mode 获取快讯或财经日历。"""
        if request.mode == "calendar_countries":
            countries = self.calendar_fetcher.fetch_countries()
            return NewsResult(
                items=list(countries),
                source=self.source_id,
                metadata={"mode": request.mode},
            )

        if request.mode == "calendar":
            if not self.calendar_enabled or request.start_ts is None or request.end_ts is None:
                return None
            events = self.calendar_fetcher.fetch_range(request.start_ts, request.end_ts)
            return NewsResult(
                items=[event.raw or event.__dict__ for event in events],
                source=self.source_id,
                metadata={"mode": request.mode},
            )

        entries, next_cursor, polling_cursor = self.live_fetcher.fetch_channel(
            request.channel_id,
            limit=request.limit,
            cursor=request.cursor,
        )
        return NewsResult(
            items=[entry.raw or entry.__dict__ for entry in entries],
            source=self.source_id,
            next_cursor=next_cursor,
            polling_cursor=polling_cursor,
            metadata={"mode": "live", "channel_id": request.channel_id},
        )

    @staticmethod
    def list_live_news_channels():
        """返回华尔街见闻快讯频道定义。"""
        return WallstreetcnLiveNewsFetcher.list_channels()

    @staticmethod
    def is_known_live_news_channel(channel_id: str) -> bool:
        """判断快讯频道 ID 是否受支持。"""
        return WallstreetcnLiveNewsFetcher.is_known_channel(channel_id)

    @staticmethod
    def live_news_scope_value(channel_id: str) -> str:
        """频道 ID 转换为仓内使用的 scope_value。"""
        return WallstreetcnLiveNewsFetcher.to_scope_value(channel_id)

    def build_live_news_url(self, channel_id: str, *, limit: int, cursor: Optional[str] = None) -> str:
        """构造单频道快讯请求 URL，供服务层做 SSRF 白名单校验。"""
        return self.live_fetcher.build_url(channel_id, limit=limit, cursor=cursor)


__all__ = [
    "CalendarFetchError",
    "LiveNewsFetchError",
    "WallstreetcnNewsSource",
]
