# -*- coding: utf-8 -*-
"""
===================================
个股 K 线接口
===================================

职责：
1. 暴露统一的 K 线 / 股票搜索 / 股票基础信息接口。
2. 端点层只做参数校验、错误映射（404 / 422 / 502）与短 TTL 响应缓存。
3. 取数经 ``src.application.quote.QuoteService`` → ``src.infrastructure.providers``
   → ``data_provider/*``，端点不直接对接数据源包。
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_quote_service
from api.v1.schemas.kline import (
    KLinePoint,
    KLineResponse,
    StockInfoResponse,
    StockSearchResponse,
    StockSearchResult,
)
from src.application.quote import QuoteDataError, QuoteService

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
    q: str = Query(..., min_length=1, description="搜索关键词（代码/名称/拼音/简拼）"),
    service: QuoteService = Depends(get_quote_service),
) -> StockSearchResponse:
    """股票搜索。"""
    cache_key = q.strip().lower()
    cached = _search_cache.get(cache_key)
    if _cache_valid(cached, ttl=300):
        return cached["data"]  # type: ignore[return-value]

    try:
        results = service.search_codes(keyword=q, limit=10)
    except Exception as exc:
        logger.error("股票搜索失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="股票搜索数据获取失败") from exc

    response = StockSearchResponse(
        results=[StockSearchResult(**item) for item in results]
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
    service: QuoteService = Depends(get_quote_service),
) -> KLineResponse:
    """获取 K 线数据。"""
    final_limit = limit if limit is not None else PERIOD_DEFAULT_LIMITS.get(period, 250)
    cache_key = f"{stock_code}_{period}_{final_limit}_{fqt}_{before_date or ''}"
    cached = _kline_cache.get(cache_key)
    if _cache_valid(cached, ttl=60):
        return cached["data"]  # type: ignore[return-value]

    try:
        payload = service.get_kline(
            stock_code=stock_code,
            period=period,
            limit=final_limit,
            fqt=fqt,
            before_date=before_date,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="K 线数据获取失败") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QuoteDataError as exc:
        logger.error("K 线数据格式异常: %s", exc)
        raise HTTPException(status_code=502, detail="K 线数据获取失败") from exc
    except Exception as exc:
        logger.error("K 线数据获取失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="K 线数据获取失败") from exc

    response = KLineResponse(
        stock_code=payload["stock_code"],
        stock_name=payload.get("stock_name"),
        period=payload["period"],
        secid=payload["secid"],
        prev_close=payload.get("prev_close"),
        source=payload.get("source"),
        data=[KLinePoint(**item) for item in payload["data"]],
    )
    _kline_cache[cache_key] = {"data": response, "timestamp": time.time()}
    return response


@router.get("/{stock_code}/info", response_model=StockInfoResponse)
def get_stock_info_endpoint(
    stock_code: str,
    service: QuoteService = Depends(get_quote_service),
) -> StockInfoResponse:
    """获取股票基础信息。"""
    cached = _info_cache.get(stock_code)
    if _cache_valid(cached, ttl=30):
        return cached["data"]  # type: ignore[return-value]
    try:
        payload = service.get_stock_info(stock_code=stock_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="股票信息获取失败") from exc
    except Exception as exc:
        logger.error("股票信息获取失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="股票信息获取失败") from exc

    response = StockInfoResponse(**payload)
    _info_cache[stock_code] = {"data": response, "timestamp": time.time()}
    return response
