# -*- coding: utf-8 -*-
"""板块与市场快照用例（市场域）。

职责边界：

- 用例层：对外响应契约（200 载荷的信封、字段投影、空数据降级），以及
  「上游没有数据」与「上游取数异常」的区分；
- 端口层：``ports.SectorProviderPort``，一次取数一个方法；
- 适配器：多来源优先级（StockSDK → 东财 → 时到量化）与各来源的 TTL 缓存、
  健康冷却在 ``data_provider/sector/`` 与适配器里，本层不重复实现选源顺序。

「空数据」与「异常」是两种语义：用例只把 ``None`` 归一成降级载荷或继续向上返回
``None``（由端点映射 502），不吞异常——数据源失败该报错就报错，避免把故障伪装成
「今天没有数据」。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application.market.ports import SectorProviderPort

__all__ = [
    "SectorService",
    "SectorSnapshotUnavailableError",
]


class SectorSnapshotUnavailableError(RuntimeError):
    """指定快照时间的历史数据不可用。

    时到量化的历史快照缺失不是客户端参数错误，也不是「今天没数据」，端点据此
    返回 502 并沿用数据源给出的文案。用独立错误类型而不是 ``LookupError``：
    板块资金流历史的 ``LookupError → 404`` 是「代码不存在」，两类语义不能混。
    """


class SectorService:
    """板块树、市场快照与板块资金流用例。"""

    def __init__(self, provider: SectorProviderPort) -> None:
        self._provider = provider

    # ---- 云图 / 层级树 -------------------------------------------------

    def get_industry_treemap(self, *, time_str: str) -> Optional[Dict[str, Any]]:
        """行业板块层级树；返回 ``None`` 表示本次取不到数据。"""
        return self._provider.fetch_industry_treemap(time_str=time_str)

    def get_stock_cloud_map(self, *, time_str: str) -> Optional[Dict[str, Any]]:
        """个股云图三级树；返回 ``None`` 表示本次取不到数据。"""
        return self._provider.fetch_stock_treemap(time_str=time_str)

    def get_etf_cloud_map(self, *, period: str, top_n: int) -> Optional[Dict[str, Any]]:
        """ETF 云图扁平列表。"""
        return self._provider.fetch_etf_treemap(period=period, top_n=top_n)

    def get_concept_cloud_map(self, *, period: str, top_n: int) -> Optional[Dict[str, Any]]:
        """概念云图扁平列表。"""
        return self._provider.fetch_concept_treemap(period=period, top_n=top_n)

    # ---- 市场快照 ------------------------------------------------------

    def get_market_indices(self, *, market: str) -> Optional[Dict[str, Any]]:
        """市场指数；无数据时返回 ``None``。"""
        indices = self._provider.fetch_market_indices(market=market)
        if not indices:
            return None
        return {"indices": indices}

    def get_market_overview(self) -> Optional[Dict[str, Any]]:
        """市场概览；无数据时返回 ``None``。"""
        return self._provider.fetch_market_overview() or None

    def get_market_cards(self, *, market: str) -> Optional[Dict[str, Any]]:
        """市场总览卡片；无数据时返回 ``None``。"""
        return self._provider.fetch_market_cards(market=market) or None

    def get_northbound_flow(self) -> Dict[str, Any]:
        """北向资金；停盘披露后常态为空，降级为占位载荷而不是报错。"""
        return self._provider.fetch_northbound_flow() or {
            "netInflow": None,
            "name": "北向资金",
        }

    def get_market_fund_flow(self) -> Dict[str, Any]:
        """大盘主力资金净流入；无数据时降级为全 ``None`` 占位。"""
        return self._provider.fetch_market_fund_flow() or {
            "mainNetInflow": None,
            "mainNetInflowPercent": None,
            "date": None,
        }

    # ---- 板块资金流 ----------------------------------------------------

    def get_sector_fund_flow_history(
        self,
        *,
        sector_type: str,
        limit: int,
        top_n: int,
        sector_codes: Optional[List[str]],
    ) -> Optional[Dict[str, Any]]:
        """板块资金流日线序列。

        指定代码全部不存在时 ``LookupError`` 原样上抛（端点映射 404）；其余
        取数异常同样上抛。只有「没有任何数据」才返回 ``None``。
        """
        return self._provider.fetch_sector_fund_flow_history(
            sector_type=sector_type,
            limit=limit,
            top_n=top_n,
            sector_codes=sector_codes,
        )

    def get_sector_fund_flow_sector_list(self, *, sector_type: str) -> Optional[Dict[str, Any]]:
        """资金流多选下拉框数据；只保留 ``code`` / ``name`` 两个字段。"""
        sectors = self._provider.fetch_sector_fund_flow_rank(
            sector_type=sector_type, top_n=200
        )
        if not sectors:
            return None
        return {
            "sectors": [
                {"code": sector["code"], "name": sector["name"]} for sector in sectors
            ]
        }

    def get_board_list(self, *, sector_type: str) -> Optional[Dict[str, Any]]:
        """板块卡片列表；``total`` 按本次实际返回条数计算。"""
        boards = self._provider.fetch_board_list(sector_type=sector_type)
        if not boards:
            return None
        return {
            "sectorType": sector_type,
            "total": len(boards),
            "boards": boards,
        }
