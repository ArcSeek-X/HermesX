# -*- coding: utf-8 -*-
"""
@file: intelligence.py
@description: 情报数据源与资讯接口契约：数据源/模板的创建与列表、情报抓取与测试、实时财经快讯（Live News）及财经日历（Calendar）；由 api.v1.endpoints.intelligence 返回，快讯与日历在官方源失败时降级到 NewsNow。
@author: Lensgcx (GaoCangxiong)

Intelligence source API schemas.

Defines source and template management payloads, fetch/test results,
live-news channel and item models with cursor pagination, and the
financial-calendar event and dictionary responses.

情报与资讯接口的 Pydantic 模型。快讯与日历共享降级语义：degraded 为 True 时表示数据来自兜底源，前端需隐藏依赖上游特性的交互（如「只看重要」开关）。
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# 情报源类型取值：rss / atom 为标准订阅格式，newsnow 为聚合兜底源。
SourceTypeValue = Literal["rss", "atom", "newsnow"]
# 作用范围取值：symbol 个股 / market 全市场 / sector 板块。
ScopeTypeValue = Literal["symbol", "market", "sector"]
# 市场取值：cn / hk / us / jp / kr / tw / global，global 表示跨市场综合源。
MarketValue = Literal["cn", "hk", "us", "jp", "kr", "tw", "global"]


class IntelligenceSourceCreateRequest(BaseModel):
    """创建情报数据源的请求体。

    使用场景：管理员新增自定义 RSS/Atom/NewsNow 源；默认启用、作用于市场维度、市场为 cn，降低最小配置成本。

    @author: Lensgcx (GaoCangxiong)
    """
    # 新建数据源名称，长度 1~100，必填。
    name: str = Field(..., min_length=1, max_length=100)
    # 订阅地址，长度 1~1000，必填。
    url: str = Field(..., min_length=1, max_length=1000)
    # 解析类型，默认 rss。
    source_type: SourceTypeValue = "rss"
    # 创建后是否立即启用，默认 True。
    enabled: bool = True
    # 作用范围类型，默认 market。
    scope_type: ScopeTypeValue = "market"
    # 作用范围取值（代码、市场或板块标识）；market 维度下可为 None。
    scope_value: Optional[str] = Field(None, max_length=64)
    # 市场标识，默认 cn。
    market: MarketValue = "cn"
    # 数据源用途说明；未填写时为 None。
    description: Optional[str] = None


class IntelligenceSourceTemplateCreateRequest(BaseModel):
    """按模板创建数据源的请求体。

    使用场景：从内置模板批量建源；仅列出可覆盖项，url 与 source_type 来自模板本身，不允许请求体改写。

    @author: Lensgcx (GaoCangxiong)
    """
    # 覆盖模板默认名称；未提供时沿用模板名。
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    # 覆盖默认启用状态；未提供时沿用模板值。
    enabled: Optional[bool] = None
    # 覆盖作用范围类型；未提供时沿用模板值。
    scope_type: Optional[ScopeTypeValue] = None
    # 作用范围取值（代码、市场或板块标识）；market 维度下可为 None。
    scope_value: Optional[str] = Field(None, max_length=64)
    # 覆盖市场标识；未提供时沿用模板值。
    market: Optional[MarketValue] = None
    # 数据源用途说明；未填写时为 None。
    description: Optional[str] = None


class IntelligenceDefaultSourcesCreateRequest(BaseModel):
    """创建默认数据源集合的请求体。

    使用场景：初始化内置源；enabled 为空时采用模板默认值。

    @author: Lensgcx (GaoCangxiong)
    """
    # 统一设置新建默认源的启用状态；未提供时采用各模板默认值。
    enabled: Optional[bool] = None


class IntelligenceSourceItem(BaseModel):
    """情报数据源条目。

    使用场景：数据源管理页；附带最近一次抓取状态与错误，便于不查日志即可定位失效源。

    @author: Lensgcx (GaoCangxiong)
    """
    # 数据源主键，供更新、删除与测试定位。
    id: int
    # 数据源或模板名称，长度 1~100；用于列表展示与去重提示。
    name: str
    # 数据源类型 rss / atom / newsnow，决定解析方式。
    source_type: str
    # 数据源地址或情报原文链接，长度上限 1000（日历/快讯类无显式约束）。
    url: str
    # 是否启用该数据源/集合；禁用后不再参与定时抓取。
    enabled: bool
    # 作用范围类型 symbol 个股 / market 市场 / sector 板块。
    scope_type: str
    # 作用范围取值（代码、市场或板块标识）；market 维度下可为 None。
    scope_value: Optional[str] = None
    # 市场标识 cn / hk / us / jp / kr / tw / global。
    market: str
    # 数据源用途说明；未填写时为 None。
    description: Optional[str] = None
    # 最近一次抓取结果状态（成功/失败）；从未抓取为 None。
    last_status: Optional[str] = None
    # 最近一次抓取失败原因；成功或从未抓取为 None。
    last_error: Optional[str] = None
    # 最近一次成功抓取时间；从未抓取为 None。
    last_fetched_at: Optional[str] = None
    # 记录创建时间字符串；历史数据可能缺失。
    created_at: Optional[str] = None
    # 记录最后更新时间字符串；历史数据可能缺失。
    updated_at: Optional[str] = None


class IntelligenceSourceTemplateItem(BaseModel):
    """情报数据源模板条目。

    使用场景：模板选择列表；不含启用状态与抓取状态，因为模板本身不会被调度。

    @author: Lensgcx (GaoCangxiong)
    """
    # 模板稳定标识，创建时据此定位模板定义。
    template_id: str
    # 数据源或模板名称，长度 1~100；用于列表展示与去重提示。
    name: str
    # 数据源类型 rss / atom / newsnow，决定解析方式。
    source_type: str
    # 数据源地址或情报原文链接，长度上限 1000（日历/快讯类无显式约束）。
    url: str
    # 作用范围类型 symbol 个股 / market 市场 / sector 板块。
    scope_type: str
    # 作用范围取值（代码、市场或板块标识）；market 维度下可为 None。
    scope_value: Optional[str] = None
    # 市场标识 cn / hk / us / jp / kr / tw / global。
    market: str
    # 数据源用途说明；未填写时为 None。
    description: Optional[str] = None


class IntelligenceSourceListResponse(BaseModel):
    """情报数据源列表响应体。

    使用场景：数据源管理页分页拉取。

    @author: Lensgcx (GaoCangxiong)
    """
    # 当前页数据源列表；无数据为空列表。
    items: List[IntelligenceSourceItem] = Field(default_factory=list)
    # 符合条件的记录总数，用于分页或空态判断。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int


class IntelligenceSourceTemplateListResponse(BaseModel):
    """情报数据源模板列表响应体。

    使用场景：模板选择弹窗一次性返回全部模板，故只有 total 无分页参数。

    @author: Lensgcx (GaoCangxiong)
    """
    # 全部可用模板列表；一次性返回，默认空列表。
    items: List[IntelligenceSourceTemplateItem] = Field(default_factory=list)
    # 模板总数，等于 items 长度。
    total: int


class IntelligenceDefaultSourceResult(BaseModel):
    """默认数据源创建结果。

    使用场景：批量初始化时逐项说明是新建还是已存在，created=False 时 source 为已有配置。

    @author: Lensgcx (GaoCangxiong)
    """
    # 本次是否新建；False 表示该默认源已存在。
    created: bool
    # 新建或已存在的数据源配置。
    source: IntelligenceSourceItem


class IntelligenceDefaultSourceCreateResponse(BaseModel):
    """默认数据源集合创建响应体。

    使用场景：初始化端点返回逐项结果与汇总数量；created_count 可能小于 total（部分已存在）。

    @author: Lensgcx (GaoCangxiong)
    """
    # 逐项创建结果列表，默认空列表。
    items: List[IntelligenceDefaultSourceResult] = Field(default_factory=list)
    # 本次实际新建的源数量，可能小于 total。
    created_count: int
    # 处理的默认源模板总数。
    total: int


class IntelligenceItem(BaseModel):
    """情报条目。

    使用场景：情报列表与检索结果；保留来源与范围字段，便于按市场、板块或个股过滤展示。

    @author: Lensgcx (GaoCangxiong)
    """
    # 情报条目主键，用于去重与详情定位。
    id: int
    # 来源数据源主键；来源被删除或外部导入时为 None。
    source_id: Optional[int] = None
    # 来源名称快照，避免数据源改名后历史条目语义漂移。
    source_name: Optional[str] = None
    # 数据源类型 rss / atom / newsnow，决定解析方式。
    source_type: str
    # 标题；快讯标题常为空字符串，前端应回退展示正文。
    title: str
    # 内容摘要；上游未提供时为 None。
    summary: Optional[str] = None
    # 数据源地址或情报原文链接，长度上限 1000（日历/快讯类无显式约束）。
    url: str
    # 来源显示名；未提供时为 None。
    source: Optional[str] = None
    # 上游发布时间字符串；缺失时为 None。
    published_at: Optional[str] = None
    # 本次抓取时间字符串；未抓取成功时为 None。
    fetched_at: Optional[str] = None
    # 作用范围类型 symbol 个股 / market 市场 / sector 板块。
    scope_type: str
    # 作用范围取值（代码、市场或板块标识）；market 维度下可为 None。
    scope_value: Optional[str] = None
    # 市场标识 cn / hk / us / jp / kr / tw / global。
    market: str


class IntelligenceSampleItem(BaseModel):
    """情报样本条目。

    使用场景：数据源测试与抓取 dry-run 的样例预览；只含展示所需字段，不写库。

    @author: Lensgcx (GaoCangxiong)
    """
    # 标题；快讯标题常为空字符串，前端应回退展示正文。
    title: str
    # 内容摘要；上游未提供时为 None。
    summary: Optional[str] = None
    # 数据源地址或情报原文链接，长度上限 1000（日历/快讯类无显式约束）。
    url: str
    # 样例的来源显示名；未提供时为 None。
    source: Optional[str] = None
    # 上游发布时间字符串；缺失时为 None。
    published_at: Optional[str] = None


class IntelligenceItemListResponse(BaseModel):
    """情报条目列表响应体。

    使用场景：情报流分页拉取。

    @author: Lensgcx (GaoCangxiong)
    """
    # 当前页情报条目列表；无数据为空列表。
    items: List[IntelligenceItem] = Field(default_factory=list)
    # 符合条件的记录总数，用于分页或空态判断。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int


class IntelligenceFetchResponse(BaseModel):
    """情报抓取响应体。

    使用场景：手动或定时抓取结果汇总；dry_run=True 时只给 sample_items 不写库，results 按源展开明细。

    @author: Lensgcx (GaoCangxiong)
    """
    # 本次抓取或测试是否成功；失败原因见 error。
    ok: bool
    # 单源抓取时的数据源 ID；全量抓取为 None。
    source_id: Optional[int] = None
    # 本次参与抓取的数据源数量；单源抓取可为 None。
    source_count: Optional[int] = None
    # 本次抓取或新入库的条数；重复条目不计入。
    fetched_count: Optional[int] = None
    # 实际入库的新条目数；dry-run 时为 0 或 None。
    saved_count: Optional[int] = None
    # 按保留策略清理掉的旧条目数；未执行清理为 None。
    retention_deleted: Optional[int] = None
    # 是否为试抓取；为 True 时不写库，仅返回样例。
    dry_run: Optional[bool] = None
    # 抓取/测试的样例条目列表，默认空列表；dry-run 时只返回该字段不写库。
    sample_items: List[IntelligenceSampleItem] = Field(default_factory=list)
    # 按数据源展开的抓取明细列表；单源抓取可为 None。
    results: Optional[List[dict]] = None
    # 整体失败原因；成功时为 None。
    error: Optional[str] = None


class IntelligenceSourceTestResponse(BaseModel):
    """情报数据源测试响应体。

    使用场景：保存数据源前验证 URL 与解析规则；source 回传归一化后的配置，便于确认实际生效值。

    @author: Lensgcx (GaoCangxiong)
    """
    # 本次抓取或测试是否成功；失败原因见 error。
    ok: bool
    # 归一化后的数据源配置，供调用方确认实际生效值。
    source: dict
    # 测试抓取解析出的条目数，不代表已入库。
    fetched_count: int
    # 抓取/测试的样例条目列表，默认空列表；dry-run 时只返回该字段不写库。
    sample_items: List[IntelligenceSampleItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 实时财经快讯（Live News）相关模型
#
# 数据来源为华尔街见闻 7x24 快讯接口，失败时降级到 NewsNow 聚合源。
# 降级后只有「要闻」单频道，且无重要级（importance 为 None），
# 前端据此隐藏「只看重要的」开关与重要标签。详见 documents/product/行情资讯/live-news.md。
# ---------------------------------------------------------------------------


class LiveNewsChannel(BaseModel):
    """快讯频道（前端 Tab 的数据源）。

    使用场景：频道列表接口返回可切换的 Tab；降级模式下只有「要闻」一项。

    Attributes:
        value: 频道 ID，同时作为接口查询入参，如 ``a-stock-channel``。
        label: 频道展示文案，如 ``A股``。

    @author: Lensgcx (GaoCangxiong)
    """

    # 频道 ID，如 a-stock-channel，同时作为列表查询参数。
    value: str
    # 频道展示文案，如「A股」。
    label: str


class LiveNewsItem(BaseModel):
    """单条快讯。

    使用场景：快讯列表元素，按 display_time 倒序展示；上游缺标题或作者时以空值表达，避免前端因字段缺失渲染失败。

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

    @author: Lensgcx (GaoCangxiong)
    """

    # 上游快讯 ID，全局唯一，用于去重与游标分页。
    id: int
    # 快讯标题；常为空字符串，前端需回退展示 content。
    title: str = ""
    # 快讯正文纯文本，默认空字符串。
    content: str = ""
    # 发布时间，秒级 Unix 时间戳；缺失时为 None，前端不应按毫秒解析。
    display_time: Optional[int] = None
    # 上游重要级，默认 1（普通）；2=重要、3=非常重要，降级源下可能恒为 1。
    score: int = 1
    # 是否达到配置的重要阈值，默认 False；降级源无重要级时恒为 False。
    important: bool = False
    # 上游原始频道值列表，一条快讯可属于多个频道；默认空列表。
    channels: List[str] = Field(default_factory=list)
    # 快讯原文链接，默认空字符串。
    uri: str = ""
    # 作者显示名；上游未提供时为 None。
    author: Optional[str] = None


class LiveNewsChannelsResponse(BaseModel):
    """频道列表响应。

    使用场景：初始化快讯页 Tab；degraded 决定前端是否隐藏「只看重要」开关与多频道筛选。

    Attributes:
        channels: 可用频道列表；降级模式下只返回「要闻」一项。
        degraded: 是否处于降级模式（官方源不可用，数据来自 NewsNow 兜底源）。
        source: 当前实际生效的数据源标识，``wallstreetcn`` 或 ``newsnow``。

    @author: Lensgcx (GaoCangxiong)
    """

    # 可用频道对象列表；降级模式下只有「要闻」一项，默认空列表。
    channels: List[LiveNewsChannel] = Field(default_factory=list)
    # 是否处于降级模式；为 True 时数据来自兜底源，前端需隐藏依赖上游特性的交互。
    degraded: bool = False
    # 实际生效的数据源：wallstreetcn 官方源 / newsnow 兜底源，默认前者。
    source: str = "wallstreetcn"


class LiveNewsListResponse(BaseModel):
    """快讯列表响应。

    使用场景：游标分页的快讯流；server_time 供前端校准本地时钟，避免客户端时间偏差导致时间显示错乱。

    Attributes:
        items: 快讯列表，按发布时间倒序。
        next_cursor: 下一页游标；为 None 表示已无更多数据。
        degraded: 是否降级数据。
        server_time: 服务端当前时间戳（秒），供前端校准本地时间。
        total: 当前过滤条件下的总条数，用于空态判断。

    @author: Lensgcx (GaoCangxiong)
    """

    # 按发布时间倒序的快讯列表，默认空列表。
    items: List[LiveNewsItem] = Field(default_factory=list)
    # 下一页游标；None 表示已无更多数据，前端据此停止加载。
    next_cursor: Optional[str] = None
    # 是否处于降级模式；为 True 时数据来自兜底源，前端需隐藏依赖上游特性的交互。
    degraded: bool = False
    # 服务端当前秒级时间戳，供前端校准本地时钟。
    server_time: int
    # 当前过滤条件下的总条数，默认 0，用于空态判断。
    total: int = 0


class LiveNewsRefreshRequest(BaseModel):
    """手动刷新快讯请求。

    使用场景：运维或用户主动触发抓取；不传 channels 表示刷新全部频道。

    Attributes:
        channels: 待刷新的频道 ID 列表；为空表示刷新全部 8 个频道。

    @author: Lensgcx (GaoCangxiong)
    """

    # 待刷新的频道 ID 列表；None 或空列表表示刷新全部 8 个频道。
    channels: Optional[List[str]] = None


class LiveNewsRefreshError(BaseModel):
    """单个频道刷新失败的详情（fail-open，不影响其他频道）。

    使用场景：部分频道抓取失败时逐项回报，整体响应仍为成功，避免单频道故障拖垮全部刷新。

    @author: Lensgcx (GaoCangxiong)
    """

    # 刷新失败的频道 ID。
    channel: str
    # 该频道的失败原因；单频道失败不影响其他频道（fail-open）。
    error: str


class LiveNewsRefreshResponse(BaseModel):
    """手动刷新快讯响应。

    使用场景：刷新端点返回新增条数、降级状态与逐频道错误；重复条目不计入 fetched_count。

    Attributes:
        fetched_count: 本次新入库的条数（重复条目不计入）。
        degraded: 是否走了 NewsNow 降级。
        errors: 各频道失败详情；为空表示全部成功。

    @author: Lensgcx (GaoCangxiong)
    """

    # 本次新入库条数，默认 0；重复条目不计入。
    fetched_count: int = 0
    # 是否处于降级模式；为 True 时数据来自兜底源，前端需隐藏依赖上游特性的交互。
    degraded: bool = False
    # 逐频道失败详情列表；为空表示全部成功。
    errors: List[LiveNewsRefreshError] = Field(default_factory=list)


# 日历分类取值：all 全部 / macro 宏观 / earnings 财报 / ipo 新股 / activity 活动。
CalendarTabValue = Literal["all", "macro", "earnings", "ipo", "activity"]


class CalendarTab(BaseModel):
    """日历分类 Tab（全部 / 宏观 / 财报 / 新股 / 活动）。

    使用场景：财经日历页的分类切换；order 必须与服务端常量一致，否则筛选与展示顺序会错位。

    @author: Lensgcx (GaoCangxiong)
    """

    # 分类 Tab 的取值，受 CalendarTabValue 约束。
    value: CalendarTabValue
    # 分类 Tab 的展示文案。
    label: str
    # 前端 Tab 展示顺序（升序），与服务端常量 _CALENDAR_TABS 一致；改动顺序需同步该常量，否则服务端筛选与前端展示会错位。
    order: int = 0


class CalendarTabsResponse(BaseModel):
    """日历分类 Tab 列表响应。

    使用场景：日历页初始化；降级时仍返回 Tab，但事件内容可能受限。

    @author: Lensgcx (GaoCangxiong)
    """

    # 分类 Tab 列表，默认空列表。
    tabs: List[CalendarTab] = Field(default_factory=list)
    # 是否使用降级数据；为 True 时事件内容可能不完整。
    degraded: bool = False


class CalendarCountry(BaseModel):
    """国家字典条目。

    使用场景：日历按国家筛选与展示国旗；货币等字段以空字符串兜底，避免前端判空分支。

    @author: Lensgcx (GaoCangxiong)
    """

    # 国家稳定标识，作为筛选入参。
    country_id: str
    # 国家展示名称。
    country_name: str
    # 货币代码，默认空字符串而非 None，便于前端直接拼接展示。
    currency: str = ""
    # 货币名称，默认空字符串。
    currency_name: str = ""
    # 国旗图标地址；缺失时为空字符串。
    flag_uri: str = ""


class CalendarCountriesResponse(BaseModel):
    """国家字典响应。

    使用场景：国家筛选下拉的数据源。

    @author: Lensgcx (GaoCangxiong)
    """

    # 国家字典列表，默认空列表。
    items: List[CalendarCountry] = Field(default_factory=list)
    # 是否处于降级模式；为 True 时数据来自兜底源，前端需隐藏依赖上游特性的交互。
    degraded: bool = False


class CalendarEvent(BaseModel):
    """单条日历事件（统一业务量纲，详见 documents/product/行情资讯/Live-calendar.md §7.3）。

    使用场景：月视图与列表展示；actual / forecast / previous 统一为字符串，保留上游的单位与「--」等占位表达，不强制数值化。

    @author: Lensgcx (GaoCangxiong)
    """

    # 上游事件 ID，用于去重与详情定位。
    id: int
    # 事件稳定键，跨刷新保持同一事件的身份。
    key: str
    # 事件开始时间，秒级 Unix 时间戳；前端按此归入日期格子。
    start_at: int
    # 标题；快讯标题常为空字符串，前端应回退展示正文。
    title: str = ""
    # 短标题，用于日历格子的紧凑展示，默认空字符串。
    short_title: str = ""
    # 事件补充说明，默认空字符串。
    summary: str = ""
    # 上游事件类型码，默认 FE（财经事件）。
    calendar_type: str = "FE"
    # 事件所属分类 Tab 列表，默认空列表；一个事件可出现在多个 Tab。
    tab_keys: List[CalendarTabValue] = Field(default_factory=list)
    # 重要级，默认 0（普通）；具体分档由上游口径决定。
    importance: int = 0
    # 国家展示名称，默认空字符串。
    country: str = ""
    # 国家标识，用于与国家字典关联，默认空字符串。
    country_id: str = ""
    # 国旗图标地址，默认空字符串。
    flag_uri: str = ""
    # 实际值，字符串保留单位与占位符，默认空字符串。
    actual: str = ""
    # 预测值，字符串保留单位与占位符，默认空字符串。
    forecast: str = ""
    # 前值，字符串保留单位与占位符，默认空字符串。
    previous: str = ""
    # 是否全天事件，默认 False；全天事件不应按小时定位。
    is_all_day: bool = False
    # 事件来源链接，默认空字符串。
    source_uri: str = ""


class CalendarMonthResponse(BaseModel):
    """月度日历事件响应。

    使用场景：按月拉取日历；server_time 供前端校准时间，source 标明本次实际使用的数据源。

    @author: Lensgcx (GaoCangxiong)
    """

    # 当月事件列表，默认空列表。
    items: List[CalendarEvent] = Field(default_factory=list)
    # 服务端当前秒级时间戳，供前端校准本地时钟。
    server_time: int
    # 当月事件总数，默认 0。
    total: int = 0
    # 是否处于降级模式；为 True 时数据来自兜底源，前端需隐藏依赖上游特性的交互。
    degraded: bool = False
    # 实际生效的数据源标识，默认 wallstreetcn；降级时为 newsnow。
    source: str = "wallstreetcn"


class CalendarRefreshRequest(BaseModel):
    """手动刷新日历请求。

    使用场景：按年月主动抓取；年份限制 2000~2100 防止越界请求打到上游。

    @author: Lensgcx (GaoCangxiong)
    """

    # 待刷新年份，范围 2000~2100，防止越界请求打到上游。
    year: int = Field(..., ge=2000, le=2100)
    # 待刷新月份，范围 1~12。
    month: int = Field(..., ge=1, le=12)


class CalendarRefreshResponse(BaseModel):
    """手动刷新日历响应。

    使用场景：刷新后返回新增条数与降级状态；errors 以字符串列表给出失败原因，部分失败不影响整体成功。

    @author: Lensgcx (GaoCangxiong)
    """

    # 本次新入库事件数，默认 0；重复事件不计入。
    fetched_count: int = 0
    # 是否处于降级模式；为 True 时数据来自兜底源，前端需隐藏依赖上游特性的交互。
    degraded: bool = False
    # 失败原因字符串列表；部分失败不影响整体成功，默认空列表。
    errors: List[str] = Field(default_factory=list)
