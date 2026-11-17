# -*- coding: utf-8 -*-
"""股票度量视图 API 端点（设计文档 §8）。

``/api/v1/stock-metric/query`` 分页查询；``/api/v1/stock-metric/export`` 导出 CSV。
业务校验异常由服务层以 ``ValueError`` 抛出，端点统一转换为 400。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from api.deps import get_stock_metric_service
from api.v1.errors import api_error
from api.v1.schemas.stock_metric import (
    StockMetricViewExportRequest,
    StockMetricViewQueryRequest,
    StockMetricViewQueryResponse,
)
from src.application.quote.stock_metric_service import StockMetricService

router = APIRouter()


@router.post("/query", response_model=StockMetricViewQueryResponse)
def stock_metric_query(
    payload: StockMetricViewQueryRequest,
    service: StockMetricService = Depends(get_stock_metric_service),
) -> Dict[str, Any]:
    """分页查询股票度量视图。"""
    try:
        return service.query(
            filter_list=payload.filterList,
            sort=payload.sort,
            page_num=payload.pageNum,
            page_size=payload.pageSize,
            force_refresh=payload.forceRefresh,
        )
    except ValueError as exc:
        raise api_error(400, "STOCK_METRIC_INVALID_PARAM", str(exc))


@router.post("/export")
def stock_metric_export(
    payload: StockMetricViewExportRequest,
    service: StockMetricService = Depends(get_stock_metric_service),
) -> Response:
    """导出股票度量视图 CSV（UTF-8 BOM + CRLF）。"""
    try:
        csv_bytes, truncated = service.export(
            filter_list=payload.filterList,
            sort=payload.sort,
            visible_columns=payload.visibleColumns,
            headers=payload.headers,
            limit=payload.limit,
        )
    except ValueError as exc:
        raise api_error(422, "STOCK_METRIC_INVALID_PARAM", str(exc))

    filename = f"stock-metric-view_{date.today().strftime('%Y%m%d')}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if truncated:
        headers["X-Export-Truncated"] = "1"
    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)
