# -*- coding: utf-8 -*-
"""华尔街见闻「7x24 快讯」抓取器（Live News Fetcher）。

职责边界
--------
本模块**只负责与华尔街见闻快讯接口的 HTTP 交互与原始响应解析**，不承载：

- 落库与去重（由 ``src/services/intelligence_service.py`` 负责）
- SSRF / DNS 校验（由服务层注入安全的 ``request_get`` 回调来提供）
- 数据源降级策略（官方源失败时降级到 NewsNow，由服务层编排）

这样的边界让抓取器可以脱离数据库与配置单独测试，也让服务层能够统一复用
``IntelligenceService`` 已有的 SSRF 防护能力。

接口契约
--------
::

    GET {base_url}/apiv1/content/lives?channel=<频道ID>&limit=<N>[&cursor=<游标>]

    成功响应::

        {
          "code": 20000,
          "message": "OK",
          "data": {
            "items": [ { "id": 3156959, "content_text": "...", "display_time": 1787923008,
                         "score": 1, "channels": ["global-channel"], "uri": "...", ... } ],
            "next_cursor": 1787912832,     # 时间戳，用于向下翻取更早内容
            "polling_cursor": 3156960      # 快讯 id，用于向上轮询拉取最新内容
          }
        }

已知边界（实测结论，详见 docs/live-news.md）
-------------------------------------------
- 8 个频道均可用，但 ``tech-channel`` **独立于 global 主流且更新最慢**，因此必须逐频道抓取，
  不能只抓 ``global-channel`` 再本地过滤。
- 快讯的 ``title`` 经常为空字符串，正文应优先取 ``content_text``。
- ``display_time`` 为**秒级**时间戳；而兜底源 NewsNow 的 ``extra.date`` 为**毫秒级**，
  换算逻辑不在这里，统一由服务层标准化，避免单位混淆。
- ``symbols`` 字段实测恒为空列表，不可用于关联个股标的。
- 上游为滚动窗口，``limit`` 上限约 100，历史数据需持续落库累积，否则永久丢失。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# 成功响应码；非该值一律视为上游异常
_SUCCESS_CODE = 20000

# 单次请求条数上限，防止配置异常导致上游压力过大
_MAX_LIMIT = 100

# 默认请求头：上游对 UA / Referer 有校验，缺失会返回非 20000 响应
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 hermesx-intel/1.0"
)
_DEFAULT_REFERER = "https://wallstreetcn.com/"

# ---------------------------------------------------------------------------
# 频道定义（单一真源：Service / API / 前端 Tab 均以此为准）
# ---------------------------------------------------------------------------
# channel_id 为上游查询入参，scope_value 为落库时使用的短码，label 为前端 Tab 文案。
# 注意：上游 channels 字段中还会出现 xgb / financing / goldc / oil 等更细的内部标记，
# 本期不单独建 Tab，仅在 raw_payload 中留痕备用。
LIVE_NEWS_CHANNELS: Tuple[Dict[str, str], ...] = (
    {"channel_id": "global-channel", "scope_value": "global", "label": "要闻"},
    {"channel_id": "a-stock-channel", "scope_value": "a-stock", "label": "A股"},
    {"channel_id": "us-stock-channel", "scope_value": "us-stock", "label": "美股"},
    {"channel_id": "hk-stock-channel", "scope_value": "hk-stock", "label": "港股"},
    {"channel_id": "forex-channel", "scope_value": "forex", "label": "外汇"},
    {"channel_id": "commodity-channel", "scope_value": "commodity", "label": "商品"},
    {"channel_id": "bond-channel", "scope_value": "bond", "label": "债券"},
    {"channel_id": "tech-channel", "scope_value": "tech", "label": "科技"},
)

# 频道 ID -> 频道定义，便于 O(1) 校验与查找
_CHANNEL_BY_ID: Dict[str, Dict[str, str]] = {item["channel_id"]: item for item in LIVE_NEWS_CHANNELS}

# 落库短码 -> 频道定义（查询时按 scope_value 反查 Tab 元信息）
_CHANNEL_BY_SCOPE_VALUE: Dict[str, Dict[str, str]] = {
    item["scope_value"]: item for item in LIVE_NEWS_CHANNELS
}

# 上游 channels 字段 -> 落库短码的映射；仅保留上述 8 个频道，其余内部标记忽略
_UPSTREAM_CHANNEL_TO_SCOPE_VALUE: Dict[str, str] = {
    item["channel_id"]: item["scope_value"] for item in LIVE_NEWS_CHANNELS
}

# 兜底频道：当快讯的 channels 未命中任何已知频道时，归属到请求频道；
# 若请求频道也未知，则落到「要闻」
_FALLBACK_SCOPE_VALUE = "global"


class LiveNewsFetchError(Exception):
    """快讯抓取失败（网络异常、上游非 20000、响应结构不合法等）。

    服务层会捕获该异常并决定是否降级到 NewsNow。
    """


@dataclass(frozen=True)
class LiveNewsEntry:
    """解析后的单条快讯，与上游客体字段一一对应的中间结构。

    Attributes:
        item_id: 快讯唯一 ID（上游 id），可作为去重键。
        content: 正文纯文本（已剥离 HTML 标签、折叠空白）。
        display_time: 发布时间，**秒级** Unix 时间戳。
        score: 上游重要级，1=普通 / 2=重要 / 3=非常重要；缺失时按 1 处理。
        channels: 上游返回的原始频道列表（形如 ``["global-channel", "xgb"]``）。
        uri: 原文链接，形如 ``https://wallstreetcn.com/livenews/<id>``。
        title: 快讯标题，常为空字符串。
        author: 作者显示名，缺失为 None。
        raw: 原始条目字典，落库时序列化进 raw_payload 便于排查。
    """

    item_id: int
    content: str
    display_time: Optional[int]
    score: int
    channels: Tuple[str, ...] = field(default_factory=tuple)
    uri: str = ""
    title: str = ""
    author: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def scope_values(self) -> Tuple[str, ...]:
        """该条目命中的落库频道短码集合（仅保留 8 个已知频道）。

        一条快讯可同时属于多个频道，落库时会按此拆成多行，
        由唯一约束 ``(source_id, url, scope_type, scope_value, market)`` 保证去重。
        """
        matched = []
        for channel in self.channels:
            scope_value = _UPSTREAM_CHANNEL_TO_SCOPE_VALUE.get(str(channel or "").strip())
            if scope_value and scope_value not in matched:
                matched.append(scope_value)
        return tuple(matched)


class WallstreetcnLiveNewsFetcher:
    """华尔街见闻快讯抓取器。

    Args:
        base_url: 接口基址，如 ``https://api-one.wallstcn.com``。
        timeout: 单频道请求超时（秒），内部会收敛到 1~30 秒。
        request_get: 可选的 GET 实现，签名与 ``requests.get`` 一致。
            服务层会传入带 SSRF / DNS 复检的实现；未注入时退化为 ``requests.get``。

    Example::

        fetcher = WallstreetcnLiveNewsFetcher()
        entries, next_cursor, polling_cursor = fetcher.fetch_channel("a-stock-channel", limit=30)
    """

    #: 接口路径（拼在 base_url 之后）
    _PATH = "/apiv1/content/lives"

    def __init__(
        self,
        base_url: str = "https://api-one.wallstcn.com",
        timeout: float = 8.0,
        request_get: Optional[Callable[..., Any]] = None,
    ):
        self.base_url = (base_url or "https://api-one.wallstcn.com").strip().rstrip("/")
        # 超时收敛在 1~30 秒，避免配置异常导致无限等待或瞬时失败
        self.timeout = max(1.0, min(float(timeout), 30.0))
        self._request_get = request_get or requests.get

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    @staticmethod
    def list_channels() -> List[Dict[str, str]]:
        """返回全部频道定义（浅拷贝，防止调用方误改模块级常量）。"""
        return [dict(item) for item in LIVE_NEWS_CHANNELS]

    @staticmethod
    def is_known_channel(channel_id: str) -> bool:
        """判断频道 ID 是否为受支持的 8 个频道之一。"""
        return str(channel_id or "").strip() in _CHANNEL_BY_ID

    @staticmethod
    def to_scope_value(channel_id: str) -> str:
        """频道 ID -> 落库短码；未知频道回退为 ``global``。"""
        item = _CHANNEL_BY_ID.get(str(channel_id or "").strip())
        return item["scope_value"] if item else _FALLBACK_SCOPE_VALUE

    @staticmethod
    def from_scope_value(scope_value: str) -> Optional[Dict[str, str]]:
        """落库短码 -> 频道定义；未知返回 None。"""
        item = _CHANNEL_BY_SCOPE_VALUE.get(str(scope_value or "").strip())
        return dict(item) if item else None

    def build_url(self, channel_id: str, *, limit: int, cursor: Optional[str] = None) -> str:
        """拼装频道抓取 URL。

        Args:
            channel_id: 频道 ID，如 ``a-stock-channel``。
            limit: 每页条数，收敛到 1~100。
            cursor: 分页游标（上游 ``next_cursor``，时间戳）；为空表示取最新一页。
        """
        safe_limit = max(1, min(int(limit), _MAX_LIMIT))
        query = f"channel={channel_id}&limit={safe_limit}"
        if cursor:
            query = f"{query}&cursor={cursor}"
        return f"{self.base_url}{self._PATH}?{query}"

    def fetch_channel(
        self,
        channel_id: str,
        *,
        limit: int = 30,
        cursor: Optional[str] = None,
    ) -> Tuple[List[LiveNewsEntry], Optional[str], Optional[str]]:
        """抓取单个频道的快讯列表。

        Returns:
            三元组 ``(entries, next_cursor, polling_cursor)``：
            entries 为解析后的快讯列表（已过滤无效条目）；
            next_cursor 为下一页游标（时间戳字符串），无更多时为 None；
            polling_cursor 为实时轮询游标（快讯 id），用于后续拉取增量。

        Raises:
            LiveNewsFetchError: 网络异常、上游非 20000、响应结构不合法。
        """
        if not self.is_known_channel(channel_id):
            raise LiveNewsFetchError(f"unsupported live news channel: {channel_id}")

        url = self.build_url(channel_id, limit=limit, cursor=cursor)
        headers = {
            "User-Agent": _DEFAULT_USER_AGENT,
            "Referer": _DEFAULT_REFERER,
            "Accept": "application/json",
        }
        try:
            response = self._request_get(url, headers=headers, timeout=self.timeout, allow_redirects=False)
        except Exception as exc:  # noqa: BLE001 - 统一收敛为领域异常，避免泄漏底层细节
            raise LiveNewsFetchError(f"live news request failed: {exc}") from exc

        try:
            status_code = int(getattr(response, "status_code", 200) or 200)
            if status_code != 200:
                raise LiveNewsFetchError(f"live news upstream returned HTTP {status_code}")
            payload = self._decode_json(response)
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

        return self.parse_payload(payload, channel_id=channel_id)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    @staticmethod
    def _decode_json(response: Any) -> Any:
        """按 JSON 解码响应体：优先流式读取（限制体积），否则退化读取 content。"""
        max_bytes = 4 * 1024 * 1024
        iter_content = getattr(response, "iter_content", None)
        if callable(iter_content):
            chunks: List[bytes] = []
            total = 0
            for chunk in iter_content(chunk_size=8192):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise LiveNewsFetchError("live news response is too large")
                chunks.append(chunk)
            content = b"".join(chunks)
        else:
            content = (getattr(response, "content", b"") or b"")[: max_bytes + 1]
            if len(content) > max_bytes:
                raise LiveNewsFetchError("live news response is too large")
        try:
            return json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LiveNewsFetchError(f"invalid live news JSON response: {exc}") from exc

    @classmethod
    def parse_payload(
        cls,
        payload: Any,
        *,
        channel_id: str,
    ) -> Tuple[List[LiveNewsEntry], Optional[str], Optional[str]]:
        """解析上游响应体。

        Args:
            payload: 已解码的 JSON 对象。
            channel_id: 当前请求的频道 ID，用于条目未命中已知频道时的兜底归属。

        Returns:
            与 :meth:`fetch_channel` 相同的三元组。

        Raises:
            LiveNewsFetchError: 响应结构不合法或上游返回业务错误码。
        """
        if not isinstance(payload, dict):
            raise LiveNewsFetchError("invalid live news response: expected object")
        code = payload.get("code")
        if code != _SUCCESS_CODE:
            message = str(payload.get("message") or "unknown upstream error")
            raise LiveNewsFetchError(f"live news upstream error: code={code} message={message}")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise LiveNewsFetchError("invalid live news response: missing data")
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            raise LiveNewsFetchError("invalid live news response: missing items")

        fallback_scope = cls.to_scope_value(channel_id)
        entries: List[LiveNewsEntry] = []
        for raw_item in raw_items:
            entry = cls._parse_item(raw_item)
            if entry is not None:
                entries.append(entry)

        next_cursor = cls._stringify_cursor(data.get("next_cursor"))
        polling_cursor = cls._stringify_cursor(data.get("polling_cursor"))
        # 单独的兜底字段仅用于日志排查，实际归属由 service 层按 scope_values 决定
        if fallback_scope and not entries:
            logger.debug("Live news channel %s returned no usable entries", channel_id)
        return entries, next_cursor, polling_cursor

    @classmethod
    def _parse_item(cls, raw_item: Any) -> Optional[LiveNewsEntry]:
        """解析单条快讯；缺少 ID 与正文的条目直接丢弃。"""
        if not isinstance(raw_item, dict):
            return None

        item_id = cls._coerce_int(raw_item.get("id"))
        if item_id is None:
            return None

        # 正文优先取纯文本 content_text，其次从 HTML 的 content 中剥离标签
        content = cls._clean_text(str(raw_item.get("content_text") or ""))
        if not content:
            content = cls._clean_text(str(raw_item.get("content") or ""))
        # 标题常为空；无正文也无标题时该条目无展示价值，丢弃
        title = cls._clean_text(str(raw_item.get("title") or ""))
        if not content and not title:
            return None

        uri = str(raw_item.get("uri") or "").strip()
        if not uri and item_id:
            # 上游偶发缺失 uri 时，按已知的 livenews 规则自行拼装，保证去重键稳定
            uri = f"https://wallstreetcn.com/livenews/{item_id}"

        raw_channels = raw_item.get("channels")
        channels: Tuple[str, ...] = ()
        if isinstance(raw_channels, list):
            channels = tuple(str(item).strip() for item in raw_channels if str(item).strip())

        author = raw_item.get("author")
        author_name = None
        if isinstance(author, dict):
            author_name = str(author.get("display_name") or "").strip() or None

        return LiveNewsEntry(
            item_id=int(item_id),
            content=content,
            display_time=cls._coerce_int(raw_item.get("display_time")),
            # score 缺失或非法时按「普通」处理，避免 None 参与比较
            score=cls._coerce_int(raw_item.get("score")) or 1,
            channels=channels,
            uri=uri,
            title=title,
            author=author_name,
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
    def _stringify_cursor(value: Any) -> Optional[str]:
        """游标统一转成字符串；空值/零值返回 None（表示无更多数据）。"""
        if value is None or value == "" or value == 0:
            return None
        return str(value)

    @staticmethod
    def _clean_text(value: str) -> str:
        """清洗文本：先剥离 HTML 标签，再折叠空白字符。"""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()
