# -*- coding: utf-8 -*-
"""
@file: kline.py
@description: 个股行情端点：K 线、代码搜索与股票基础信息；由 api.v1.router 挂到 /api/v1/kline，取数经 QuoteService → infrastructure.providers → data_provider。
@author: Lensgcx (GaoCangxiong)

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

# 模块级日志器，记录行情取数失败与数据源异常。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/kline。
router = APIRouter()

# K 线响应缓存：完整缓存键 -> {data, timestamp}；进程内共享，无容量淘汰。
_kline_cache: Dict[str, Dict[str, object]] = {}
# 股票基础信息缓存：股票代码 -> {data, timestamp}。
_info_cache: Dict[str, Dict[str, object]] = {}
# 代码搜索缓存：归一化关键词 -> {data, timestamp}。
_search_cache: Dict[str, Dict[str, object]] = {}

# 各 K 线周期在未传 limit 时的默认返回条数；短周期取更多点以覆盖完整交易日。
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
    """判断 K 线缓存条目是否仍在 TTL 内。

    缓存条目缺失、无 timestamp 或已过期均视为无效；timestamp 缺失按 0 处理，确保旧格式条目立即失效而不是永久命中。

    Args:
        cache_item: 缓存条目字典，可为 None；需含 timestamp 与 data 键。
        ttl: 有效期秒数，由调用方按接口数据时效设定。

    Returns:
        bool: 命中且未过期返回 True。

    Side Effects:
        无；只读取系统时钟与入参。
    """
    if not cache_item:
        return False
    return (time.time() - float(cache_item.get("timestamp", 0))) < ttl


@router.get("/search", response_model=StockSearchResponse)
def search_stocks(
    q: str = Query(..., min_length=1, description="搜索关键词（代码/名称/拼音/简拼）"),
    service: QuoteService = Depends(get_quote_service),
) -> StockSearchResponse:
    """股票搜索：按代码、名称、拼音或简拼匹配标的。

    命中缓存时直接返回；数据源异常统一映射为 502，避免把第三方错误细节暴露给前端。

    Args:
        q: 搜索关键词，至少 1 字符；作为缓存键时做去空白与小写归一化。
        service: 行情用例，由 Depends(get_quote_service) 装配。

    Returns:
        StockSearchResponse: 最多 10 条搜索结果。

    Raises:
        HTTPException: 取数失败时返回 502。

    Side Effects:
        写入模块级 _search_cache，记录带时间戳的响应对象。
    """
    cache_key = q.strip().lower()
    cached = _search_cache.get(cache_key)
    # 搜索词到结果的映射稳定，缓存 300s 以吸收自动补全的连续输入。
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
    """获取指定股票的 K 线数据。

    未传 limit 时按周期采用 PERIOD_DEFAULT_LIMITS 的默认条数；缓存键包含代码、周期、条数、复权方式与分页日期，避免不同口径互相污染。

    Args:
        stock_code: 股票代码，来自路径参数。
        period: K 线周期，正则限定 1m/5m/15m/30m/60m/120m/5d/daily/weekly/monthly/yearly。
        limit: 数据条数，范围 1~10000；None 时取周期默认值。
        fqt: 复权方式 0 不复权 / 1 前复权 / 2 后复权，默认 1。
        before_date: 分页游标，仅返回该日期之前的数据。
        service: 行情用例，由 Depends(get_quote_service) 装配。

    Returns:
        KLineResponse: 含 secid、昨收、数据源标识与 K 线点列表。

    Raises:
        HTTPException: 代码无数据 404、参数非法 422、数据格式或取数异常 502。

    Side Effects:
        写入模块级 _kline_cache。
    """
    final_limit = limit if limit is not None else PERIOD_DEFAULT_LIMITS.get(period, 250)
    cache_key = f"{stock_code}_{period}_{final_limit}_{fqt}_{before_date or ''}"
    cached = _kline_cache.get(cache_key)
    # K 线按分钟/日更新，缓存 60s 平衡实时性与数据源压力。
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
    """获取单只股票的实时基础信息。

    以股票代码为缓存键；未命中时调用行情用例并映射为 404/502。

    Args:
        stock_code: 股票代码，来自路径参数。
        service: 行情用例，由 Depends(get_quote_service) 装配。

    Returns:
        StockInfoResponse: 价格、涨跌、成交量、估值与数据源标识。

    Raises:
        HTTPException: 代码无数据 404、其他取数异常 502。

    Side Effects:
        写入模块级 _info_cache。
    """
    cached = _info_cache.get(stock_code)
    # 基础信息变化更少但盘中价格字段较敏感，缓存 30s。
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
