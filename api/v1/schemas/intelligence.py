# -*- coding: utf-8 -*-
"""Intelligence source API schemas."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SourceTypeValue = Literal["rss", "atom", "newsnow"]
ScopeTypeValue = Literal["symbol", "market", "sector"]
MarketValue = Literal["cn", "hk", "us", "jp", "kr", "tw", "global"]


class IntelligenceSourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=1000)
    source_type: SourceTypeValue = "rss"
    enabled: bool = True
    scope_type: ScopeTypeValue = "market"
    scope_value: Optional[str] = Field(None, max_length=64)
    market: MarketValue = "cn"
    description: Optional[str] = None


class IntelligenceSourceTemplateCreateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    enabled: Optional[bool] = None
    scope_type: Optional[ScopeTypeValue] = None
    scope_value: Optional[str] = Field(None, max_length=64)
    market: Optional[MarketValue] = None
    description: Optional[str] = None


class IntelligenceDefaultSourcesCreateRequest(BaseModel):
    enabled: Optional[bool] = None


class IntelligenceSourceItem(BaseModel):
    id: int
    name: str
    source_type: str
    url: str
    enabled: bool
    scope_type: str
    scope_value: Optional[str] = None
    market: str
    description: Optional[str] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    last_fetched_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class IntelligenceSourceTemplateItem(BaseModel):
    template_id: str
    name: str
    source_type: str
    url: str
    scope_type: str
    scope_value: Optional[str] = None
    market: str
    description: Optional[str] = None


class IntelligenceSourceListResponse(BaseModel):
    items: List[IntelligenceSourceItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class IntelligenceSourceTemplateListResponse(BaseModel):
    items: List[IntelligenceSourceTemplateItem] = Field(default_factory=list)
    total: int


class IntelligenceDefaultSourceResult(BaseModel):
    created: bool
    source: IntelligenceSourceItem


class IntelligenceDefaultSourceCreateResponse(BaseModel):
    items: List[IntelligenceDefaultSourceResult] = Field(default_factory=list)
    created_count: int
    total: int


class IntelligenceItem(BaseModel):
    id: int
    source_id: Optional[int] = None
    source_name: Optional[str] = None
    source_type: str
    title: str
    summary: Optional[str] = None
    url: str
    source: Optional[str] = None
    published_at: Optional[str] = None
    fetched_at: Optional[str] = None
    scope_type: str
    scope_value: Optional[str] = None
    market: str


class IntelligenceSampleItem(BaseModel):
    title: str
    summary: Optional[str] = None
    url: str
    source: Optional[str] = None
    published_at: Optional[str] = None


class IntelligenceItemListResponse(BaseModel):
    items: List[IntelligenceItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class IntelligenceFetchResponse(BaseModel):
    ok: bool
    source_id: Optional[int] = None
    source_count: Optional[int] = None
    fetched_count: Optional[int] = None
    saved_count: Optional[int] = None
    retention_deleted: Optional[int] = None
    dry_run: Optional[bool] = None
    sample_items: List[IntelligenceSampleItem] = Field(default_factory=list)
    results: Optional[List[dict]] = None
    error: Optional[str] = None


class IntelligenceSourceTestResponse(BaseModel):
    ok: bool
    source: dict
    fetched_count: int
    sample_items: List[IntelligenceSampleItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 实时财经快讯（Live News）相关模型
#
# 数据来源为华尔街见闻 7x24 快讯接口，失败时降级到 NewsNow 聚合源。
# 降级后只有「要闻」单频道，且无重要级（importance 为 None），
# 前端据此隐藏「只看重要的」开关与重要标签。详见 docs/live-news.md。
# ---------------------------------------------------------------------------


class LiveNewsChannel(BaseModel):
    """快讯频道（前端 Tab 的数据源）。

    Attributes:
        value: 频道 ID，同时作为接口查询入参，如 ``a-stock-channel``。
        label: 频道展示文案，如 ``A股``。
    """

    value: str
    label: str


class LiveNewsItem(BaseModel):
    """单条快讯。

    Attributes:
        id: 快讯 ID（上游 id），全局唯一。
        title: 标题；快讯常为空字符串，前端应回退展示 content。
        content: 正文纯文本。
        display_time: 发布时间（**秒级** Unix 时间戳）。
        score: 上游重要级，1=普通 / 2=重要 / 3=非常重要。
        important: 是否重要，等价于 ``score >= 阈值``（阈值由配置决定）。
        channels: 所属频道（上游原始值），一条快讯可属于多个频道。
        uri: 原文链接，形如 ``https://wallstreetcn.com/livenews/<id>``。
        author: 作者显示名，可能为空。
    """

    id: int
    title: str = ""
    content: str = ""
    display_time: Optional[int] = None
    score: int = 1
    important: bool = False
    channels: List[str] = Field(default_factory=list)
    uri: str = ""
    author: Optional[str] = None


class LiveNewsChannelsResponse(BaseModel):
    """频道列表响应。

    Attributes:
        channels: 可用频道列表；降级模式下只返回「要闻」一项。
        degraded: 是否处于降级模式（官方源不可用，数据来自 NewsNow 兜底源）。
        source: 当前实际生效的数据源标识，``wallstreetcn`` 或 ``newsnow``。
    """

    channels: List[LiveNewsChannel] = Field(default_factory=list)
    degraded: bool = False
    source: str = "wallstreetcn"


class LiveNewsListResponse(BaseModel):
    """快讯列表响应。

    Attributes:
        items: 快讯列表，按发布时间倒序。
        next_cursor: 下一页游标；为 None 表示已无更多数据。
        degraded: 是否降级数据。
        server_time: 服务端当前时间戳（秒），供前端校准本地时间。
        total: 当前过滤条件下的总条数，用于空态判断。
    """

    items: List[LiveNewsItem] = Field(default_factory=list)
    next_cursor: Optional[str] = None
    degraded: bool = False
    server_time: int
    total: int = 0


class LiveNewsRefreshRequest(BaseModel):
    """手动刷新快讯请求。

    Attributes:
        channels: 待刷新的频道 ID 列表；为空表示刷新全部 8 个频道。
    """

    channels: Optional[List[str]] = None


class LiveNewsRefreshError(BaseModel):
    """单个频道刷新失败的详情（fail-open，不影响其他频道）。"""

    channel: str
    error: str


class LiveNewsRefreshResponse(BaseModel):
    """手动刷新快讯响应。

    Attributes:
        fetched_count: 本次新入库的条数（重复条目不计入）。
        degraded: 是否走了 NewsNow 降级。
        errors: 各频道失败详情；为空表示全部成功。
    """

    fetched_count: int = 0
    degraded: bool = False
    errors: List[LiveNewsRefreshError] = Field(default_factory=list)
