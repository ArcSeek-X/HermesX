# -*- coding: utf-8 -*-
"""股票度量视图 API 请求/响应模型（设计文档 §7）。

契约与前端 ``apps/hrs-web/src/types/stockMetricView.ts`` 严格对齐：
camelCase 平铺行、filterList / sort / 分页同形。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from api.v1.schemas.common import PaginatedResponse


class StockMetricViewFilterItem(BaseModel):
    """单条筛选条件：字段 + 算子 + 值。"""

    field: str
    op: str
    value: Optional[Any] = None


class StockMetricViewSortDef(BaseModel):
    """排序定义（领域语义，field/order）。"""

    field: str = "totalMarketCap"
    order: str = "desc"


class StockMetricViewQueryRequest(BaseModel):
    """POST /query 请求体。"""

    filterList: List[StockMetricViewFilterItem] = Field(default_factory=list)
    sort: StockMetricViewSortDef = Field(
        default_factory=lambda: StockMetricViewSortDef(field="totalMarketCap", order="desc")
    )
    pageNum: int = 1
    pageSize: int = 20
    # 手动刷新时跳过在线快照 TTL 缓存；老客户端不传时保持默认（命中缓存）
    forceRefresh: bool = False


class StockMetricViewRowOut(BaseModel):
    """单行股票度量（camelCase 平铺）。"""

    market: str
    code: str
    name: str
    price: Optional[float] = None
    changePct: Optional[float] = None
    volume: Optional[float] = None
    relativeVolume: Optional[float] = None
    totalMarketCap: Optional[float] = None
    peRatioTTM: Optional[float] = None
    epsDiluted: Optional[float] = None
    epsGrowthTtmYoyPct: Optional[float] = None
    dividendYieldPct: Optional[float] = None
    industry: Optional[str] = None
    analystRating: Optional[float] = None


class StockMetricViewQueryResponse(PaginatedResponse):
    """POST /query 响应：分页包装 + 离线基准日 / 在线快照时刻 / 警告 / 降级标记。"""

    list: List[StockMetricViewRowOut] = Field(default_factory=list)
    asOfDate: str = ""
    # 本批在线快照的抓取时刻（ISO 8601 带 UTC 偏移）；命中 TTL 缓存 / 沿用旧快照时为
    # 该批缓存数据的写入时刻；全部市场无在线数据时为空串，不伪造当前时刻
    quoteAsOf: str = ""
    warnings: List[str] = Field(default_factory=list)
    degraded: bool = False


class StockMetricViewExportRequest(BaseModel):
    """POST /export 请求体。"""

    filterList: List[StockMetricViewFilterItem] = Field(default_factory=list)
    sort: StockMetricViewSortDef = Field(
        default_factory=lambda: StockMetricViewSortDef(field="totalMarketCap", order="desc")
    )
    headers: Dict[str, str] = Field(default_factory=dict)
    visibleColumns: List[str] = Field(default_factory=list)
    limit: int = 5000
