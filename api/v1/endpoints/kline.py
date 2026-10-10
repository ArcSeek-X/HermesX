# -*- coding: utf-8 -*-
"""
===================================
个股 K 线接口
===================================

职责：
1. 暴露统一的 K 线 / 股票搜索 / 股票基础信息接口。
2. 端点层只做参数校验、错误映射与短 TTL 缓存。
3. 真实取数与 fallback 下沉到 `data_provider/*`，避免端点层直接对接上游源。
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.kline import (
    KLinePoint,
    KLineResponse,
    StockInfoResponse,
    StockSearchResponse,
    StockSearchResult,
)
from data_provider.code_search.base import search_codes
from data_provider.kline.base import KLineRequest, get_kline_data
from data_provider.stock_info.base import get_stock_info

logger = logging.getLogger(__name__)

router = APIRouter()

_kline_cache: Dict[str, Dict[str, object]] = {}
_info_cache: Dict[str, Dict[str, object]] = {}
_search_cache: Dict[str, Dict[str, object]] = {}

PERIOD_DEFAULT_LIMITS = {
    "1m": 240,
    "5m": 240,
    "15m": 200,
    "30m": 160,
    "60m": 120,
    "120m": 100,
    "5d": 120,
    "daily": 250,
    "weekly": 150,
    "monthly": 80,
    "yearly": 40,
}


def _cache_valid(cache_item: Optional[Dict[str, object]], ttl: int) -> bool:
    if not cache_item:
        return False
    return (time.time() - float(cache_item.get("timestamp", 0))) < ttl


@router.get("/search", response_model=StockSearchResponse)
def search_stocks(
    q: str = Query(..., min_length=1, description="搜索关键词（代码/名称/拼音/简拼）")
) -> StockSearchResponse:
    """股票搜索。"""
    cache_key = q.strip().lower()
    cached = _search_cache.get(cache_key)
    if _cache_valid(cached, ttl=300):
        return cached["data"]  # type: ignore[return-value]

    try:
        results = search_codes(q, limit=10)
    except Exception as exc:
        logger.error("股票搜索失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="股票搜索数据获取失败") from exc

    response = StockSearchResponse(
        results=[
            StockSearchResult(code=item.code, name=item.name, market=item.market, secid=item.secid)
            for item in results
        ]
    )
    _search_cache[cache_key] = {"data": response, "timestamp": time.time()}
    return response


@router.get("/{stock_code}/kline", response_model=KLineResponse)
def get_kline_endpoint(
    stock_code: str,
    period: str = Query(
        "daily",
        description="K 线周期",
        pattern="^(1m|5m|15m|30m|60m|120m|5d|daily|weekly|monthly|yearly)$",
    ),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="数据条数（不传则使用周期默认值）"),
    fqt: int = Query(1, ge=0, le=2, description="复权方式：0=不复权，1=前复权，2=后复权"),
    before_date: Optional[str] = Query(None, description="分页加载：返回此日期之前的数据"),
) -> KLineResponse:
    """获取 K 线数据。"""
    final_limit = limit if limit is not None else PERIOD_DEFAULT_LIMITS.get(period, 250)
    cache_key = f"{stock_code}_{period}_{final_limit}_{fqt}_{before_date or ''}"
    cached = _kline_cache.get(cache_key)
    if _cache_valid(cached, ttl=60):
        return cached["data"]  # type: ignore[return-value]

    request = KLineRequest(
        stock_code=stock_code,
        period=period,
        limit=final_limit,
        fqt=fqt,
        before_date=before_date,
    )
    try:
        result = get_kline_data(request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="K 线数据获取失败") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("K 线数据获取失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="K 线数据获取失败") from exc

    # 前端现有体积格式化假设 volume 单位为“手”，这里继续保持历史兼容。
    normalized_rows: List[dict] = []
    for row in result.data:
        item = dict(row)
        if item.get("volume") is not None:
            item["volume"] = item["volume"] / 100
        item.pop("prev_close", None)
        normalized_rows.append(item)

    response = KLineResponse(
        stock_code=result.stock_code,
        stock_name=result.stock_name,
        period=result.period,
        secid=result.secid,
        prev_close=result.prev_close,
        source=result.source,
        data=[KLinePoint(**item) for item in normalized_rows],
    )
    _kline_cache[cache_key] = {"data": response, "timestamp": time.time()}
    return response


@router.get("/{stock_code}/info", response_model=StockInfoResponse)
def get_stock_info_endpoint(stock_code: str) -> StockInfoResponse:
    """获取股票基础信息。"""
    cached = _info_cache.get(stock_code)
    if _cache_valid(cached, ttl=30):
        return cached["data"]  # type: ignore[return-value]
    try:
        result = get_stock_info(stock_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="股票信息获取失败") from exc
    except Exception as exc:
        logger.error("股票信息获取失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="股票信息获取失败") from exc

    response = StockInfoResponse(
        stock_code=result.stock_code,
        stock_name=result.stock_name,
        current_price=result.current_price,
        change=result.change,
        change_percent=result.change_percent,
        open=result.open,
        prev_close=result.prev_close,
        high=result.high,
        low=result.low,
        volume=result.volume,
        amount=result.amount,
        turnover_rate=result.turnover_rate,
        amplitude=result.amplitude,
        pe_ratio_ttm=result.pe_ratio_ttm,
        total_market_cap=result.total_market_cap,
        update_time=None,
        source=result.source,
    )
    _info_cache[stock_code] = {"data": response, "timestamp": time.time()}
    return response
