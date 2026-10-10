# -*- coding: utf-8 -*-
"""
===================================
东方财富代码搜索源
===================================
"""

from __future__ import annotations

import logging
from typing import List, Optional

import requests

from data_provider.code_search.base import CodeSearchResult, CodeSearchSource

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
EASTMONEY_SEARCH_URL = "http://searchapi.eastmoney.com/api/suggest/get"

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.proxies = {"http": None, "https": None}


class EastMoneyCodeSearchSource(CodeSearchSource):
    """东方财富搜索实现。"""

    source_id = "eastmoney"

    def search(self, query: str, limit: int = 10) -> Optional[List[CodeSearchResult]]:
        try:
            response = _SESSION.get(
                EASTMONEY_SEARCH_URL,
                params={
                    "input": query,
                    "type": 14,
                    "token": "D43BF722C8E33BDC906FB84D85E326E8",
                    "count": limit,
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("[EastMoneyCodeSearchSource] search failed: %s", exc)
            return None

        results: List[CodeSearchResult] = []
        for item in payload.get("QuotationCodeTable", {}).get("Data", []):
            code = item.get("Code", "")
            name = item.get("Name", "")
            market = item.get("MktNum", "")
            if market == "0":
                market_name = "SZ"
            elif market == "1":
                market_name = "SH"
            elif market == "0.8":
                market_name = "BJ"
            else:
                market_name = str(market)
            secid = f"{market}.{code}" if market in {"0", "1"} else code
            results.append(
                CodeSearchResult(
                    code=code,
                    name=name,
                    market=market_name,
                    secid=secid,
                    source=self.source_id,
                )
            )
        return results
