# -*- coding: utf-8 -*-
"""
@file: sina_source.py
@description: 板块能力新浪财经 source，承接费城半导体指数（gb_sox）补充行情取数。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = (5, 10)
CACHE_TTL = 60

SINA_QUOTE_URL = "https://hq.sinajs.cn/list=gb_sox"
SOX_INDEX_CODE = "SOX"
SOX_INDEX_NAME = "费城半导体指数"

# 新浪 gb_ 行情按逗号分隔：名称/最新价/涨跌幅/时间/涨跌额/开盘/最高/最低/.../昨收。
_FIELD_NAME = 0
_FIELD_PRICE = 1
_FIELD_CHANGE_PERCENT = 2
_FIELD_CHANGE = 4
_FIELD_HIGH = 6
_FIELD_LOW = 7
_FIELD_PRE_CLOSE = 26
_MIN_FIELD_COUNT = _FIELD_PRE_CLOSE + 1

DEFAULT_HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

_session = requests.Session()
_session.trust_env = False
_session.proxies = {"http": None, "https": None}
_session.headers.update(DEFAULT_HEADERS)

_SOX_CACHE: Dict[str, Any] = {"data": None, "timestamp": 0.0, "ttl": CACHE_TTL}


def _to_float(value: Optional[str]) -> Optional[float]:
    """把新浪行情字段转为有限数值，缺失值与占位符返回 None。"""
    text = "" if value is None else str(value).strip()
    if not text or text in ("-", "--"):
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_sox_quote(payload: str) -> Optional[Dict[str, Any]]:
    """解析新浪 gb_sox 行情文本，输出与东财指数卡片同构的 payload。"""
    if not payload or "hq_str_gb_sox" not in payload:
        return None
    start = payload.find('"')
    end = payload.find('"', start + 1)
    if start < 0 or end < 0:
        return None
    fields = payload[start + 1:end].split(",")
    if len(fields) < _MIN_FIELD_COUNT or not fields[_FIELD_NAME].strip():
        logger.warning("新浪费城半导体指数行情字段异常: count=%d", len(fields))
        return None
    price = _to_float(fields[_FIELD_PRICE])
    pre_close = _to_float(fields[_FIELD_PRE_CLOSE])
    if price is None or pre_close is None:
        logger.warning("新浪费城半导体指数行情缺少点位或昨收")
        return None
    return {
        # 新浪原名为「费交所半导体股指数」，与东财卡片名称统一。
        "name": SOX_INDEX_NAME,
        "code": SOX_INDEX_CODE,
        "price": price,
        "changePercent": _to_float(fields[_FIELD_CHANGE_PERCENT]),
        "change": _to_float(fields[_FIELD_CHANGE]),
        # 新浪指数无成交额，交由前端降级展示振幅。
        "amount": None,
        "high": _to_float(fields[_FIELD_HIGH]),
        "low": _to_float(fields[_FIELD_LOW]),
        "preClose": pre_close,
    }


def fetch_sox_index() -> Optional[Dict[str, Any]]:
    """直连新浪财经取费城半导体指数行情，失败返回 None 交由上层降级。"""
    try:
        response = _session.get(SINA_QUOTE_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = "gbk"
        return parse_sox_quote(response.text)
    except Exception as exc:  # noqa: BLE001 - 单一补充源失败不影响其余卡片
        logger.warning("新浪费城半导体指数行情获取失败: %s", exc)
        return None


def get_cached_sox_index() -> Optional[Dict[str, Any]]:
    """带 TTL 缓存的费城半导体指数行情，刷新失败时保留上一次有效值。"""
    fresh = (
        _SOX_CACHE["data"] is not None
        and (time.time() - float(_SOX_CACHE["timestamp"])) <= int(_SOX_CACHE["ttl"])
    )
    if fresh:
        return _SOX_CACHE["data"]
    data = fetch_sox_index()
    if data:
        _SOX_CACHE["data"] = data
        _SOX_CACHE["timestamp"] = time.time()
    return _SOX_CACHE["data"]
