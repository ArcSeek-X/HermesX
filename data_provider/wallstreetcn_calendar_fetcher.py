# -*- coding: utf-8 -*-
"""华尔街见闻「财经日历」抓取器（Calendar Fetcher）。

职责边界
--------
本模块**只负责与华尔街见闻日历接口的 HTTP 交互与原始响应解析**，不承载：

- 事件分类打标（宏观 / 财报 / 新股 / 活动，由服务层 ``CalendarService`` 负责）
- 落库与去重（由服务层 / 仓储层负责）
- SSRF / DNS 校验（由服务层注入安全的 ``request_get`` 回调提供）
- 数据源降级策略（上游失败时读库存，由服务层编排）

接口契约（实测于 2026-09-01，详见 docs/Live-calendar.md §2）
--------------------------------------------------------------
::

    # 国家字典
    GET {base_url}/apiv1/finance/countries
    # 日历事件（按 UTC 秒级时间戳区间）
    GET {base_url}/apiv1/finance/macrodatas?start=<ts>&end=<ts>

    成功响应::

        {
          "code": 20000, "message": "OK",
          "data": {
            "items": [
              {
                "id": 15044, "public_date": 1788192000, "calendar_type": "FE",
                "country": "美国", "country_id": "US", "importance": 4,
                "title": "美联储主席沃什在杰克逊霍尔年会首秀", "foresight": "前瞻 | ...",
                "actual": "", "forecast": "", "previous": "", "revised": "",
                "wscn_ticker": "", "flag_uri": "https://...", "uri": "", ...
              }
            ]
          }
        }

已知边界（实测结论，详见 docs/Live-calendar.md §2）
---------------------------------------------------
- ``macrodatas`` 一次返回区间内全部事件（无分页游标），单月约 500~900 条；
- ``calendar_type`` 取值 ``FE``（财经大事件）/ ``FD``（经济数据指标）；
- ``public_date`` 为**秒级 UTC**，部分全天事件为 ``0``；
- ``importance`` 实测取值 ``{1,2,3,4}``（上限 4，无 5），缺失需归为业务量纲的 ``0``（无）；
- 「宏观 / 财报 / 新股 / 活动」分类**不是上游字段**，须由服务层按标题关键字打标。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# 成功响应码；非该值一律视为上游异常
_SUCCESS_CODE = 20000

# 默认请求头：上游对 UA / Referer 有校验，缺失会返回非 20000 响应
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 hermesx-calendar/1.0"
)
_DEFAULT_REFERER = "https://wallstreetcn.com/calendar"

# 默认接口基址（注意：与快讯的 api-one.wallstcn.com 不同）
_DEFAULT_BASE_URL = "https://api-one-wscn.awtmt.com"

# 单次响应体最大体积（字节），防止异常上游撑爆内存
_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class CalendarFetchError(Exception):
    """日历抓取失败（网络异常、上游非 20000、响应结构不合法等）。"""


@dataclass(frozen=True)
class CalendarCountryEntry:
    """解析后的单个国家字典条目。"""

    country_id: str
    country_name: str
    currency: str
    currency_name: str
    flag_uri: str


@dataclass(frozen=True)
class CalendarEventEntry:
    """解析后的单条日历事件，与上游字段一一对应的中间结构。

    Attributes:
        item_id: 上游事件 ID，可作为去重键。
        public_date: 事件时间，**秒级** Unix 时间戳；``0`` 表示全天事件。
        calendar_type: ``FE``（财经大事件）/ ``FD``（经济数据指标）。
        title: 事件标题（简短，日历格子主文案）。
        foresight: 前瞻解读（长文本，详情面板正文）。
        importance: 上游重要级 ``1~4``；缺失为 ``None``（由服务层归一化为 ``0``）。
        country / country_id: 国家中文名 / 国家代码。
        wscn_ticker: 宏观指标代码（仅 ``FD`` 有值），非个股代码。
        actual / forecast / previous / revised: 经济数据四值（仅 ``FD``）。
        flag_uri: 国旗图 URL。
        uri: 原文链接（``FE`` 多为空）。
        raw: 原始条目字典，落库时序列化进 raw_payload 便于排查。
    """

    item_id: int
    public_date: Optional[int]
    calendar_type: str
    title: str
    foresight: str
    importance: Optional[int]
    country: str
    country_id: str
    wscn_ticker: str = ""
    actual: str = ""
    forecast: str = ""
    previous: str = ""
    revised: str = ""
    flag_uri: str = ""
    uri: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


class WallstreetcnCalendarFetcher:
    """华尔街见闻财经日历抓取器。

    Args:
        base_url: 接口基址，如 ``https://api-one-wscn.awtmt.com``。
        timeout: 单请求超时（秒），内部收敛到 1~30 秒。
        request_get: 可选的 GET 实现，签名与 ``requests.get`` 一致。
            服务层会传入带 SSRF / DNS 复检的实现；未注入时退化为 ``requests.get``。

    Example::

        fetcher = WallstreetcnCalendarFetcher()
        countries = fetcher.fetch_countries()
        events = fetcher.fetch_range(1788192000, 1790351999)
    """

    #: 国家字典路径
    _COUNTRIES_PATH = "/apiv1/finance/countries"
    #: 日历事件路径
    _MACRODATAS_PATH = "/apiv1/finance/macrodatas"

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 8.0,
        request_get: Optional[Callable[..., Any]] = None,
    ):
        self.base_url = (base_url or _DEFAULT_BASE_URL).strip().rstrip("/")
        self.timeout = max(1.0, min(float(timeout), 30.0))
        self._request_get = request_get or requests.get

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def fetch_countries(self) -> List[CalendarCountryEntry]:
        """拉取国家字典（低频稳定数据，服务层做进程内缓存）。"""
        url = f"{self.base_url}{self._COUNTRIES_PATH}"
        payload = self._fetch_json(url)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise CalendarFetchError("invalid calendar countries response: missing data")
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            raise CalendarFetchError("invalid calendar countries response: missing items")

        countries: List[CalendarCountryEntry] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            country_id = str(raw_item.get("country_id") or "").strip()
            if not country_id:
                continue
            countries.append(CalendarCountryEntry(
                country_id=country_id,
                country_name=str(raw_item.get("country_name") or "").strip(),
                currency=str(raw_item.get("currency") or "").strip(),
                currency_name=str(raw_item.get("currency_name") or "").strip(),
                flag_uri=str(raw_item.get("flag_uri") or "").strip(),
            ))
        return countries

    def fetch_range(self, start_ts: int, end_ts: int) -> List[CalendarEventEntry]:
        """拉取 ``[start_ts, end_ts]``（秒级 UTC，含端点）区间内的日历事件。

        Args:
            start_ts: 起始时间戳（秒级 UTC）。
            end_ts: 结束时间戳（秒级 UTC，含）。

        Returns:
            解析后的事件列表（已过滤无 ID 的脏数据）。
        """
        if start_ts < 0 or end_ts < start_ts:
            raise CalendarFetchError(
                f"invalid calendar time range: start={start_ts} end={end_ts}"
            )
        url = f"{self.base_url}{self._MACRODATAS_PATH}?start={start_ts}&end={end_ts}"
        payload = self._fetch_json(url)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise CalendarFetchError("invalid calendar response: missing data")
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            raise CalendarFetchError("invalid calendar response: missing items")

        events: List[CalendarEventEntry] = []
        for raw_item in raw_items:
            entry = self._parse_item(raw_item)
            if entry is not None:
                events.append(entry)
        return events

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _fetch_json(self, url: str) -> Any:
        """GET 请求并解码 JSON；统一收敛网络/结构异常为领域异常。"""
        headers = {
            "User-Agent": _DEFAULT_USER_AGENT,
            "Referer": _DEFAULT_REFERER,
            "Accept": "application/json",
        }
        try:
            response = self._request_get(
                url, headers=headers, timeout=self.timeout, allow_redirects=False
            )
        except Exception as exc:  # noqa: BLE001 - 统一收敛为领域异常
            raise CalendarFetchError(f"calendar request failed: {exc}") from exc

        try:
            status_code = int(getattr(response, "status_code", 200) or 200)
            if status_code != 200:
                raise CalendarFetchError(f"calendar upstream returned HTTP {status_code}")
            payload = self._decode_json(response)
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

        if not isinstance(payload, dict):
            raise CalendarFetchError("invalid calendar response: expected object")
        code = payload.get("code")
        if code != _SUCCESS_CODE:
            message = str(payload.get("message") or "unknown upstream error")
            raise CalendarFetchError(
                f"calendar upstream error: code={code} message={message}"
            )
        return payload

    @staticmethod
    def _decode_json(response: Any) -> Any:
        """按 JSON 解码响应体：优先流式读取（限制体积），否则退化读取 content。"""
        iter_content = getattr(response, "iter_content", None)
        if callable(iter_content):
            chunks: List[bytes] = []
            total = 0
            for chunk in iter_content(chunk_size=8192):
                if not chunk:
                    continue
                total += len(chunk)
                if total > _MAX_RESPONSE_BYTES:
                    raise CalendarFetchError("calendar response is too large")
                chunks.append(chunk)
            content = b"".join(chunks)
        else:
            content = (getattr(response, "content", b"") or b"")[: _MAX_RESPONSE_BYTES + 1]
            if len(content) > _MAX_RESPONSE_BYTES:
                raise CalendarFetchError("calendar response is too large")
        try:
            return json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CalendarFetchError(f"invalid calendar JSON response: {exc}") from exc

    @classmethod
    def _parse_item(cls, raw_item: Any) -> Optional[CalendarEventEntry]:
        """解析单条日历事件；缺少 ID 或标题的条目直接丢弃。"""
        if not isinstance(raw_item, dict):
            return None

        item_id = cls._coerce_int(raw_item.get("id"))
        if item_id is None:
            return None

        title = cls._clean_text(str(raw_item.get("title") or ""))
        foresight = cls._clean_text(str(raw_item.get("foresight") or ""))
        if not title and not foresight:
            return None

        return CalendarEventEntry(
            item_id=int(item_id),
            public_date=cls._coerce_int(raw_item.get("public_date")),
            calendar_type=str(raw_item.get("calendar_type") or "").strip(),
            title=title,
            foresight=foresight,
            # importance 缺失时保留 None，由服务层归一化为业务量纲 0（无），
            # 不可在此兜底为 1（「没告诉我」≠「这是普通的」）
            importance=cls._coerce_int(raw_item.get("importance")),
            country=str(raw_item.get("country") or "").strip(),
            country_id=str(raw_item.get("country_id") or "").strip(),
            wscn_ticker=str(raw_item.get("wscn_ticker") or "").strip(),
            actual=str(raw_item.get("actual") or "").strip(),
            forecast=str(raw_item.get("forecast") or "").strip(),
            previous=str(raw_item.get("previous") or "").strip(),
            revised=str(raw_item.get("revised") or "").strip(),
            flag_uri=str(raw_item.get("flag_uri") or "").strip(),
            uri=str(raw_item.get("uri") or "").strip(),
            raw=dict(raw_item),
        )

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        """把上游字段安全转成 int；不可转换时返回 None。"""
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clean_text(value: str) -> str:
        """清洗文本：先剥离 HTML 标签，再折叠空白字符。"""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()
