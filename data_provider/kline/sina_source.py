# -*- coding: utf-8 -*-
"""
===================================
新浪 K 线源
===================================
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional

import requests

from data_provider.common.normalize import code_to_secid, code_to_sina_symbol
from data_provider.kline.base import KLineDataSource, KLineRequest, KLineResult
from data_provider.kline.transform import trim_rows

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
SINA_KLINE_URL = "https://quotes.sina.cn/cn/api/jsonp_v2.php"
SINA_KLINE_URL_LEGACY = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
SCALE_MAP = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
    "120m": 120,
    "5d": 240,
    "daily": 240,
    "weekly": 1200,
    "monthly": 7200,
    "yearly": 86400,
}

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.proxies = {"http": None, "https": None}
_SESSION.headers.update(
    {
        "Referer": "http://finance.sina.com.cn/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }
)


class SinaKLineSource(KLineDataSource):
    """新浪 K 线实现。"""

    source_id = "sina"

    def fetch(self, request: KLineRequest) -> Optional[KLineResult]:
        scale = SCALE_MAP.get(request.period)
        if not scale:
            return None
        symbol = code_to_sina_symbol(request.stock_code)
        rows = self._fetch_rows(symbol, scale, request.limit, request.period)
        if not rows:
            return None
        rows = trim_rows(rows, request.limit, request.before_date)
        prev_close = rows[0]["close"] if rows else None
        return KLineResult(
            stock_code=request.stock_code,
            stock_name=None,
            period=request.period,
            secid=code_to_secid(request.stock_code),
            prev_close=prev_close,
            data=rows,
            source=self.source_id,
        )

    def _fetch_rows(self, symbol: str, scale: int, limit: int, period: str) -> Optional[List[Dict]]:
        total_limit = max(min(limit, 10000), 1)
        items: Optional[List[Dict]] = None
        try:
            response = _SESSION.get(
                SINA_KLINE_URL_LEGACY,
                params={"symbol": symbol, "scale": scale, "ma": "no", "datalen": total_limit},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            parsed = response.json()
            if isinstance(parsed, list):
                items = parsed
        except Exception as exc:
            logger.warning("[SinaKLineSource] legacy endpoint failed: %s", exc)

        if not items:
            try:
                response = _SESSION.get(
                    f"{SINA_KLINE_URL}/var%20_{symbol}=/CN_MarketDataService.getKLineData",
                    params={"symbol": symbol, "scale": scale, "ma": "no", "datalen": min(total_limit, 1000)},
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                match = re.search(r"\((\[.*\])\)", response.text, re.DOTALL)
                if not match:
                    return None
                items = json.loads(match.group(1))
            except Exception as exc:
                logger.warning("[SinaKLineSource] jsonp endpoint failed: %s", exc)
                return None

        rows: List[Dict] = []
        for item in items or []:
            volume = float(item.get("volume", 0)) if item.get("volume") else None
            close = float(item.get("close", 0))
            rows.append(
                {
                    "date": item.get("day", ""),
                    "open": float(item.get("open", 0)),
                    "close": close,
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "volume": volume,
                    "amount": volume * close if volume else None,
                    "change_percent": None,
                    "turnover_rate": None,
                }
            )
        for index in range(1, len(rows)):
            prev_close = rows[index - 1]["close"]
            current_close = rows[index]["close"]
            if prev_close:
                rows[index]["change_percent"] = round((current_close - prev_close) / prev_close * 100, 2)
        if period == "1m" and rows:
            latest_date = rows[-1]["date"].split(" ")[0]
            rows = [row for row in rows if row["date"].startswith(latest_date)]
        return rows
