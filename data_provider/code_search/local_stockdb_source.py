# -*- coding: utf-8 -*-
"""
===================================
StockDB 本地代码搜索源
===================================
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from data_provider.code_search.base import CodeSearchResult, CodeSearchSource
from data_provider.common.normalize import code_to_secid, stock_market_label
from data_provider.stockdb_fetcher import StockDbError, get_stockdb_client
from src.data.stock_index_loader import get_stock_name_index_map
from src.data.stock_mapping import STOCK_NAME_MAP

logger = logging.getLogger(__name__)


class LocalStockDbCodeSearchSource(CodeSearchSource):
    """使用 StockDB 可用代码池做本地搜索过滤。"""

    source_id = "local"

    def search(self, query: str, limit: int = 10) -> Optional[List[CodeSearchResult]]:
        dataset = _build_dataset()
        if not dataset:
            return None
        active_codes = _load_active_codes()
        normalized_query = (query or "").strip().lower()
        results: List[CodeSearchResult] = []
        for code, name in dataset.items():
            if active_codes and code not in active_codes:
                continue
            if (
                normalized_query in code.lower()
                or normalized_query in name.lower()
            ):
                results.append(
                    CodeSearchResult(
                        code=code,
                        name=name,
                        market=stock_market_label(code).upper(),
                        secid=code_to_secid(code),
                        source=self.source_id,
                    )
                )
            if len(results) >= limit:
                break
        return results


def _build_dataset() -> Dict[str, str]:
    dataset: Dict[str, str] = {}
    for code, name in STOCK_NAME_MAP.items():
        if code and name:
            dataset[str(code).strip()] = str(name).strip()
    for code, name in get_stock_name_index_map().items():
        if code and name:
            dataset[str(code).strip()] = str(name).strip()
    return dataset


def _load_active_codes() -> set[str]:
    client = get_stockdb_client()
    try:
        payload = client.fetch_code_index()
    except StockDbError as exc:
        logger.warning("[LocalStockDbCodeSearchSource] code index failed: %s", exc)
        return set()
    codes: set[str] = set()
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                for code in value:
                    if isinstance(code, str) and code.isdigit():
                        codes.add(code)
    return codes
