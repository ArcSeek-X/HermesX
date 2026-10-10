# -*- coding: utf-8 -*-
"""
===================================
腾讯 K 线源
===================================
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from data_provider.common.normalize import code_to_secid, code_to_sina_symbol
from data_provider.kline.base import KLineDataSource, KLineRequest, KLineResult
from data_provider.kline.transform import trim_rows

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
TENCENT_KLINE_URL = "https://ifzq.gtimg.cn/appstock/app/fqkline/get"
PERIOD_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "60min",
    "120m": "120min",
    "5d": "day",
    "daily": "day",
    "weekly": "week",
    "monthly": "month",
    "yearly": "year",
}

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.proxies = {"http": None, "https": None}


class TencentKLineSource(KLineDataSource):
    """腾讯 K 线实现。"""

    source_id = "tencent"

    def fetch(self, request: KLineRequest) -> Optional[KLineResult]:
        tx_period = PERIOD_MAP.get(request.period)
        if not tx_period:
            return None
        symbol = code_to_sina_symbol(request.stock_code)
        rows = self._fetch_rows(symbol, tx_period, request.limit, request.fqt, request.period)
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

    def _fetch_rows(
        self,
        symbol: str,
        tx_period: str,
        limit: int,
        fqt: int,
        period: str,
    ) -> Optional[List[Dict]]:
        total_limit = max(min(limit, 10000), 1)
        fqt_str = "qfq" if fqt == 1 else ("hfq" if fqt == 2 else "")
        rows: List[Dict] = []
        seen_dates = set()
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=730)
        for _ in range(30):
            if start_dt < datetime(2000, 1, 1):
                start_dt = datetime(2000, 1, 1)
            param = (
                f"{symbol},{tx_period},{start_dt.strftime('%Y-%m-%d')},"
                f"{end_dt.strftime('%Y-%m-%d')},600,{fqt_str}"
            )
            try:
                response = _SESSION.get(
                    TENCENT_KLINE_URL,
                    params={"param": param},
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                logger.warning("[TencentKLineSource] fetch failed: %s", exc)
                return None
            stock_data = payload.get("data", {}).get(symbol, {})
            suffix = PERIOD_MAP.get(period, "day")
            suffix = "day" if "min" in suffix else suffix
            if fqt_str == "qfq":
                day_data = stock_data.get(f"qfq{suffix}", stock_data.get(suffix, []))
            elif fqt_str == "hfq":
                day_data = stock_data.get(f"hfq{suffix}", stock_data.get(suffix, []))
            else:
                day_data = stock_data.get(suffix, [])
            if not isinstance(day_data, list) or not day_data:
                end_dt = start_dt - timedelta(days=1)
                start_dt = end_dt - timedelta(days=730)
                if end_dt <= datetime(2000, 1, 1):
                    break
                continue
            for item in day_data:
                if not isinstance(item, list) or len(item) < 5 or item[0] in seen_dates:
                    continue
                seen_dates.add(item[0])
                volume = float(item[5]) if len(item) > 5 and item[5] else None
                close = float(item[2])
                rows.append(
                    {
                        "date": item[0],
                        "open": float(item[1]),
                        "close": close,
                        "high": float(item[3]),
                        "low": float(item[4]),
                        "volume": volume,
                        "amount": volume * close if volume else None,
                        "change_percent": None,
                        "turnover_rate": None,
                    }
                )
            if len(rows) >= total_limit:
                break
            end_dt = start_dt - timedelta(days=1)
            start_dt = end_dt - timedelta(days=730)
            if end_dt <= datetime(2000, 1, 1):
                break
            time.sleep(0.2)
        if not rows:
            return None
        rows.sort(key=lambda item: item["date"])
        for index in range(1, len(rows)):
            prev_close = rows[index - 1]["close"]
            current_close = rows[index]["close"]
            if prev_close:
                rows[index]["change_percent"] = round((current_close - prev_close) / prev_close * 100, 2)
        if period == "1m" and rows:
            latest_date = rows[-1]["date"].split(" ")[0]
            rows = [row for row in rows if row["date"].startswith(latest_date)]
        return rows[-total_limit:]
