# -*- coding: utf-8 -*-
"""资讯领域外部数据源端口（application 层契约）。

分层说明：``IntelligenceService`` 对 Wallstreetcn 快讯/日历源的依赖经本端口
绑定 ``src/infrastructure/providers/wallstreetcn_news_port.py`` 适配器，由
bootstrap 装配（B4c/S2e 同型）。用例层保留抓取编排（SSRF 校验、降级判定、
异常文案），源实现与 data_provider 细节收纳在适配器内。

``fetch`` 返回上游结果对象（含 ``items``/``next_cursor`` 等字段）而非纯
dataclass 镜像：快讯条目字段集随上游演进，转换层会形成第二份字段契约；
用例层只按 ``.items`` 等公开属性消费，与 MarketSnapshotPort 的 DataFrame
形状例外同理（见 ``application/quote/ports.py``）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from src.domain.search import SearchResponse


@dataclass(frozen=True)
class NewsQuery:
    """资讯抓取请求（与 data_provider ``NewsRequest`` 字段镜像、适配器转换）。"""

    mode: str = "live"
    channel_id: str = "global-channel"
    limit: int = 30
    cursor: Optional[str] = None
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None


class NewsLiveFetchError(RuntimeError):
    """快讯上游抓取失败（适配器转换自 data_provider ``LiveNewsFetchError``）。"""


class NewsCalendarFetchError(RuntimeError):
    """日历上游抓取失败（适配器转换自 data_provider ``CalendarFetchError``）。"""


class NewsSourceHandle(Protocol):
    """一次注入安全请求实现与运行时配置后的资讯源句柄。

    服务层用 ``build_live_news_url`` 先做 SSRF 白名单校验、再 ``fetch``；
    异常以本模块端口异常上抛，降级/转换编排由用例处理。
    """

    def build_live_news_url(
        self, channel_id: str, *, limit: int, cursor: Optional[str] = None
    ) -> str:
        ...

    def fetch(self, query: NewsQuery) -> Any:
        ...


class NewsSourcePort(Protocol):
    """华尔街见闻资讯源端口：频道元数据 + 运行时句柄工厂。"""

    def list_channels(self) -> List[Dict[str, Any]]:
        ...

    def is_known_channel(self, channel_id: str) -> bool:
        ...

    def channel_scope_value(self, channel_id: str) -> str:
        ...

    def create_handle(
        self,
        *,
        request_get: Callable[..., Any],
        live_base_url: str,
        live_timeout: float,
        calendar_base_url: str,
        calendar_timeout: float,
    ) -> NewsSourceHandle:
        ...


@dataclass(frozen=True)
class SearchOptions:
    """检索中性选项（SA2 方案 A）。

    取代 ``SearchService`` 历史上按 ``isinstance(provider, TavilySearchProvider /
    BraveSearchProvider)`` 注入各引擎专有 ``search()`` keyword 的硬耦合：用例层按业务
    意图填充本契约字段，各引擎适配器只读取自身支持的字段、忽略其余（不支持即不消费，
    等价于原 ``isinstance`` 未命中分支）。

    字段来源（见 SA2-0 逐 Provider 语义矩阵）：
    - ``topic``：Tavily 新闻 topic 开关（原 ``search_kwargs["topic"]`` / ``dim['tavily_topic']``）；
    - ``search_lang`` / ``country``：Brave 区域语言偏好（原 ``_brave_search_locale`` 返回）。
    """

    topic: Optional[str] = None
    search_lang: Optional[str] = None
    country: Optional[str] = None


class SearchProviderPort(Protocol):
    """单个搜索引擎适配器的能力端口。

    用例层只依赖这三件公开成员（``name`` / ``is_available`` / ``search``），不感知具体
    引擎类；外部 HTTP/SDK 调用、Key 轮询与健康记账收纳在 ``src/infrastructure`` 的实现
    （SA2-3 下沉）与 ``build_search_service`` 工厂装配（SA2-4）内。
    """

    @property
    def name(self) -> str:
        ...

    @property
    def is_available(self) -> bool:
        ...

    def search(
        self,
        query: str,
        max_results: int = 5,
        days: int = 7,
        options: Optional[SearchOptions] = None,
    ) -> SearchResponse:
        ...


# ---------------------------------------------------------------------------
# 资讯/情报持久化端口（PP-1 持久化收口 Epic：application 不再具体 import
# ``src.repositories.IntelligenceRepository``，改经本端口由 bootstrap 装配 infra 实现。
# 沿用 history/backtest/market_light 的 ``Protocol`` 端口先例。）
# ---------------------------------------------------------------------------

#: ``intelligence_items.scope_value`` 空值哨兵。单一真源落 application 端口：
#: application 不得 import infra model，而 model（infra）反向 import 本端口合法，
#: 故哨兵字符串以本处为权威，model 与仓储均从此处取，避免多份定义漂移。
INTELLIGENCE_ITEM_NULL_SCOPE_VALUE = "__hrs_null_scope__"


class IntelligenceSourceNameConflictError(Exception):
    """资讯源 ``name`` 唯一约束冲突（服务层与仓储层的共享业务异常契约）。

    由 infra 仓储把 ``IntegrityError`` 转换为本异常上抛、application 服务捕获并拼
    文案；异常类型本身收纳在 application 端口，仓储反向 import 合法。
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class IntelligenceRepositoryPort(Protocol):
    """资讯源 / 资讯条目读写端口。

    方法面按 ``IntelligenceService`` 实读实写收敛；返回的持久化对象为会话内可读的
    记录（detached 后仅公开属性可读），故端口以 ``Any``/``Dict`` 描述，避免用例层依赖
    SQLAlchemy ORM 类型。实现落点：``src/infrastructure/persistence/repositories/
    intelligence_repository.py``，由 ``bootstrap.intelligence`` 装配。
    """

    def create_source(self, fields: Dict[str, Any]) -> Any:
        ...

    def get_source(self, source_id: int) -> Any:
        ...

    def get_source_by_name(self, name: str) -> Any:
        ...

    def update_source_enabled(self, source_id: int, enabled: bool) -> None:
        ...

    def update_source_status(
        self,
        source_id: int,
        *,
        status: str,
        error: Optional[str] = None,
        fetched_at: Optional[Any] = None,
    ) -> None:
        ...

    def list_sources(self, **filters: Any) -> Tuple[List[Any], int]:
        ...

    def list_items(self, **filters: Any) -> Tuple[List[Any], int]:
        ...

    def upsert_items(self, items: Any) -> int:
        ...

    def list_live_news_items(self, **filters: Any) -> Tuple[List[Any], int]:
        ...

    def get_live_news_item_by_id(self, item_id: int) -> Any:
        ...

    def count_live_news_items(self, *, scope_value: str) -> int:
        ...

    def list_calendar_events(self, **filters: Any) -> List[Any]:
        ...

    def apply_retention(self, retention_days: int) -> int:
        ...
