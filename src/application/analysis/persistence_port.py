# -*- coding: utf-8 -*-
"""个股分析主流程的持久化端口契约（W4.2）。

``StockAnalysisPipeline`` 历史上在构造期 ``get_db()`` 直连 ``src.storage``：日线读写、
基本面快照、新闻情报、分析历史、分析上下文与均线判定等 10 个方法全部落在同一个
``DatabaseManager`` 上。搬入 ``src/application/analysis/`` 后，这行 import 会命中
application 层“不得依赖持久化实现”的边界要求，因此把 pipeline 实际用到的持久化能力
收敛为 :class:`AnalysisPipelinePersistencePort`。

设计约束（对齐 ``StockDataPort`` / ``MarketReviewHistoryPort`` 既有模式）：

- 方法面即 pipeline 实测调用点去重后的 10 个方法，不新增、不遗漏；名称均为公开名。
- ``get_analysis_history`` 单列，是因为 ``DailyMarketContextService`` 以
  ``history_repo`` 注入方式复用同一持久化入口（``src.application.history.ports``
  的 ``HistoryRepositoryPort`` 子集），pipeline 自身并不直接调用。
- 具体实现为 ``DatabaseManagerPipelinePersistenceAdapter``，逐方法委托宿主公开面，
  保持与原 ``get_db()`` 调用逐字一致的语义（尤其 ``analyze_ma_status`` 仅存在于宿主
  公开面，仓储层无同名方法，若另行聚合会造成判定口径漂移）。
- 与取数端口一致，持久化是主流程必需能力：未装配时 **显式报错**，不静默降级为
  “不落库”。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class AnalysisPipelinePersistencePort(Protocol):
    """个股分析主流程所需的持久化能力（按 pipeline 真实调用点去重）。"""

    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        """判断指定交易日是否已有日线数据（断点续传检查）。"""

    def save_daily_data(self, df: Any, code: str, data_source: str = "Unknown") -> int:
        """按 ``(code, date)`` UPSERT 日线数据，返回本次新增条数。"""

    def save_fundamental_snapshot(
        self,
        query_id: str,
        code: str,
        payload: Optional[Dict[str, Any]],
        source_chain: Optional[Any] = None,
        coverage: Optional[Any] = None,
    ) -> int:
        """写入基本面快照（只写不读，失败由调用方 fail-open）。"""

    def get_data_range(self, code: str, start_date: date, end_date: date) -> List[Any]:
        """按区间读取日线记录（``StockDaily`` 列表）。"""

    def save_news_intel(
        self,
        code: str,
        name: str,
        dimension: str,
        query: str,
        response: Any,
        query_context: Optional[Dict[str, str]] = None,
    ) -> int:
        """保存新闻情报检索结果，返回写入条数。"""

    def save_analysis_history(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str],
        context_snapshot: Optional[Dict[str, Any]] = None,
        save_snapshot: bool = True,
    ) -> int:
        """保存分析历史，返回新记录主键（失败返回 ``0``）。"""

    def get_analysis_history(
        self,
        code: Optional[str] = None,
        query_id: Optional[str] = None,
        days: int = 30,
        limit: int = 50,
        exclude_query_id: Optional[str] = None,
    ) -> List[Any]:
        """按代码或 ``query_id`` 查询历史记录（供日度市场上下文复用）。"""

    def update_analysis_history_diagnostics(
        self,
        *,
        query_id: str,
        code: Optional[str] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        notification_runs: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """补写已保存分析历史的运行诊断快照，返回受影响行数。"""

    def get_analysis_context(
        self, code: str, target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """读取分析上下文（今日/昨日对比与均线状态）。"""

    def analyze_ma_status(self, data: Any) -> str:
        """均线形态判定（宿主公开面，保证与历史判定口径一致）。"""


# —— 持久化端口的 bootstrap seam（W4.2）——
#
# application 不得 import ``src.storage``；编排层需要的默认实现改由下面这对 hook 取得：
# 具体工厂（infra 的 ``DatabaseManagerPipelinePersistenceAdapter``）由入口
# （``main.py`` / ``api_lifecycle`` / 测试 conftest）经
# ``src.bootstrap.analysis.configure_analysis_pipeline_persistence()`` 注册。
# 与取数端口一致，未注册时直接抛错，把漏装配暴露在启动期。
_persistence_port_factory: Optional[
    Callable[[], "AnalysisPipelinePersistencePort"]
] = None


def set_analysis_pipeline_persistence_port_factory(
    factory: Optional[Callable[[], "AnalysisPipelinePersistencePort"]],
) -> None:
    """注册默认持久化端口工厂（入口装配用，幂等；传 None 可重置）。"""
    global _persistence_port_factory
    _persistence_port_factory = factory


def build_pipeline_persistence_port() -> "AnalysisPipelinePersistencePort":
    """构造默认持久化端口；未装配时抛错（不静默降级为不落库）。"""
    if _persistence_port_factory is None:
        raise RuntimeError(
            "AnalysisPipelinePersistencePort 未装配：请在启动链路调用 "
            "src.bootstrap.analysis.configure_analysis_pipeline_persistence()（CLI 见 "
            "main.py，API 见 src.bootstrap.api_lifecycle，测试见 tests/conftest.py）"
        )
    return _persistence_port_factory()
