# -*- coding: utf-8 -*-
"""财经日历（Live Calendar）抓取-落库-查询链路测试。

重点覆盖回归：统一数据源重构后 ``WallstreetcnNewsSource.fetch`` 的 calendar / live
模式必须返回**类型对象**（CalendarEventEntry / LiveNewsEntry），而非原始 dict。
服务层 ``_calendar_entry_to_rows`` / ``_live_news_entry_to_item_fields`` 按属性访问
（含 ``scope_values`` 这类 @property），一旦拿到 dict 会抛
``'dict' object has no attribute 'title'``，并在接口层被兜底成 500。

注：用例不访问真实上游，保证离线确定性。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import patch

from data_provider.news.base import NewsRequest
from data_provider.news.wallstreetcn_source import WallstreetcnNewsSource
from data_provider.wallstreetcn_calendar_fetcher import CalendarEventEntry
from src.config import Config
from src.infrastructure.persistence.repositories.intelligence_repository import (
    IntelligenceRepository,
)
from src.application.intelligence.intelligence_service import IntelligenceService
from src.storage import DatabaseManager

# 资讯源/仓储端口装配（calendar 用例经 NewsSourcePort + IntelligenceRepositoryPort；seam 幂等，模块级一次即可）
from src.bootstrap.intelligence import configure_intelligence_repository, configure_news_source

configure_news_source()
configure_intelligence_repository()

_YEAR, _MONTH = 2026, 8
# 月内一个确定时间点（UTC 秒级），保证落在 _month_utc_range(2026, 8) 闭区间内
_PUBLIC_TS = int(datetime(2026, 8, 15, 2, 0, 0, tzinfo=timezone.utc).timestamp())


def _fe_entry() -> CalendarEventEntry:
    """宏观大事件（FE）：命中 macro 关键字。"""
    return CalendarEventEntry(
        item_id=9001,
        public_date=_PUBLIC_TS,
        calendar_type="FE",
        title="美联储议息会议公布利率决议",
        foresight="前瞻 | 关注点阵图与缩表表态。",
        importance=4,
        country="美国",
        country_id="US",
    )


def _fd_entry() -> CalendarEventEntry:
    """经济数据（FD）：归入 economic_data，不参与分类打标。"""
    return CalendarEventEntry(
        item_id=9002,
        public_date=_PUBLIC_TS,
        calendar_type="FD",
        title="美国7月CPI年率",
        foresight="",
        importance=3,
        country="美国",
        country_id="US",
        actual="",
        forecast="3.0%",
        previous="3.1%",
        wscn_ticker="US.CPI.YoY",
    )


class NewsSourceContractTestCase(unittest.TestCase):
    """数据源契约：calendar / live 模式返回类型对象而非 dict。"""

    def test_calendar_mode_returns_event_objects(self) -> None:
        with patch(
            "data_provider.news.wallstreetcn_source.WallstreetcnCalendarFetcher.fetch_range",
            return_value=[_fe_entry(), _fd_entry()],
        ):
            source = WallstreetcnNewsSource()
            result = source.fetch(NewsRequest(mode="calendar", start_ts=_PUBLIC_TS, end_ts=_PUBLIC_TS + 3600))
        assert result is not None
        self.assertTrue(result.items)
        for item in result.items:
            # 关键断言：不得是 dict，否则服务层属性访问崩溃
            self.assertIsInstance(item, CalendarEventEntry)
            self.assertFalse(isinstance(item, dict))
            self.assertTrue(hasattr(item, "title"))

    def test_calendar_mode_includes_raw_dict_on_entry(self) -> None:
        """原始字典通过 entry.raw 保留，不因返回对象而丢失溯源能力。"""
        entry = _fe_entry()
        self.assertIsInstance(entry.raw, dict)


class LiveCalendarServiceTestCase(unittest.TestCase):
    """服务层：list_calendar 惰性抓取链路端到端可用（回归 500）。"""

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = os.path.join(self._temp_dir.name, "live_calendar.db")
        os.environ["WALLSTREETCN_CALENDAR_ENABLED"] = "true"
        Config._instance = None
        DatabaseManager.reset_instance()
        IntelligenceService._calendar_countries_cache = []
        IntelligenceService._calendar_countries_cached_at = None
        self.service = IntelligenceService()
        self.repo = IntelligenceRepository()

    def tearDown(self) -> None:
        self._temp_dir.cleanup()
        for key in ("DATABASE_PATH", "WALLSTREETCN_CALENDAR_ENABLED"):
            os.environ.pop(key, None)
        Config._instance = None
        DatabaseManager.reset_instance()
        IntelligenceService._calendar_countries_cache = []
        IntelligenceService._calendar_countries_cached_at = None

    def _patch_fetch(self) -> Any:
        return patch(
            "data_provider.news.wallstreetcn_source.WallstreetcnCalendarFetcher.fetch_range",
            return_value=[_fe_entry(), _fd_entry()],
        )

    def test_list_calendar_lazy_fetch_does_not_crash(self) -> None:
        """库中该月无数据触发惰性抓取：全链路不得抛 'dict' object has no attribute。"""
        with self._patch_fetch():
            page = self.service.list_calendar(year=_YEAR, month=_MONTH, include_economic_data=True)
        self.assertFalse(page["degraded"])
        self.assertEqual(page["total"], 2)
        titles = {item["title"] for item in page["items"]}
        self.assertIn("美联储议息会议公布利率决议", titles)
        self.assertIn("美国7月CPI年率", titles)

    def test_economic_data_toggle_filters_fd_events(self) -> None:
        """include_economic_data=False 时 FD 经济数据应被过滤，仅保留 FE。"""
        with self._patch_fetch():
            without = self.service.list_calendar(year=_YEAR, month=_MONTH, include_economic_data=False)
        self.assertEqual(without["total"], 1)
        self.assertEqual(without["items"][0]["calendar_type"], "FE")

    def test_tab_filter_macro_excludes_economic(self) -> None:
        """宏观 Tab 命中 FE 事件；FD 经济数据无 tab_keys，按 tab 过滤时不应出现。"""
        with self._patch_fetch():
            macro = self.service.list_calendar(
                year=_YEAR, month=_MONTH, tab="macro", include_economic_data=True
            )
        self.assertEqual(macro["total"], 1)
        self.assertIn("macro", macro["items"][0]["tab_keys"])


if __name__ == "__main__":
    unittest.main()
