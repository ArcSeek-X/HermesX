# -*- coding: utf-8 -*-
"""
===================================
K 线标准化与聚合
===================================

职责：
1. 统一不同源的 K 线数据排序与字段形态。
2. 处理 StockDB 的复权换算与分钟/日线聚合。
3. 输出 `/api/v1/kline` 可直接消费的标准点列表。
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


def sort_kline_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按日期升序排列 K 线。"""
    result = list(rows)
    result.sort(key=lambda item: str(item.get("date") or ""))
    return result


def ensure_change_percent(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """补齐涨跌幅。"""
    prev_close: Optional[float] = None
    for item in rows:
        close = _to_float(item.get("close"))
        if item.get("change_percent") is None and prev_close and close is not None and prev_close > 0:
            item["change_percent"] = round((close - prev_close) / prev_close * 100, 2)
        if close is not None:
            prev_close = close
    return rows


def normalize_stockdb_daily_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将 StockDB 日 K 标准化为统一结构。"""
    normalized: List[Dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        date_value = str(raw.get("date") or "")
        if len(date_value) == 8 and date_value.isdigit():
            date_value = f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:8]}"
        normalized.append(
            {
                "date": date_value,
                "open": _to_float(raw.get("open")),
                "close": _to_float(raw.get("close")),
                "high": _to_float(raw.get("high")),
                "low": _to_float(raw.get("low")),
                "volume": _to_float(raw.get("volume")),
                "amount": _to_float(raw.get("amount")),
                "change_percent": _to_float(raw.get("pct_chg")),
                "turnover_rate": _to_float(raw.get("turnover")),
                "prev_close": _to_float(raw.get("pre_close")),
            }
        )
    return ensure_change_percent(sort_kline_rows(normalized))


def normalize_stockdb_minute_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将 StockDB 分钟 K 标准化为统一结构。"""
    normalized: List[Dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        normalized.append(
            {
                "date": _normalize_minute_timestamp(raw.get("date")),
                "open": _to_float(raw.get("open")),
                "close": _to_float(raw.get("close")),
                "high": _to_float(raw.get("high")),
                "low": _to_float(raw.get("low")),
                "volume": _to_float(raw.get("volume")),
                "amount": _to_float(raw.get("amount")),
                "change_percent": None,
                "turnover_rate": None,
            }
        )
    return ensure_change_percent(sort_kline_rows(normalized))


def apply_stockdb_adjust(rows: List[Dict[str, Any]], factors: Iterable[Dict[str, Any]], fq: str) -> List[Dict[str, Any]]:
    """对 StockDB 原始日 K 应用前/后复权。"""
    if fq not in {"qfq", "hfq"}:
        return rows
    factor_map: Dict[str, float] = {}
    for item in factors:
        if not isinstance(item, dict):
            continue
        date_key = str(item.get("date") or "")
        if len(date_key) == 8 and date_key.isdigit():
            date_key = f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:8]}"
        cum = _to_float(item.get("cum"))
        if cum is not None and cum > 0:
            factor_map[date_key] = cum
    if not factor_map:
        return rows
    latest_factor = max(factor_map.values())
    result: List[Dict[str, Any]] = []
    for row in rows:
        current_factor = factor_map.get(str(row.get("date")), latest_factor)
        if current_factor <= 0:
            result.append(dict(row))
            continue
        ratio = current_factor / latest_factor if fq == "qfq" else current_factor
        scaled = dict(row)
        for key in ("open", "close", "high", "low", "prev_close"):
            value = _to_float(row.get(key))
            scaled[key] = round(value / ratio, 4) if value is not None and ratio else value
        result.append(scaled)
    return ensure_change_percent(result)


def resample_rows(rows: List[Dict[str, Any]], period: str) -> List[Dict[str, Any]]:
    """聚合缺失周期。"""
    if period == "5d":
        return _aggregate_fixed_chunk(rows, 5)
    if period == "120m":
        return _aggregate_intraday(rows, 120)
    if period == "weekly":
        return _aggregate_calendar(rows, "week")
    if period == "monthly":
        return _aggregate_calendar(rows, "month")
    if period == "yearly":
        return _aggregate_calendar(rows, "year")
    if period in {"5m", "15m", "30m", "60m"}:
        return _aggregate_intraday(rows, int(period[:-1]))
    return rows


def trim_rows(rows: List[Dict[str, Any]], limit: int, before_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """按 before_date 和 limit 截断。"""
    filtered = rows
    if before_date:
        filtered = [row for row in rows if str(row.get("date") or "") < before_date]
    if limit > 0 and len(filtered) > limit:
        filtered = filtered[-limit:]
    return filtered


def _aggregate_fixed_chunk(rows: List[Dict[str, Any]], chunk_size: int) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for index in range(0, len(rows), chunk_size):
        chunk = rows[index:index + chunk_size]
        if chunk:
            result.append(_merge_chunk(chunk))
    return result


def _aggregate_intraday(rows: List[Dict[str, Any]], step_minutes: int) -> List[Dict[str, Any]]:
    buckets: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for row in rows:
        stamp = str(row.get("date") or "")
        try:
            dt = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        bucket_minute = (dt.hour * 60 + dt.minute) // step_minutes * step_minutes
        bucket_dt = dt.replace(hour=bucket_minute // 60, minute=bucket_minute % 60, second=0)
        bucket_key = bucket_dt.strftime("%Y-%m-%d %H:%M:%S")
        buckets.setdefault(bucket_key, []).append(row)
    return [_merge_chunk(bucket, bucket_key=key) for key, bucket in buckets.items()]


def _aggregate_calendar(rows: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    buckets: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for row in rows:
        stamp = str(row.get("date") or "")
        day_stamp = stamp.split(" ")[0]
        try:
            dt = datetime.strptime(day_stamp, "%Y-%m-%d")
        except ValueError:
            continue
        if mode == "week":
            bucket_key = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
        elif mode == "month":
            bucket_key = f"{dt.year}-{dt.month:02d}"
        else:
            bucket_key = f"{dt.year}"
        buckets.setdefault(bucket_key, []).append(row)
    return [_merge_chunk(bucket) for bucket in buckets.values()]


def _merge_chunk(chunk: List[Dict[str, Any]], bucket_key: Optional[str] = None) -> Dict[str, Any]:
    last = chunk[-1]
    merged = {
        "date": bucket_key or str(last.get("date") or ""),
        "open": chunk[0].get("open"),
        "close": last.get("close"),
        "high": max(_safe_number(item.get("high")) for item in chunk),
        "low": min(_safe_number(item.get("low")) for item in chunk),
        "volume": sum(_safe_number(item.get("volume")) for item in chunk) or None,
        "amount": sum(_safe_number(item.get("amount")) for item in chunk) or None,
        "change_percent": last.get("change_percent"),
        "turnover_rate": sum(_safe_number(item.get("turnover_rate")) for item in chunk) or None,
    }
    return merged


def _normalize_minute_timestamp(value: Any) -> str:
    raw = str(value or "")
    if len(raw) == 14 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]} {raw[8:10]}:{raw[10:12]}:{raw[12:14]}"
    return raw


def _to_float(value: Any) -> Optional[float]:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_number(value: Any) -> float:
    number = _to_float(value)
    return number if number is not None else 0.0

