# -*- coding: utf-8 -*-
"""板块与市场快照的数据源适配器。

把 ``data_provider/sector/`` 的四个来源模块收敛到 :class:`SectorProviderPort`：

- 多来源优先级（StockSDK → 东财 → 时到量化）从 ``api/v1/endpoints/sector.py``
  原样移入本层，顺序、异常吞噬范围与日志文案都保持不变；
- 各来源的 TTL 缓存与健康冷却仍在原模块里，这里不重写；
- 只做「来源选择 + 契约词汇转换」，不裁剪字段、不改单位、不做默认值兜底，
  那些都属于用例层的对外契约。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from data_provider.sector.eastmoney_source import (
    fetch_sector_fund_flow_rank as fetch_sector_fund_flow_rank_from_eastmoney,
    get_cached_board_list as get_cached_board_list_from_eastmoney,
    get_cached_market_fund_flow as get_cached_market_fund_flow_from_eastmoney,
    get_cached_market_indices as get_cached_market_indices_from_eastmoney,
    get_cached_market_overview as get_cached_market_overview_from_eastmoney,
    get_cached_northbound_flow as get_cached_northbound_flow_from_eastmoney,
    get_sector_fund_flow_history_data as get_sector_fund_flow_history_data_from_eastmoney,
)
from data_provider.sector.market_cards_source import get_market_cards
from data_provider.sector.shidaotec_source import (
    SnapshotDataUnavailableError,
    get_board_card_list as get_board_card_list_from_shidaotec,
    get_concept_treemap,
    get_etf_treemap,
    get_industry_treemap,
    get_stock_treemap,
)
from data_provider.sector.stocksdk_source import (
    fetch_sector_fund_flow_rank as fetch_sector_fund_flow_rank_from_stocksdk,
    get_cached_board_list as get_cached_board_list_from_stocksdk,
    get_cached_market_fund_flow as get_cached_market_fund_flow_from_stocksdk,
    get_cached_market_indices as get_cached_market_indices_from_stocksdk,
    get_cached_market_overview as get_cached_market_overview_from_stocksdk,
    get_cached_northbound_flow as get_cached_northbound_flow_from_stocksdk,
    get_sector_fund_flow_history_data as get_sector_fund_flow_history_data_from_stocksdk,
)
from src.application.market.sector import SectorSnapshotUnavailableError

logger = logging.getLogger(__name__)


def _prefer_stocksdk_then_fallback(
    stocksdk_loader: Callable[[], Any],
    fallback_loader: Callable[[], Any],
) -> Any:
    """优先尝试 StockSDK，失败后回退到既有数据源。

    StockSDK 的异常在内层吞掉（含空结果），回退来源的异常原样外抛——回退来源
    本来就没有第二层兜底，吞掉会变成静默空数据。
    """
    try:
        data = stocksdk_loader()
    except Exception as exc:  # noqa: BLE001 - 适配器只负责聚合回退
        logger.warning("StockSDK sector provider failed, fallback to legacy source: %s", exc)
        data = None
    if data:
        return data
    return fallback_loader()


def _prefer_loader_chain(*loaders: Callable[[], Any]) -> Any:
    """按顺序尝试多个 provider，返回第一份可用数据。"""
    for loader in loaders:
        try:
            data = loader()
        except Exception as exc:  # noqa: BLE001 - 适配器只负责聚合回退
            logger.warning("Sector provider failed in fallback chain: %s", exc)
            data = None
        if data:
            return data
    return None


def _translate_snapshot_error(loader: Callable[[], Any]) -> Any:
    """把数据源的历史快照错误换成用例层错误，保留原文案。"""
    try:
        return loader()
    except SnapshotDataUnavailableError as exc:
        raise SectorSnapshotUnavailableError(str(exc)) from exc


class DataProviderSectorProvider:
    """``SectorProviderPort`` 的数据源实现。"""

    def fetch_industry_treemap(self, *, time_str: str) -> Optional[Dict[str, Any]]:
        return _translate_snapshot_error(lambda: get_industry_treemap(time_str))

    def fetch_stock_treemap(self, *, time_str: str) -> Optional[Dict[str, Any]]:
        return _translate_snapshot_error(lambda: get_stock_treemap(time_str))

    def fetch_etf_treemap(self, *, period: str, top_n: int) -> Optional[Dict[str, Any]]:
        return get_etf_treemap(period=period, top_n=top_n)

    def fetch_concept_treemap(self, *, period: str, top_n: int) -> Optional[Dict[str, Any]]:
        return get_concept_treemap(period=period, top_n=top_n)

    def fetch_market_indices(self, *, market: str) -> Optional[List[Dict[str, Any]]]:
        return _prefer_stocksdk_then_fallback(
            lambda: get_cached_market_indices_from_stocksdk(market),
            lambda: get_cached_market_indices_from_eastmoney(market),
        )

    def fetch_market_overview(self) -> Optional[Dict[str, Any]]:
        return _prefer_stocksdk_then_fallback(
            get_cached_market_overview_from_stocksdk,
            get_cached_market_overview_from_eastmoney,
        )

    def fetch_northbound_flow(self) -> Optional[Dict[str, Any]]:
        return _prefer_stocksdk_then_fallback(
            get_cached_northbound_flow_from_stocksdk,
            get_cached_northbound_flow_from_eastmoney,
        )

    def fetch_market_fund_flow(self) -> Optional[Dict[str, Any]]:
        return _prefer_stocksdk_then_fallback(
            get_cached_market_fund_flow_from_stocksdk,
            get_cached_market_fund_flow_from_eastmoney,
        )

    def fetch_market_cards(self, *, market: str) -> Optional[Dict[str, Any]]:
        return get_market_cards(market)

    def fetch_board_list(self, *, sector_type: str) -> Optional[List[Dict[str, Any]]]:
        return _prefer_loader_chain(
            lambda: get_cached_board_list_from_stocksdk(sector_type),
            lambda: get_cached_board_list_from_eastmoney(sector_type),
            lambda: get_board_card_list_from_shidaotec(sector_type),
        )

    def fetch_sector_fund_flow_rank(
        self, *, sector_type: str, top_n: int
    ) -> Optional[List[Dict[str, Any]]]:
        return _prefer_stocksdk_then_fallback(
            lambda: fetch_sector_fund_flow_rank_from_stocksdk(sector_type, top_n),
            lambda: fetch_sector_fund_flow_rank_from_eastmoney(sector_type, top_n),
        )

    def fetch_sector_fund_flow_history(
        self,
        *,
        sector_type: str,
        limit: int,
        top_n: int,
        sector_codes: Optional[List[str]],
    ) -> Optional[Dict[str, Any]]:
        return _prefer_stocksdk_then_fallback(
            lambda: get_sector_fund_flow_history_data_from_stocksdk(
                sector_type=sector_type,
                limit=limit,
                top_n=top_n,
                sector_codes=sector_codes,
            ),
            lambda: get_sector_fund_flow_history_data_from_eastmoney(
                sector_type=sector_type,
                limit=limit,
                top_n=top_n,
                sector_codes=sector_codes,
            ),
        )
