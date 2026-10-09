# -*- coding: utf-8 -*-
"""
===================================
StockSDK 板块与市场数据源
===================================

职责：
1. 为 market/index 页面提供 A 股 / 港美指数、市场概览、北向资金与大盘主力数据。
2. 为 sector-analysis 页面提供行业/概念板块列表与资金流历史的 StockSDK 优先入口。
3. 对不稳定或缺失的上游结果返回 None，由 endpoint 层统一回退到既有东财实现。
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from data_provider.stocksdk_bridge import StockSdkBridgeError, get_stocksdk_client

logger = logging.getLogger(__name__)

_INDEX_CACHE: Dict[str, Dict[str, object]] = {}
_OVERVIEW_CACHE = {"data": None, "timestamp": 0.0, "ttl": 60}
_FLOW_CACHE = {
    "northbound": None,
    "market_fund_flow": None,
    "timestamp": 0.0,
    "ttl": 60,
}
_BOARD_LIST_CACHE = {
    "data": {},
    "timestamp": 0.0,
    "ttl": 60,
}
_FUND_FLOW_HISTORY_CACHE: Dict[str, Dict[str, object]] = {}

_COLOR_PALETTE = [
    "#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
    "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc", "#d48265",
    "#c23531", "#2f4554", "#61a0a8", "#d48265", "#749f83",
]


def fetch_market_indices(market: str = "a") -> Optional[List[Dict]]:
    """获取 StockSDK 市场指数数据。"""
    client = get_stocksdk_client()
    if not client.is_available():
        return None

    try:
        rows = client.fetch_market_indices(market)
    except StockSdkBridgeError as exc:
        logger.warning("[StockSDK][sector] market indices failed: market=%s error=%s", market, exc)
        return None

    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        name = str(row.get("name") or "").strip()
        if not code or not name:
            continue
        normalized.append(
            {
                "name": name,
                "code": code,
                "price": _to_float(row.get("price")),
                "changePercent": _to_float(row.get("changePercent")),
                "change": _to_float(row.get("change")),
                "amount": _to_float(row.get("amount")),
                "high": _to_float(row.get("high")),
                "low": _to_float(row.get("low")),
                "preClose": _to_float(row.get("preClose")),
            }
        )
    return normalized or None


def get_cached_market_indices(market: str = "a") -> Optional[List[Dict]]:
    """获取带缓存的 StockSDK 市场指数数据。"""
    cache = _INDEX_CACHE.setdefault(market, {"data": None, "timestamp": 0.0, "ttl": 60})
    if cache["data"] is None or (time.time() - float(cache["timestamp"])) > int(cache["ttl"]):
        data = fetch_market_indices(market)
        if data:
            cache["data"] = data
            cache["timestamp"] = time.time()
    return cache["data"]  # type: ignore[return-value]


def fetch_market_overview() -> Optional[Dict]:
    """获取 StockSDK A 股市场概览。"""
    client = get_stocksdk_client()
    if not client.is_available():
        return None
    try:
        data = client.fetch_market_overview()
    except StockSdkBridgeError as exc:
        logger.warning("[StockSDK][sector] market overview failed: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    return {
        "riseCount": int(_to_float(data.get("riseCount")) or 0),
        "fallCount": int(_to_float(data.get("fallCount")) or 0),
        "flatCount": int(_to_float(data.get("flatCount")) or 0),
        "totalAmount": _to_float(data.get("totalAmount")) or 0.0,
        "volumeRatio": _to_float(data.get("volumeRatio")),
        "limitUpCount": int(_to_float(data.get("limitUpCount")) or 0),
        "limitDownCount": int(_to_float(data.get("limitDownCount")) or 0),
    }


def get_cached_market_overview() -> Optional[Dict]:
    """获取带缓存的 StockSDK 市场概览。"""
    if _OVERVIEW_CACHE["data"] is None or (time.time() - float(_OVERVIEW_CACHE["timestamp"])) > int(_OVERVIEW_CACHE["ttl"]):
        data = fetch_market_overview()
        if data:
            _OVERVIEW_CACHE["data"] = data
            _OVERVIEW_CACHE["timestamp"] = time.time()
    return _OVERVIEW_CACHE["data"]  # type: ignore[return-value]


def fetch_northbound_flow() -> Optional[Dict]:
    """获取 StockSDK 北向资金汇总。"""
    client = get_stocksdk_client()
    if not client.is_available():
        return None
    try:
        data = client.fetch_northbound_summary()
    except StockSdkBridgeError as exc:
        logger.warning("[StockSDK][sector] northbound failed: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    return {
        "netInflow": _to_float(data.get("netInflow")),
        "name": str(data.get("name") or "北向资金"),
        "date": str(data.get("date") or "").strip() or None,
        "riseCount": _to_int(data.get("riseCount")),
        "fallCount": _to_int(data.get("fallCount")),
    }


def get_cached_northbound_flow() -> Optional[Dict]:
    """获取带缓存的 StockSDK 北向资金数据。"""
    if _FLOW_CACHE["northbound"] is None or (time.time() - float(_FLOW_CACHE["timestamp"])) > int(_FLOW_CACHE["ttl"]):
        data = fetch_northbound_flow()
        if data:
            _FLOW_CACHE["northbound"] = data
            _FLOW_CACHE["timestamp"] = time.time()
    return _FLOW_CACHE["northbound"]  # type: ignore[return-value]


def fetch_market_fund_flow() -> Optional[Dict]:
    """获取 StockSDK 大盘主力资金。"""
    client = get_stocksdk_client()
    if not client.is_available():
        return None
    try:
        data = client.fetch_market_fund_flow()
    except StockSdkBridgeError as exc:
        logger.warning("[StockSDK][sector] market fund flow failed: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    return {
        "mainNetInflow": _to_float(data.get("mainNetInflow")),
        "mainNetInflowPercent": _to_float(data.get("mainNetInflowPercent")),
        "date": str(data.get("date") or "").strip() or None,
    }


def get_cached_market_fund_flow() -> Optional[Dict]:
    """获取带缓存的 StockSDK 大盘主力资金。"""
    if (
        _FLOW_CACHE["market_fund_flow"] is None
        or (time.time() - float(_FLOW_CACHE["timestamp"])) > int(_FLOW_CACHE["ttl"])
    ):
        data = fetch_market_fund_flow()
        if data:
            _FLOW_CACHE["market_fund_flow"] = data
            _FLOW_CACHE["timestamp"] = time.time()
    return _FLOW_CACHE["market_fund_flow"]  # type: ignore[return-value]


def fetch_board_list(sector_type: str = "industry") -> Optional[List[Dict]]:
    """获取 StockSDK 板块卡片列表。"""
    client = get_stocksdk_client()
    if not client.is_available():
        return None
    try:
        rows = client.fetch_board_list(sector_type)
    except StockSdkBridgeError as exc:
        logger.warning("[StockSDK][sector] board list failed: sector_type=%s error=%s", sector_type, exc)
        return None

    boards = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        name = str(row.get("name") or "").strip()
        if not code or not name:
            continue
        boards.append(
            {
                "rank": _to_int(row.get("rank")) or idx,
                "code": code,
                "name": name,
                "changePercent": round(_to_float(row.get("changePercent")) or 0.0, 2),
                "totalMarketCap": _normalize_board_market_cap(row.get("totalMarketCap")),
                "turnoverRate": round(_to_float(row.get("turnoverRate")) or 0.0, 2),
                "riseCount": _to_int(row.get("riseCount")) or 0,
                "fallCount": _to_int(row.get("fallCount")) or 0,
            }
        )
    return boards or None


def get_cached_board_list(sector_type: str = "industry") -> Optional[List[Dict]]:
    """获取带缓存的 StockSDK 板块列表。"""
    if (
        sector_type not in _BOARD_LIST_CACHE["data"]
        or (time.time() - float(_BOARD_LIST_CACHE["timestamp"])) > int(_BOARD_LIST_CACHE["ttl"])
    ):
        boards = fetch_board_list(sector_type)
        if not boards:
            return None
        _BOARD_LIST_CACHE["data"][sector_type] = boards
        _BOARD_LIST_CACHE["timestamp"] = time.time()
    return _BOARD_LIST_CACHE["data"][sector_type]  # type: ignore[return-value]


def fetch_sector_fund_flow_rank(sector_type: str = "industry", top_n: int = 10) -> Optional[List[Dict]]:
    """获取 StockSDK 板块资金流排行。"""
    client = get_stocksdk_client()
    if not client.is_available():
        return None
    try:
        rows = client.fetch_sector_fund_flow_rank(sector_type, limit=max(top_n, 1))
    except StockSdkBridgeError as exc:
        logger.warning("[StockSDK][sector] fund flow rank failed: sector_type=%s error=%s", sector_type, exc)
        return None
    sectors = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        name = str(row.get("name") or "").strip()
        if not code or not name:
            continue
        sectors.append(
            {
                "code": code,
                "name": name,
                "latest": _yuan_to_yi(_to_float(row.get("mainNetInflow"))),
            }
        )
    return sectors or None


def get_sector_fund_flow_history_data(
    sector_type: str = "industry",
    limit: int = 30,
    top_n: int = 10,
    sector_codes: Optional[List[str]] = None,
) -> Optional[Dict]:
    """获取 StockSDK 板块资金流历史序列。"""
    specified_codes = [code.strip() for code in (sector_codes or []) if code and code.strip()]
    codes_key = ",".join(specified_codes) if specified_codes else f"top{top_n}"
    cache_key = f"stocksdk_{sector_type}_{limit}_{codes_key}"
    cached = _FUND_FLOW_HISTORY_CACHE.get(cache_key)
    if cached and (time.time() - float(cached.get("timestamp", 0.0))) < 300:
        return cached["data"]  # type: ignore[return-value]

    rank_sectors: Optional[List[Dict]]
    if specified_codes:
        rank_sectors = []
        for code in specified_codes:
            rank_sectors.append({"code": code, "name": code, "latest": None})
    else:
        rank_sectors = fetch_sector_fund_flow_rank(sector_type=sector_type, top_n=top_n)
    if not rank_sectors:
        return None

    client = get_stocksdk_client()
    if not client.is_available():
        return None
    try:
        history_map = client.fetch_sector_fund_flow_history_batch(
            [sector["code"] for sector in rank_sectors],
            limit=limit,
        )
    except StockSdkBridgeError as exc:
        logger.warning("[StockSDK][sector] fund flow history failed: sector_type=%s error=%s", sector_type, exc)
        return None
    if not history_map:
        return None

    all_dates = set()
    sector_results = []
    name_map = {sector["code"]: sector for sector in rank_sectors}
    for code, rows in history_map.items():
        if not isinstance(rows, list) or not rows:
            continue
        normalized_rows = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            date = str(row.get("date") or "").strip()
            if not date:
                continue
            all_dates.add(date)
            normalized_rows[date] = _yuan_to_yi(_to_float(row.get("mainNetInflow")))
        if not normalized_rows:
            continue
        sector_meta = name_map.get(code) or {"code": code, "name": code, "latest": None}
        sector_results.append(
            {
                "code": code,
                "name": sector_meta["name"],
                "latest": sector_meta.get("latest"),
                "rows": normalized_rows,
            }
        )

    if not sector_results or not all_dates:
        return None

    sorted_dates = sorted(all_dates)
    sectors = []
    for idx, sector in enumerate(sector_results):
        sectors.append(
            {
                "code": sector["code"],
                "name": sector["name"],
                "series": [sector["rows"].get(date) for date in sorted_dates],
                "latest": sector["latest"],
                "color": _COLOR_PALETTE[idx % len(_COLOR_PALETTE)],
            }
        )

    result = {"dates": sorted_dates, "sectors": sectors}
    _FUND_FLOW_HISTORY_CACHE[cache_key] = {"data": result, "timestamp": time.time()}
    return result


def _normalize_board_market_cap(value: object) -> float:
    numeric = _to_float(value) or 0.0
    # StockSDK 某些 provider 返回亿元，某些返回元；用数量级做一次保守归一。
    if numeric > 1e9:
        return round(numeric / 1e8, 2)
    return round(numeric, 2)


def _yuan_to_yi(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value / 1e8, 2)


def _to_float(value: object) -> Optional[float]:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    numeric = _to_float(value)
    if numeric is None:
        return None
    return int(numeric)

