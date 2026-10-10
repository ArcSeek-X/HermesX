# -*- coding: utf-8 -*-
"""
===================================
StockSDK 代码搜索源
===================================
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from data_provider.code_search.base import CodeSearchResult, CodeSearchSource
from data_provider.common.normalize import code_to_secid
from data_provider.stocksdk_bridge import StockSdkBridgeError, get_stocksdk_client

logger = logging.getLogger(__name__)


class StockSdkCodeSearchSource(CodeSearchSource):
    """StockSDK 搜索实现。"""

    source_id = "stocksdk"

    def search(self, query: str, limit: int = 10) -> Optional[List[CodeSearchResult]]:
        client = get_stocksdk_client()
        if not client.is_available():
            return None

        try:
            payload = client.search(query, limit=limit)
        except StockSdkBridgeError as exc:
            logger.warning("[StockSdkCodeSearchSource] bridge failed: %s", exc)
            return None

        results: List[CodeSearchResult] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            raw_code = str(item.get("code") or "").strip()
            raw_market = str(item.get("market") or "").strip().lower()
            normalized_code = _normalize_search_code(raw_code, raw_market)
            if not normalized_code:
                continue
            market = _normalize_market(raw_market, normalized_code)
            secid = code_to_secid(normalized_code) if market in {"SH", "SZ", "BJ"} else normalized_code
            results.append(
                CodeSearchResult(
                    code=normalized_code,
                    name=str(item.get("name") or "").strip(),
                    market=market,
                    secid=secid,
                    source=self.source_id,
                )
            )
            if len(results) >= limit:
                break
        return results


def _normalize_search_code(raw_code: str, market: str) -> str:
    upper = raw_code.upper()
    if upper.startswith(("SH", "SZ", "BJ")) and upper[2:].isdigit():
        return upper[2:]
    if upper.startswith("HK") and upper[2:].isdigit():
        return upper[2:]
    if re.fullmatch(r"\d{1,5}\.HK", upper):
        return upper[:-3].zfill(5)
    if market == "us":
        return upper
    return raw_code


def _normalize_market(raw_market: str, code: str) -> str:
    market = raw_market.lower()
    if market in {"sh", "sz", "bj", "hk", "us"}:
        return market.upper()
    if code.isdigit() and len(code) == 6:
        if code.startswith("6"):
            return "SH"
        if code.startswith(("0", "3")):
            return "SZ"
        if code.startswith(("4", "8")):
            return "BJ"
    if code.isdigit() and 4 <= len(code) <= 5:
        return "HK"
    return "US"
