# -*- coding: utf-8 -*-
"""
===================================
东方财富 K 线源
===================================

职责：
1. 对接东方财富 K 线接口并输出统一结构。
2. 为周/月/年/5 日等周期提供远端基础数据。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from data_provider.common.normalize import code_to_secid
from data_provider.kline.base import KLineDataSource, KLineRequest, KLineResult
from data_provider.kline.transform import trim_rows

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
EASTMONEY_KLINE_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_KLINE_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/stock/kline/get"
KLT_MAP = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
    "120m": 120,
    "5d": 101,
    "daily": 101,
    "weekly": 102,
    "monthly": 103,
    "yearly": 104,
}

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.proxies = {"http": None, "https": None}


class EastMoneyKLineSource(KLineDataSource):
    """东方财富 K 线实现。"""

    source_id = "eastmoney"

    def fetch(self, request: KLineRequest) -> Optional[KLineResult]:
        klt = KLT_MAP.get(request.period)
        if not klt:
            return None
        secid = code_to_secid(request.stock_code)
        rows = self._fetch_rows(secid, klt, request.limit, request.fqt, request.period)
        if not rows:
            return None
        rows = trim_rows(rows, request.limit, request.before_date)
        prev_close = rows[0]["close"] if rows else None
        return KLineResult(
            stock_code=request.stock_code,
            stock_name=None,
            period=request.period,
            secid=secid,
            prev_close=prev_close,
            data=rows,
            source=self.source_id,
        )

    def _fetch_rows(
        self,
        secid: str,
        klt: int,
        limit: int,
        fqt: int,
        period: str,
    ) -> Optional[List[Dict]]:
        total_limit = max(min(limit, 10000), 1)
        for base_url in (EASTMONEY_KLINE_URL, EASTMONEY_KLINE_URL_DELAY):
            try:
                rows: List[Dict] = []
                seen_dates = set()
                beg = "0"
                end = "20500101"
                for _ in range(20):
                    response = _SESSION.get(
                        base_url,
                        params={
                            "secid": secid,
                            "fields1": "f1,f2,f3,f4,f5,f6",
                            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                            "klt": klt,
                            "fqt": fqt,
                            "beg": beg,
                            "end": end,
                            "lmt": 1000,
                            "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
                        },
                        timeout=REQUEST_TIMEOUT,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    klines = payload.get("data", {}).get("klines", [])
                    if not klines:
                        break
                    new_count = 0
                    for item in klines:
                        parts = item.split(",")
                        if len(parts) < 11 or parts[0] in seen_dates:
                            continue
                        seen_dates.add(parts[0])
                        raw_volume = float(parts[5]) if parts[5] != "-" else None
                        rows.append(
                            {
                                "date": parts[0],
                                "open": float(parts[1]),
                                "close": float(parts[2]),
                                "high": float(parts[3]),
                                "low": float(parts[4]),
                                "volume": raw_volume * 100 if raw_volume is not None else None,
                                "amount": float(parts[6]) if parts[6] != "-" else None,
                                "change_percent": float(parts[8]) if parts[8] != "-" else None,
                                "turnover_rate": float(parts[10]) if parts[10] != "-" else None,
                            }
                        )
                        new_count += 1
                    if len(rows) >= total_limit or len(klines) < 1000 or new_count == 0:
                        break
                    try:
                        last_date = datetime.strptime(klines[-1].split(",")[0], "%Y-%m-%d")
                    except ValueError:
                        break
                    beg = (last_date + timedelta(days=1)).strftime("%Y%m%d")
                if rows:
                    if period == "1m":
                        latest_date = rows[-1]["date"].split(" ")[0]
                        rows = [row for row in rows if row["date"].startswith(latest_date)]
                    return rows[-total_limit:]
            except Exception as exc:
                logger.warning("[EastMoneyKLineSource] fetch failed from %s: %s", base_url, exc)
        return None
