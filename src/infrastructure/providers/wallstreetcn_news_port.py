# -*- coding: utf-8 -*-
"""Wallstreetcn 资讯源端口适配器（data_provider 实现收纳层）。

把 ``data_provider.news.wallstreetcn_source.WallstreetcnNewsSource`` 的频道
元数据、URL 构造与抓取实现绑定到 ``application/intelligence/ports.py`` 的
``NewsSourcePort``；上游专有异常在此转换为应用层端口异常，用例层不再直接
依赖 data_provider 类型（B4c/S2e 同型，由 bootstrap 装配）。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from src.application.intelligence.ports import (
    NewsCalendarFetchError,
    NewsLiveFetchError,
    NewsQuery,
)


class _WallstreetcnNewsHandle:
    """``NewsSourceHandle`` 实现：包一层 data_provider 源实例。"""

    def __init__(self, source: Any) -> None:
        self._source = source

    def build_live_news_url(
        self, channel_id: str, *, limit: int, cursor: str | None = None
    ) -> str:
        return self._source.build_live_news_url(channel_id, limit=limit, cursor=cursor)

    def fetch(self, query: NewsQuery) -> Any:
        from data_provider.news.base import NewsRequest
        from data_provider.news.wallstreetcn_source import (
            CalendarFetchError,
            LiveNewsFetchError,
        )

        request = NewsRequest(
            mode=query.mode,
            channel_id=query.channel_id,
            limit=query.limit,
            cursor=query.cursor,
            start_ts=query.start_ts,
            end_ts=query.end_ts,
        )
        try:
            return self._source.fetch(request)
        except LiveNewsFetchError as exc:
            raise NewsLiveFetchError(str(exc)) from exc
        except CalendarFetchError as exc:
            raise NewsCalendarFetchError(str(exc)) from exc


class WallstreetcnNewsPort:
    """``NewsSourcePort`` 实现：元数据转发 + 运行时句柄工厂。"""

    def list_channels(self) -> List[Dict[str, Any]]:
        from data_provider.news.wallstreetcn_source import WallstreetcnNewsSource

        return WallstreetcnNewsSource.list_live_news_channels()

    def is_known_channel(self, channel_id: str) -> bool:
        from data_provider.news.wallstreetcn_source import WallstreetcnNewsSource

        return WallstreetcnNewsSource.is_known_live_news_channel(channel_id)

    def channel_scope_value(self, channel_id: str) -> str:
        from data_provider.news.wallstreetcn_source import WallstreetcnNewsSource

        return WallstreetcnNewsSource.live_news_scope_value(channel_id)

    def create_handle(
        self,
        *,
        request_get: Callable[..., Any],
        live_base_url: str,
        live_timeout: float,
        calendar_base_url: str,
        calendar_timeout: float,
    ) -> _WallstreetcnNewsHandle:
        from data_provider.news.wallstreetcn_source import WallstreetcnNewsSource

        source = WallstreetcnNewsSource(
            request_get=request_get,
            live_base_url=live_base_url,
            live_timeout=live_timeout,
            calendar_base_url=calendar_base_url,
            calendar_timeout=calendar_timeout,
        )
        return _WallstreetcnNewsHandle(source)
