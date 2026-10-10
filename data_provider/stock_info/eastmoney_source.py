# -*- coding: utf-8 -*-
"""
===================================
东方财富基础信息源
===================================
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from data_provider.common.normalize import code_to_secid
from data_provider.stock_info.base import StockInfoResult, StockInfoSource

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
EASTMONEY_STOCK_URL = "http://push2.eastmoney.com/api/qt/stock/get"
EASTMONEY_STOCK_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/stock/get"

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.proxies = {"http": None, "https": None}


class EastMoneyStockInfoSource(StockInfoSource):
    """东方财富股票基础信息。"""

    source_id = "eastmoney"

    def fetch(self, stock_code: str) -> Optional[StockInfoResult]:
        secid = code_to_secid(stock_code)
        for url in (EASTMONEY_STOCK_URL, EASTMONEY_STOCK_URL_DELAY):
            try:
                response = _SESSION.get(
                    url,
                    params={
                        "secid": secid,
                        "fields": "f9,f43,f44,f45,f46,f47,f48,f58,f60,f115,f116,f167,f168,f170",
                        "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
                    },
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data", {})
                if payload.get("rc") != 0 or not data:
                    continue
                current_price = _price(data.get("f43"))
                high = _price(data.get("f44"))
                low = _price(data.get("f45"))
                open_price = _price(data.get("f46"))
                prev_close = _price(data.get("f60"))
                change_percent = _ratio(data.get("f170"))
                change = current_price - prev_close if current_price is not None and prev_close is not None else None
                amplitude = (
                    round((high - low) / prev_close * 100, 2)
                    if high is not None and low is not None and prev_close not in (None, 0)
                    else None
                )
                return StockInfoResult(
                    stock_code=stock_code,
                    stock_name=_normalize_name(data.get("f58")),
                    current_price=current_price or 0.0,
                    change=change,
                    change_percent=change_percent,
                    open=open_price,
                    prev_close=prev_close,
                    high=high,
                    low=low,
                    volume=(float(data["f47"]) * 100) if data.get("f47") not in (None, "-") else None,
                    amount=float(data["f48"]) if data.get("f48") not in (None, "-") else None,
                    turnover_rate=_ratio(data.get("f168")),
                    amplitude=amplitude,
                    pe_ratio_ttm=_resolve_pe_ttm(data),
                    total_market_cap=float(data["f116"]) if data.get("f116") not in (None, "-") else None,
                    source=self.source_id,
                )
            except Exception as exc:
                logger.warning("[EastMoneyStockInfoSource] fetch failed from %s: %s", url, exc)
        return None


def get_stock_name_from_eastmoney(stock_code: str) -> Optional[str]:
    """按股票代码获取名称，供 K 线与基础信息能力共享。"""
    result = EastMoneyStockInfoSource().fetch(stock_code)
    return result.stock_name if result else None


def _normalize_name(value: object) -> Optional[str]:
    if value in (None, "", "-"):
        return None
    return str(value).strip() or None


def _price(value: object) -> Optional[float]:
    if value in (None, "", "-"):
        return None
    return float(value) / 100


def _ratio(value: object) -> Optional[float]:
    if value in (None, "", "-"):
        return None
    return float(value) / 100


def _resolve_pe_ttm(data: dict) -> Optional[float]:
    for key in ("f115", "f9"):
        value = _ratio(data.get(key))
        if value not in (None, 0):
            return value
    return None
