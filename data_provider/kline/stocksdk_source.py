# -*- coding: utf-8 -*-
"""
===================================
StockSDK K 线源
===================================
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from data_provider.common.normalize import code_to_secid
from data_provider.kline.base import KLINE_ADJUSTMENT_TO_FQT, KLineDataSource, KLineRequest, KLineResult
from data_provider.kline.transform import ensure_change_percent, resample_rows, sort_kline_rows, trim_rows
from data_provider.stocksdk_bridge import (
    StockSdkBridgeError,
    get_stocksdk_client,
    resolve_stocksdk_symbol,
)

logger = logging.getLogger(__name__)

_FETCH_PERIOD_MAP = {
    "120m": "60m",
    "5d": "daily",
    "yearly": "monthly",
}


class StockSdkKLineSource(KLineDataSource):
    """StockSDK K 线实现。"""

    source_id = "stocksdk"

    def fetch(self, request: KLineRequest) -> Optional[KLineResult]:
        client = get_stocksdk_client()
        if not client.is_available():
            return None

        fetch_period = _FETCH_PERIOD_MAP.get(request.period, request.period)
        try:
            raw_rows = client.fetch_kline(
                request.stock_code,
                period=fetch_period,
                adjust=_fqt_to_adjust_label(request.fqt),
                limit=_fetch_limit(request.period, request.limit),
                before_date=request.before_date,
            )
        except StockSdkBridgeError as exc:
            logger.warning("[StockSdkKLineSource] bridge failed: %s", exc)
            return None

        rows = _normalize_kline_rows(raw_rows)
        if request.period in _FETCH_PERIOD_MAP:
            rows = resample_rows(rows, request.period)
        rows = trim_rows(rows, request.limit, request.before_date)
        if not rows:
            return None

        symbol = resolve_stocksdk_symbol(request.stock_code)
        stock_name = _first_non_empty_name(raw_rows)
        prev_close = rows[0].get("prev_close") or rows[0].get("close")
        secid = code_to_secid(request.stock_code) if symbol.market == "cn" else symbol.symbol
        return KLineResult(
            stock_code=request.stock_code,
            stock_name=stock_name,
            period=request.period,
            secid=secid,
            prev_close=prev_close,
            data=rows,
            source=self.source_id,
            metadata={"market": symbol.market},
        )


def _fetch_limit(period: str, limit: int) -> int:
    if period == "120m":
        return max(limit * 2, limit)
    if period == "5d":
        return max(limit * 5, limit)
    if period == "yearly":
        return max(limit * 12, limit)
    return limit


def _fqt_to_adjust_label(fqt: int) -> str:
    for label, current in KLINE_ADJUSTMENT_TO_FQT.items():
        if current == fqt:
            return "" if label == "none" else label
    return "qfq"


def _normalize_kline_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        normalized.append(
            {
                "date": _normalize_date(raw.get("date") or raw.get("tradeDate") or raw.get("time")),
                "open": _to_float(raw.get("open")),
                "close": _to_float(raw.get("close")),
                "high": _to_float(raw.get("high")),
                "low": _to_float(raw.get("low")),
                "volume": _to_float(raw.get("volume")),
                "amount": _to_float(raw.get("amount")),
                "change_percent": _to_float(
                    raw.get("changePercent") or raw.get("pctChange") or raw.get("change_percent")
                ),
                "turnover_rate": _to_float(raw.get("turnoverRate") or raw.get("turnover_rate")),
                "prev_close": _to_float(raw.get("prevClose") or raw.get("preClose") or raw.get("prev_close")),
            }
        )
    return ensure_change_percent(sort_kline_rows(normalized))


def _normalize_date(value: Any) -> str:
    raw = str(value or "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    if len(raw) == 14 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]} {raw[8:10]}:{raw[10:12]}:{raw[12:14]}"
    return raw


def _first_non_empty_name(rows: List[Dict[str, Any]]) -> Optional[str]:
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if name:
            return name
    return None


def _to_float(value: Any) -> Optional[float]:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
