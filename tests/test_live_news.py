# -*- coding: utf-8 -*-
"""实时财经快讯（Live News）测试。

覆盖三个层次：
1. Fetcher：频道定义、URL 拼装、响应解析、多频道归属推导（不发起真实网络请求）；
2. Service：抓取落库、多频道拆行、重要级过滤、按日过滤、游标分页、降级链路；
3. 边界：科技频道「只看重要的」为空、秒/毫秒单位换算、缺字段容错。

注：所有用例均不访问真实上游，保证测试确定性与离线可运行。
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import patch

from data_provider.wallstreetcn_live_news import (
    LiveNewsFetchError,
    WallstreetcnLiveNewsFetcher,
)
from api.v1.endpoints.intelligence import (
    get_live_news_item,
    list_live_news,
    list_live_news_channels,
    refresh_live_news,
)
from api.v1.schemas.intelligence import LiveNewsRefreshRequest
from src.config import Config
from src.repositories.intelligence_repo import IntelligenceRepository
from src.services.intelligence_service import IntelligenceService, IntelligenceServiceError
from src.storage import DatabaseManager

# 上游成功响应样例：两条快讯，一条跨多频道且为重要级
OFFICIAL_PAYLOAD: Dict[str, Any] = {
    "code": 20000,
    "message": "OK",
    "data": {
        "items": [
            {
                "id": 3157010,
                "title": "",
                "content": "<p>现货钯金涨8.00%，现报1457.21美元/盎司。</p>",
                "content_text": "现货钯金涨8.00%，现报1457.21美元/盎司。",
                "display_time": 1787925480,
                "score": 2,
                # 含非 Tab 的内部标记（xgb-channel），解析时应被忽略
                "channels": ["global-channel", "a-stock-channel", "xgb-channel"],
                "uri": "https://wallstreetcn.com/livenews/3157010",
                "author": {"display_name": "葛冬瑾"},
                "symbols": [],
            },
            {
                "id": 3157011,
                "title": "",
                "content_text": "美股盘前小幅波动。",
                "display_time": 1787925380,
                "score": 1,
                "channels": ["global-channel"],
                "uri": "https://wallstreetcn.com/livenews/3157011",
                "author": None,
            },
            # 缺 id 与正文的脏数据，应被丢弃
            {"title": "", "content_text": "", "display_time": 1787925280},
        ],
        "next_cursor": 1787912832,
        "polling_cursor": 3157012,
    },
}

# 上游业务错误响应
ERROR_PAYLOAD: Dict[str, Any] = {"code": 71404, "message": "Not Found", "data": {}}


class _FakeResponse:
    """最小化的响应替身，供 Fetcher 的解析路径使用。"""

    def __init__(self, payload: Dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.content = json.dumps(payload).encode("utf-8")

    def iter_content(self, chunk_size: int = 8192):
        yield self.content

    def close(self) -> None:
        return None


class LiveNewsFetcherTestCase(unittest.TestCase):
    """Fetcher 层：定义、解析与容错。"""

    def test_channels_definition(self) -> None:
        channels = WallstreetcnLiveNewsFetcher.list_channels()
        self.assertEqual(len(channels), 8)
        self.assertEqual(channels[0]["channel_id"], "global-channel")
        self.assertEqual(channels[0]["scope_value"], "global")
        # 每个频道都必须同时具备入参 ID、落库短码与 Tab 文案
        for item in channels:
            self.assertTrue(item["channel_id"].endswith("-channel"))
            self.assertTrue(item["scope_value"])
            self.assertTrue(item["label"])

    def test_channel_lookup_helpers(self) -> None:
        self.assertTrue(WallstreetcnLiveNewsFetcher.is_known_channel("tech-channel"))
        self.assertFalse(WallstreetcnLiveNewsFetcher.is_known_channel("unknown-channel"))
        self.assertEqual(WallstreetcnLiveNewsFetcher.to_scope_value("a-stock-channel"), "a-stock")
        # 未知频道回退到「要闻」
        self.assertEqual(WallstreetcnLiveNewsFetcher.to_scope_value("nope"), "global")
        self.assertIsNotNone(WallstreetcnLiveNewsFetcher.from_scope_value("hk-stock"))
        self.assertIsNone(WallstreetcnLiveNewsFetcher.from_scope_value("nope"))

    def test_build_url(self) -> None:
        fetcher = WallstreetcnLiveNewsFetcher(base_url="https://example.com")
        self.assertEqual(
            fetcher.build_url("global-channel", limit=30),
            "https://example.com/apiv1/content/lives?channel=global-channel&limit=30",
        )
        self.assertEqual(
            fetcher.build_url("global-channel", limit=30, cursor="1787912832"),
            "https://example.com/apiv1/content/lives?channel=global-channel&limit=30&cursor=1787912832",
        )
        # limit 应被收敛到 1~100
        self.assertIn("limit=100", fetcher.build_url("global-channel", limit=999))
        self.assertIn("limit=1", fetcher.build_url("global-channel", limit=0))

    def test_parse_payload(self) -> None:
        entries, next_cursor, polling_cursor = WallstreetcnLiveNewsFetcher.parse_payload(
            OFFICIAL_PAYLOAD, channel_id="global-channel"
        )
        # 脏数据被丢弃，剩 2 条
        self.assertEqual(len(entries), 2)
        self.assertEqual(next_cursor, "1787912832")
        self.assertEqual(polling_cursor, "3157012")

        first = entries[0]
        self.assertEqual(first.item_id, 3157010)
        # 正文优先取 content_text 且已剥离 HTML
        self.assertEqual(first.content, "现货钯金涨8.00%，现报1457.21美元/盎司。")
        self.assertEqual(first.display_time, 1787925480)  # 秒级时间戳
        self.assertEqual(first.score, 2)
        self.assertEqual(first.author, "葛冬瑾")
        # 非 Tab 的内部频道标记（xgb-channel）应被过滤掉
        self.assertEqual(first.scope_values, ("global", "a-stock"))

    def test_parse_payload_upstream_error(self) -> None:
        with self.assertRaises(LiveNewsFetchError):
            WallstreetcnLiveNewsFetcher.parse_payload(ERROR_PAYLOAD, channel_id="global-channel")

    def test_parse_payload_invalid_shape(self) -> None:
        for payload in (None, [], {"code": 20000}, {"code": 20000, "data": {}}):
            with self.assertRaises(LiveNewsFetchError):
                WallstreetcnLiveNewsFetcher.parse_payload(payload, channel_id="global-channel")

    def test_fetch_channel_unsupported(self) -> None:
        fetcher = WallstreetcnLiveNewsFetcher()
        with self.assertRaises(LiveNewsFetchError):
            fetcher.fetch_channel("nope-channel", limit=10)

    def test_fetch_channel_uses_injected_getter(self) -> None:
        """验证 request_get 可被注入（服务层借此复用 SSRF 校验能力）。"""
        calls: List[Dict[str, Any]] = []

        def fake_get(url: str, **kwargs: Any):
            calls.append({"url": url, **kwargs})
            return _FakeResponse(OFFICIAL_PAYLOAD)

        fetcher = WallstreetcnLiveNewsFetcher(
            base_url="https://example.com", request_get=fake_get
        )
        entries, _, _ = fetcher.fetch_channel("global-channel", limit=5)
        self.assertEqual(len(entries), 2)
        self.assertEqual(len(calls), 1)
        # 必须带浏览器 UA 与 Referer，否则上游会拒绝
        self.assertIn("User-Agent", calls[0]["headers"])
        self.assertIn("Referer", calls[0]["headers"])
        self.assertEqual(calls[0]["headers"]["Referer"], "https://wallstreetcn.com/")


class LiveNewsServiceTestCase(unittest.TestCase):
    """Service 层：落库、查询、降级与边界。"""

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = os.path.join(self._temp_dir.name, "live_news.db")
        os.environ["NEWS_INTEL_RETENTION_DAYS"] = "30"
        os.environ["NEWS_INTEL_MAX_ITEMS_PER_SOURCE"] = "50"
        os.environ["NEWS_INTEL_FETCH_TIMEOUT_SEC"] = "3"
        os.environ["WSCN_LIVE_NEWS_ENABLED"] = "true"
        os.environ["WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC"] = "300"
        os.environ["WSCN_LIVE_NEWS_IMPORTANT_SCORE"] = "2"
        os.environ["WSCN_LIVE_NEWS_FALLBACK_NEWSNOW"] = "true"
        Config._instance = None
        DatabaseManager.reset_instance()
        IntelligenceService.reset_auto_fetch_state()
        IntelligenceService.reset_live_news_state()
        self.service = IntelligenceService()
        self.repo = IntelligenceRepository()

    def tearDown(self) -> None:
        # 必须完整清理：本用例会改写 DATABASE_PATH 与快讯相关环境变量，
        # 若不还原会污染同进程内后续测试（Config / DatabaseManager 均为单例）。
        IntelligenceService.reset_live_news_state()
        self._temp_dir.cleanup()
        self._reset_shared_state()

    @staticmethod
    def _reset_shared_state() -> None:
        """还原进程级共享状态，避免跨测试文件污染。"""
        for key in (
            "DATABASE_PATH",
            "WSCN_LIVE_NEWS_ENABLED",
            "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
            "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC",
            "NEWS_INTEL_RETENTION_DAYS",
            "NEWS_INTEL_MAX_ITEMS_PER_SOURCE",
            "NEWS_INTEL_FETCH_TIMEOUT_SEC",
        ):
            os.environ.pop(key, None)
        Config._instance = None
        DatabaseManager.reset_instance()

    # ------------------------------------------------------------------
    # 频道与抓取
    # ------------------------------------------------------------------
    def test_channels_normal_mode(self) -> None:
        result = self.service.live_news_channels()
        self.assertEqual(len(result["channels"]), 8)
        self.assertFalse(result["degraded"])
        self.assertEqual(result["source"], "wallstreetcn")
        self.assertEqual(result["channels"][0], {"value": "global-channel", "label": "要闻"})

    def test_refresh_persists_and_expands_channels(self) -> None:
        """一条快讯命中 2 个 Tab 频道时，应拆成 2 行落库。"""
        with patch.object(
            WallstreetcnLiveNewsFetcher,
            "fetch_channel",
            return_value=(
                WallstreetcnLiveNewsFetcher.parse_payload(
                    OFFICIAL_PAYLOAD, channel_id="global-channel"
                )[0],
                "1787912832",
                "3157012",
            ),
        ):
            result = self.service.refresh_live_news(channels=["global-channel"])

        self.assertFalse(result["degraded"])
        self.assertEqual(result["errors"], [])
        # 快讯1 命中 global + a-stock 两行；快讯2 命中 global 一行
        self.assertEqual(result["fetched_count"], 3)

        rows, total = self.repo.list_live_news_items(scope_value="global", limit=50)
        self.assertEqual(total, 2)
        a_stock_rows, a_stock_total = self.repo.list_live_news_items(
            scope_value="a-stock", limit=50
        )
        self.assertEqual(a_stock_total, 1)

        # 重要级应落库
        important_row = next(row for row in rows if row.url.endswith("/livenews/3157010"))
        self.assertEqual(important_row.importance, 2)
        self.assertEqual(important_row.scope_type, "channel")

    def test_list_live_news_maps_fields(self) -> None:
        self.test_refresh_persists_and_expands_channels()
        page = self.service.list_live_news(channel="global-channel", limit=10)
        self.assertEqual(page["total"], 2)
        self.assertFalse(page["degraded"])
        self.assertIsNone(page["next_cursor"])

        item = next(entry for entry in page["items"] if entry["id"] == 3157010)
        self.assertEqual(item["score"], 2)
        self.assertTrue(item["important"])
        self.assertEqual(item["author"], "葛冬瑾")
        self.assertIn("global-channel", item["channels"])
        self.assertEqual(item["uri"], "https://wallstreetcn.com/livenews/3157010")

    def test_important_only_filter(self) -> None:
        self.test_refresh_persists_and_expands_channels()
        important = self.service.list_live_news(
            channel="global-channel", important_only=True, limit=10
        )
        self.assertEqual(important["total"], 1)
        self.assertEqual(important["items"][0]["id"], 3157010)

        # 未勾选时返回全部
        all_items = self.service.list_live_news(channel="global-channel", limit=10)
        self.assertEqual(all_items["total"], 2)

    def test_tech_channel_has_no_important_items(self) -> None:
        """实测科技频道重要率为 0，过滤后应为空（前端走专门空态文案）。"""
        tech_payload = {
            "code": 20000,
            "message": "OK",
            "data": {
                "items": [
                    {
                        "id": 3156729,
                        "content_text": "AI机器人公司Sharpa已完成超45亿人民币融资。",
                        "display_time": 1787905680,
                        "score": 1,
                        "channels": ["tech-channel"],
                        "uri": "https://wallstreetcn.com/livenews/3156729",
                    }
                ],
                "next_cursor": None,
                "polling_cursor": None,
            },
        }
        with patch.object(
            WallstreetcnLiveNewsFetcher,
            "fetch_channel",
            return_value=(
                WallstreetcnLiveNewsFetcher.parse_payload(
                    tech_payload, channel_id="tech-channel"
                )[0],
                None,
                None,
            ),
        ):
            self.service.refresh_live_news(channels=["tech-channel"])

        page = self.service.list_live_news(channel="tech-channel", limit=10)
        self.assertEqual(page["total"], 1)
        important = self.service.list_live_news(
            channel="tech-channel", important_only=True, limit=10
        )
        self.assertEqual(important["total"], 0)

    def test_keyword_search(self) -> None:
        self.test_refresh_persists_and_expands_channels()
        hit = self.service.list_live_news(channel="global-channel", keyword="钯金", limit=10)
        self.assertEqual(hit["total"], 1)
        miss = self.service.list_live_news(channel="global-channel", keyword="不存在的词", limit=10)
        self.assertEqual(miss["total"], 0)

    def test_date_filter(self) -> None:
        self.test_refresh_persists_and_expands_channels()
        target = datetime.fromtimestamp(1787925480, tz=timezone.utc).replace(tzinfo=None)
        day_start = target.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1) - timedelta(seconds=1)

        in_range = self.service.list_live_news(
            channel="global-channel",
            published_from=day_start,
            published_to=day_end,
            limit=10,
        )
        self.assertEqual(in_range["total"], 2)

        # 前一天应查不到任何数据
        prev_start = day_start - timedelta(days=1)
        prev_end = day_start - timedelta(seconds=1)
        out_range = self.service.list_live_news(
            channel="global-channel",
            published_from=prev_start,
            published_to=prev_end,
            limit=10,
        )
        self.assertEqual(out_range["total"], 0)

    def test_cursor_pagination(self) -> None:
        self.test_refresh_persists_and_expands_channels()
        first = self.service.list_live_news(channel="global-channel", limit=1)
        self.assertEqual(len(first["items"]), 1)
        self.assertIsNotNone(first["next_cursor"])

        second = self.service.list_live_news(
            channel="global-channel", limit=1, cursor=first["next_cursor"]
        )
        self.assertEqual(len(second["items"]), 1)
        # 两页不应重复
        self.assertNotEqual(first["items"][0]["id"], second["items"][0]["id"])

    def test_invalid_cursor(self) -> None:
        for bad in ("abc", "123", "abc|def"):
            with self.assertRaises(IntelligenceServiceError):
                self.service.list_live_news(channel="global-channel", cursor=bad)

    def test_unsupported_channel(self) -> None:
        with self.assertRaises(IntelligenceServiceError):
            self.service.list_live_news(channel="nope-channel")

    def test_limit_boundary(self) -> None:
        with self.assertRaises(IntelligenceServiceError):
            self.service.list_live_news(channel="global-channel", limit=0)
        with self.assertRaises(IntelligenceServiceError):
            self.service.list_live_news(channel="global-channel", limit=101)

    # ------------------------------------------------------------------
    # 降级链路
    # ------------------------------------------------------------------
    def test_fallback_to_newsnow(self) -> None:
        """官方源全部失败时，应降级到 NewsNow 并只保留「要闻」频道。"""
        newsnow_payload = {
            "status": "cache",
            "id": "wallstreetcn-quick",
            "updatedTime": 1787925484000,
            "items": [
                {
                    "id": 915,
                    "title": "顺丰控股：上半年总营业收入1555.1亿元",
                    # 注意：毫秒级时间戳，与官方源的秒级不同
                    "extra": {"date": 1787925484000},
                    "url": "https://wallstreetcn.com/livenews/915",
                }
            ],
        }

        with patch.object(
            WallstreetcnLiveNewsFetcher,
            "fetch_channel",
            side_effect=LiveNewsFetchError("upstream down"),
        ), patch.object(
            IntelligenceService,
            "_fetch_newsnow_entries",
            return_value=[self._make_feed_entry(newsnow_payload["items"][0])],
        ):
            result = self.service.refresh_live_news()

        self.assertTrue(result["degraded"])
        self.assertEqual(result["fetched_count"], 1)

        # 降级后频道列表只剩「要闻」
        channels = self.service.live_news_channels()
        self.assertEqual(len(channels["channels"]), 1)
        self.assertEqual(channels["channels"][0]["value"], "global-channel")
        self.assertTrue(channels["degraded"])

        # 降级数据没有重要级，important 恒为 False
        page = self.service.list_live_news(channel="global-channel", limit=10)
        self.assertEqual(page["total"], 1)
        self.assertFalse(page["items"][0]["important"])
        # 正文应回退到标题（NewsNow 的快讯全文在 title 字段）
        self.assertTrue(page["items"][0]["content"])

    def test_fallback_disabled(self) -> None:
        """关闭降级开关时，官方源失败应返回空而不是兜底数据。"""
        os.environ["WSCN_LIVE_NEWS_FALLBACK_NEWSNOW"] = "false"
        Config._instance = None
        service = IntelligenceService()
        with patch.object(
            WallstreetcnLiveNewsFetcher,
            "fetch_channel",
            side_effect=LiveNewsFetchError("upstream down"),
        ):
            result = service.refresh_live_news()
        self.assertFalse(result["degraded"])
        self.assertEqual(result["fetched_count"], 0)
        self.assertTrue(result["errors"])

    def test_disabled_switch(self) -> None:
        os.environ["WSCN_LIVE_NEWS_ENABLED"] = "false"
        Config._instance = None
        service = IntelligenceService()
        result = service.refresh_live_news()
        self.assertTrue(result.get("skipped"))
        self.assertEqual(result["fetched_count"], 0)

    # ------------------------------------------------------------------
    # 按需刷新的节流
    # ------------------------------------------------------------------
    def test_ensure_fresh_throttles(self) -> None:
        cold_start_calls = {"count": 0}
        real_refresh = self.service.refresh_live_news

        def counting_refresh(channels=None):
            cold_start_calls["count"] += 1
            return real_refresh(channels=channels)

        with patch.object(
            WallstreetcnLiveNewsFetcher,
            "fetch_channel",
            return_value=(
                WallstreetcnLiveNewsFetcher.parse_payload(
                    OFFICIAL_PAYLOAD, channel_id="global-channel"
                )[0],
                None,
                None,
            ),
        ), patch.object(self.service, "refresh_live_news", side_effect=counting_refresh):
            self.service.ensure_live_news_fresh("global-channel")
            self.assertEqual(cold_start_calls["count"], 1)
            # 紧接着的第二次调用应被节流拦截
            self.service.ensure_live_news_fresh("global-channel")
            self.assertEqual(cold_start_calls["count"], 1)

    def test_ensure_fresh_skips_when_interval_zero(self) -> None:
        os.environ["WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC"] = "0"
        Config._instance = None
        service = IntelligenceService()
        with patch.object(service, "refresh_live_news") as mocked:
            service.ensure_live_news_fresh("global-channel")
        mocked.assert_not_called()

    def test_ensure_fresh_ignores_unknown_channel(self) -> None:
        with patch.object(self.service, "refresh_live_news") as mocked:
            self.service.ensure_live_news_fresh("nope-channel")
        mocked.assert_not_called()

    # ------------------------------------------------------------------
    # 单位换算
    # ------------------------------------------------------------------
    def test_timestamp_unit_conversion(self) -> None:
        """官方源为秒级，NewsNow 为毫秒级，标准化后应得到同一时刻。"""
        self.assertEqual(
            self.service._timestamp_to_datetime(1787925480),
            datetime.fromtimestamp(1787925480, tz=timezone.utc).replace(tzinfo=None),
        )
        # 非法输入不应抛异常
        self.assertIsNone(self.service._timestamp_to_datetime(None))
        self.assertIsNone(self.service._timestamp_to_datetime("bad"))

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _make_feed_entry(item: Dict[str, Any]):
        """把 NewsNow 条目构造成 FeedEntry（模拟服务层内部解析结果）。"""
        from src.services.intelligence_service import FeedEntry

        return FeedEntry(
            title=str(item.get("title") or ""),
            summary="",
            url=str(item.get("url") or ""),
            source="华尔街见闻快讯",
            published_at=IntelligenceService._parse_datetime_or_timestamp(
                (item.get("extra") or {}).get("date")
            ),
            raw_payload={"source": "newsnow"},
        )


class LiveNewsEndpointTestCase(unittest.TestCase):
    """API 端点层：直接调用路由函数，验证参数解析与响应模型。

    说明：这里不使用 TestClient，因为项目在本地 ``.env`` 开启
    ``ADMIN_AUTH_ENABLED`` 时会对 ``/api/v1/*`` 返回 401；直接调用路由函数
    可以稳定覆盖参数解析与响应契约，不受认证中间件影响。
    """

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = os.path.join(self._temp_dir.name, "live_news_api.db")
        os.environ["WSCN_LIVE_NEWS_ENABLED"] = "true"
        os.environ["WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC"] = "300"
        os.environ["WSCN_LIVE_NEWS_IMPORTANT_SCORE"] = "2"
        Config._instance = None
        DatabaseManager.reset_instance()
        IntelligenceService.reset_live_news_state()
        self.service = IntelligenceService()
        self._entries = WallstreetcnLiveNewsFetcher.parse_payload(
            OFFICIAL_PAYLOAD, channel_id="global-channel"
        )[0]
        # 本用例聚焦于「参数解析 + 响应契约」，因此屏蔽自动刷新。
        # 列表接口默认会先调用 ensure_live_news_fresh() 按需补数据，那会触发
        # 真实 DNS 解析与网络请求；既有测试对 socket.getaddrinfo 做全局 patch，
        # 两者并发会产生竞态并污染后续用例。抓取行为本身由 Service 用例覆盖。
        self._fresh_patcher = patch.object(
            IntelligenceService, "ensure_live_news_fresh", return_value=None
        )
        self._fresh_patcher.start()
        self.addCleanup(self._fresh_patcher.stop)
        # 双保险：即便其他路径触发抓取，也不允许打到真实上游
        self._net_patcher = patch.object(
            WallstreetcnLiveNewsFetcher,
            "fetch_channel",
            return_value=(self._entries, None, None),
        )
        self._net_patcher.start()
        self.addCleanup(self._net_patcher.stop)

    def tearDown(self) -> None:
        # 与 Service 用例同样需要完整清理，避免污染同进程内后续测试
        IntelligenceService.reset_live_news_state()
        self._temp_dir.cleanup()
        LiveNewsServiceTestCase._reset_shared_state()

    def _seed(self) -> None:
        with patch.object(
            WallstreetcnLiveNewsFetcher,
            "fetch_channel",
            return_value=(self._entries, None, None),
        ):
            self.service.refresh_live_news(channels=["global-channel"])

    def test_list_channels_endpoint(self) -> None:
        response = list_live_news_channels()
        self.assertEqual(len(response.channels), 8)
        self.assertFalse(response.degraded)

    def test_list_endpoint(self) -> None:
        self._seed()
        response = list_live_news(
            channel="global-channel",
            important_only=False,
            keyword=None,
            date=None,
            date_from=None,
            date_to=None,
            cursor=None,
            limit=10,
        )
        self.assertEqual(response.total, 2)
        self.assertIsNone(response.next_cursor)
        self.assertGreater(response.server_time, 0)

    def test_list_endpoint_date_string_parsing(self) -> None:
        """日期参数由端点层从 YYYY-MM-DD 解析为闭区间。"""
        self._seed()
        day = datetime.fromtimestamp(1787925480, tz=timezone.utc).strftime("%Y-%m-%d")
        in_range = list_live_news(
            channel="global-channel",
            important_only=False,
            keyword=None,
            date=day,
            date_from=None,
            date_to=None,
            cursor=None,
            limit=10,
        )
        self.assertEqual(in_range.total, 2)

        # 传入一个没有数据的日期
        empty = list_live_news(
            channel="global-channel",
            important_only=False,
            keyword=None,
            date="2000-01-01",
            date_from=None,
            date_to=None,
            cursor=None,
            limit=10,
        )
        self.assertEqual(empty.total, 0)

    def test_list_endpoint_invalid_date(self) -> None:
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            list_live_news(
                channel="global-channel",
                important_only=False,
                keyword=None,
                date="2026/08/28",
                date_from=None,
                date_to=None,
                cursor=None,
                limit=10,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_list_endpoint_invalid_channel(self) -> None:
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            list_live_news(
                channel="nope-channel",
                important_only=False,
                keyword=None,
                date=None,
                date_from=None,
                date_to=None,
                cursor=None,
                limit=10,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_get_item_endpoint(self) -> None:
        self._seed()
        item = get_live_news_item(3157010)
        self.assertEqual(item.id, 3157010)
        self.assertEqual(item.score, 2)
        self.assertTrue(item.important)

    def test_get_item_endpoint_not_found(self) -> None:
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            get_live_news_item(99999999)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_refresh_endpoint(self) -> None:
        with patch.object(
            WallstreetcnLiveNewsFetcher,
            "fetch_channel",
            return_value=(self._entries, None, None),
        ):
            response = refresh_live_news(LiveNewsRefreshRequest(channels=["global-channel"]))
        self.assertEqual(response.fetched_count, 3)
        self.assertFalse(response.degraded)
        self.assertEqual(response.errors, [])


if __name__ == "__main__":
    unittest.main()
