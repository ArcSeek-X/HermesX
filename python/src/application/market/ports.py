# -*- coding: utf-8 -*-
"""市场用例的端口定义。

端口只描述用例需要的能力，不描述数据源如何实现。选源、回退、TTL 缓存、
健康冷却仍由 ``data_provider/`` 各能力包负责（ADR-001 §4.4），本端口不做二次封装。

实现方：

- :class:`~src.infrastructure.providers.limit_pool_provider.DataProviderLimitPoolProvider`
- :class:`~src.infrastructure.providers.sector_provider.DataProviderSectorProvider`
- :class:`~src.infrastructure.persistence.repositories.analysis_repository.AnalysisRepository`（:class:`MarketLightSnapshotRepositoryPort` 的实现，由 ``bootstrap`` 注入市场灯塔用例）
- :class:`~src.infrastructure.persistence.repositories.analysis_history_repo.AnalysisHistoryRepository`（:class:`MarketReviewHistoryPort` 的实现，由 ``src.bootstrap.market.configure_market_review`` 注册工厂）
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Protocol, Tuple


class LimitPoolProviderPort(Protocol):
    """涨跌停榜单取数能力。"""

    def fetch_board(
        self,
        *,
        pool_type: str,
        date: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """返回榜单明细（``to_dict()`` 形状，字段与前端契约一致）。

        取数失败由实现方抛异常，降级策略由用例层决定。
        """


class SectorProviderPort(Protocol):
    """板块与市场快照取数能力。

    方法逐项对应 ``data_provider/sector/`` 单一能力包里的既有函数，一个方法只服务
    一个端点的一次取数；不合并成通用 ``fetch(kind, **kwargs)``，否则端点语义会被
    压成字符串参数，回到按名称分派的旧写法。

    返回 ``None`` 表示「所有来源都没有可用数据」，由用例层决定降级或报错；
    抛异常表示取数过程失败，同样由用例层决定是否吞掉。
    """

    def fetch_industry_treemap(self, *, time_str: str) -> Optional[Dict[str, Any]]:
        """行业板块层级树（一级行业含二级子节点）。"""

    def fetch_stock_treemap(self, *, time_str: str) -> Optional[Dict[str, Any]]:
        """个股云图（行业 → 子行业 → 个股三级树）。"""

    def fetch_etf_treemap(self, *, period: str, top_n: int) -> Optional[Dict[str, Any]]:
        """ETF 云图（按市值排序的扁平列表）。"""

    def fetch_concept_treemap(self, *, period: str, top_n: int) -> Optional[Dict[str, Any]]:
        """概念云图（按市值排序的扁平列表）。"""

    def fetch_market_indices(self, *, market: str) -> Optional[List[Dict[str, Any]]]:
        """市场指数实时行情（``a`` / ``us`` / ``jp-kr``）。"""

    def fetch_market_overview(self) -> Optional[Dict[str, Any]]:
        """市场概览（涨跌家数、成交额、涨跌停家数、量能）。"""

    def fetch_northbound_flow(self) -> Optional[Dict[str, Any]]:
        """北向资金净流入；停盘披露后常态为空。"""

    def fetch_market_fund_flow(self) -> Optional[Dict[str, Any]]:
        """大盘主力资金净流入。"""

    def fetch_market_cards(self, *, market: str) -> Optional[Dict[str, Any]]:
        """市场总览 TAB 的统一卡片列表（``a`` / ``hk-us`` / ``jp-kr``）。"""

    def fetch_board_list(self, *, sector_type: str) -> Optional[List[Dict[str, Any]]]:
        """行业 / 概念板块卡片列表。"""

    def fetch_sector_fund_flow_rank(self, *, sector_type: str, top_n: int) -> Optional[List[Dict[str, Any]]]:
        """板块资金流排行（用于前端多选下拉框）。"""

    def fetch_sector_fund_flow_history(
        self,
        *,
        sector_type: str,
        limit: int,
        top_n: int,
        sector_codes: Optional[List[str]],
    ) -> Optional[Dict[str, Any]]:
        """板块资金流日线序列。

        指定板块代码全部不存在时实现方抛 ``LookupError``（端点映射 404），
        这与「取不到数据」的 ``None`` 是两种不同语义。
        """

class MarketLightSnapshotRepositoryPort(Protocol):
    """市场灯塔历史快照读取端口（持久化记录，非数据源）。

    只暴露用例 ``load_previous_snapshot`` 实际所需的“按时间倒序惰性遍历大盘复盘
    历史行的 (主键, context_snapshot)”能力；实现方为
    :class:`~src.infrastructure.persistence.repositories.analysis_repository.AnalysisRepository`，由 ``bootstrap``
    装配注入，使 :mod:`src.application.market.market_light` 不再直接依赖
    ``src.storage`` 或具体仓储实现（与同域的 limit_pool / sector 一致，
    只依赖端口）。
    """

    def iter_market_review_snapshot_payloads(
        self, *, limit: Optional[int] = None
    ) -> Iterator[Tuple[int, Any]]:
        """惰性产出 ``(主键, context_snapshot 原始 JSON)`` 元组，按时间倒序。"""


class SectorRankingPort(Protocol):
    """行业 / 概念板块排行取数能力（供市场热点用例注入）。

    只描述热点用例 ``_fetch_rankings`` 实际需要的两个方法，返回 ``(top, bottom)``
    二元组（与旧 ``_SectorRankingGateway`` 逐字一致）；选源、降级、TTL 缓存仍在
    ``data_provider/sector/`` 里，本端口不二次封装。实现方为
    :class:`~src.infrastructure.providers.sector_ranking_provider.DataSectorRankingProvider`，
    由 ``bootstrap`` 在进程启动时装配为用例的默认端口；用例主路仍可注入任意具备
    同名方法的取数器（如 ``DataFetcherManager``）。
    """

    def get_sector_rankings(
        self, limit: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """行业板块排行，返回 ``(top_sectors, bottom_sectors)``。"""

    def get_concept_rankings(
        self, limit: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """概念板块排行，返回 ``(top_sectors, bottom_sectors)``。"""


class MarketReviewDataPort(Protocol):
    """大盘复盘用例的取数能力（指数行情 / 涨跌统计 / 行业与概念排行）。

    方法逐项对应 ``data_provider.base.DataFetcherManager`` 既有接口，迁移前
    ``MarketAnalyzer`` 直接持有该 manager；此处只抽取用例实际使用的四个方法，
    选源优先级、健康冷却与 TTL 缓存仍留在 ``data_provider`` 内，适配器不做二次
    封装，也不复用 ``data_provider.sector`` 的旁路实现（两者取数路径不同）。

    返回空列表 / 空字典表示「所有来源都没有可用数据」，用例层沿用原
    ``status=empty`` 降级；抛异常表示取数过程失败，同样由用例层记录后继续。

    实现方：:class:`~src.infrastructure.providers.market_review_provider.DataProviderMarketReviewProvider`，
    由 ``src.bootstrap.market.configure_market_review`` 在进程启动时写入
    ``src.application.market.market_analyzer`` 的默认工厂。
    """

    def get_main_indices(self, region: str = "cn") -> List[Dict[str, Any]]:
        """主要指数实时行情（``cn`` / ``hk`` / ``us`` / ``jp`` / ``kr``）。"""

    def get_market_stats(self, *, purpose: str = "unspecified") -> Dict[str, Any]:
        """市场涨跌统计（涨跌家数、涨跌停家数、成交额）。"""

    def get_sector_rankings(
        self, limit: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """行业板块排行，返回 ``(top_sectors, bottom_sectors)``。"""

    def get_concept_rankings(
        self, limit: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """概念 / 题材板块排行，返回 ``(top_concepts, bottom_concepts)``。"""


class MarketReviewHistoryPort(Protocol):
    """大盘复盘历史落库端口（持久化记录，非数据源）。

    只暴露复盘流程实际需要的两次写入：保存一条分析历史、补写运行诊断快照。
    实现方为
    :class:`~src.infrastructure.persistence.repositories.analysis_history_repo.AnalysisHistoryRepository`，
    由 ``src.bootstrap.market.configure_market_review`` 注册工厂、用例内按需现建，
    使 :mod:`src.application.market.market_review` 不再直接依赖 ``src.storage``。

    返回值语义与既有 ``DatabaseManager`` 同名方法逐字一致：
    ``save_analysis_history`` 返回新记录主键，保存失败返回 ``0``；
    ``update_analysis_history_diagnostics`` 返回受影响行数，未命中返回 ``0``。
    """

    def save_analysis_history(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str],
        context_snapshot: Optional[Dict[str, Any]] = None,
        save_snapshot: bool = True,
    ) -> int:
        """保存分析结果历史记录，返回新记录主键（失败返回 ``0``）。"""

    def update_analysis_history_diagnostics(
        self,
        *,
        query_id: str,
        code: Optional[str] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        notification_runs: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """补写已保存分析历史的运行诊断快照，返回受影响行数。"""
