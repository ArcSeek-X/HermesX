# -*- coding: utf-8 -*-
"""回测用例的端口定义。

``DailyBarRefillPort`` 描述回测评估前"日线补数"这一步骤所需的**外部能力**：
按给定代码与日线窗口取数并落库。窗口计算与失败降级仍留在用例层
（:class:`~src.application.backtest.service.BacktestService`），端口只承接有副作用的
取数 + 写入。

契约：
- 入参 ``code`` 为已归一化的标准代码，``start_date`` / ``end_date`` 为
  ``YYYY-MM-DD`` 字符串，``days`` 为期望覆盖的交易日跨度；
- 实现方内部完成"选源取数 -> 空数据直接返回 -> 非空落库"，不吞异常：
  取数或写入失败向上抛出，由用例层统一降级为告警日志，保持原有行为；
- 返回值恒为 ``None``（补数是纯副作用步骤，调用方随后重新读取窗口）。

实现方：:class:`~src.infrastructure.providers.backtest_daily_refill.DataProviderDailyBarRefill`。

``BacktestRepositoryPort`` / ``StockRepositoryPort`` 描述用例层实际消费的仓储能 力：
实现方为 ``src.infrastructure.persistence.repositories`` 的 ``BacktestRepository`` /
``StockRepository``（ 由 :mod:`src.bootstrap.backtest` 装配注入）。端口以领域记录
:class:`~src.domain.backtest.BacktestResultRecord` / :class:`~src.domain.backtest.BacktestSummaryRecord`
为类型，联查行非首列与候选分析记录、日线行均用 ``Any`` 松类型，以免 application 层
反向依赖 ``src.infrastructure.persistence.models``（与 ``history`` 用例端口同一口径）。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, List, Optional, Protocol, Tuple

from src.domain.backtest import BacktestResultRecord, BacktestSummaryRecord


class DailyBarRefillPort(Protocol):
    """按日线窗口取数并持久化（回测评估前的补齐步骤）。"""

    def refill(
        self,
        *,
        code: str,
        start_date: str,
        end_date: str,
        days: int,
    ) -> None:
        """取 ``[start_date, end_date]`` 日线并写库；空数据静默返回，失败上抛。"""


class BacktestRepositoryPort(Protocol):
    """回测结果的读写能力（仅声明用例层实际调用的方法）。

    实现方 ``src.infrastructure.persistence.repositories.backtest_repository.BacktestRepository``
    以结构方式满足本协议，不要求显式继承。返回的记录为领域 DTO，联查行与候选记录以
    ``Any`` 松类型。
    """

    def get_candidates(
        self,
        *,
        code: Optional[str],
        min_age_days: int,
        limit: int,
        offset: int = 0,
        eval_window_days: int,
        engine_version: str,
        force: bool,
    ) -> List[Any]:
        """返回待评估的候选分析记录（实现内部为 AnalysisHistory，用例层只鸭子消费）。"""

    def align_existing_result_dates(
        self,
        *,
        code: Optional[str],
        min_age_days: int,
        eval_window_days: int,
        engine_version: str,
        analysis_date_from: Optional[date],
        analysis_date_to: Optional[date],
    ) -> int:
        """将已有结果的评估日期对齐到当前窗口，返回受影响行数。"""

    def save_results_batch(
        self,
        results: List[BacktestResultRecord],
        *,
        replace_existing: bool = False,
    ) -> int:
        """批量写入回测结果（内部 Record→ORM），返回写入行数。"""

    def get_results_paginated(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int],
        offset: int,
        limit: int,
    ) -> Tuple[List[Any], int]:
        """分页返回上下文联查行 ``(rows, total)``；row 首列为领域记录、其余为分析裸列。"""

    def get_results_with_context_batch(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int],
        offset: int,
        limit: int,
    ) -> List[Any]:
        """批量返回上下文联查行（首列为领域记录）。"""

    def list_results_with_context(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Tuple[BacktestResultRecord, Any]]:
        """返回 ``(结果记录, 趋势预测)`` 元组列表。"""

    def count_results(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int] = None,
    ) -> int:
        """返回符合条件的结果行数。"""

    def list_results_for_recompute(
        self,
        *,
        code: Optional[str],
        eval_window_days: int,
        engine_version: str,
    ) -> List[BacktestResultRecord]:
        """返回用于重算汇总的全部结果记录（``code=None`` 表示 overall 全量）。"""

    def list_results(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[BacktestResultRecord]:
        """返回结果记录列表。"""

    def upsert_summary(self, summary: BacktestSummaryRecord) -> None:
        """插入或更新一条汇总记录。"""

    def get_summary(
        self,
        *,
        scope: str,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: str,
    ) -> Optional[BacktestSummaryRecord]:
        """返回汇总记录；缺行返回 ``None``。"""

    def parse_analysis_date_from_snapshot(
        self, context_snapshot: Optional[str]
    ) -> Optional[date]:
        """从分析上下文快照解析分析日期（实现侧为静态方法，经实例调用）。"""

    def get_distinct_eval_windows(
        self,
        *,
        code: Optional[str],
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
    ) -> List[int]:
        """返回已有结果的去重评估窗口列表。"""


class StockRepositoryPort(Protocol):
    """日线读取能力（用例层将其实例转发给窗口解析器消费）。"""

    def get_daily_on_date(
        self, *, code: str, target_date: date
    ) -> Any:
        """返回指定交易日当日日线行（实现内部为 StockDaily，端口以 ``Any`` 松类型）。"""

    def get_forward_bars(
        self, *, code: str, analysis_date: date, eval_window_days: int
    ) -> List[Any]:
        """返回分析日之后、窗口内的日线行列表。"""


# ---------------------------------------------------------------------------
# 日线仓储工厂 seam（PP-5 引入）：持**可调用工厂**而非已构造实例。
# 供 decision（结果评估/技能观点评估）等**跨域**用例取缺省实现，避免用例层为
# ``get_daily_on_date`` / ``get_forward_bars`` 反向依赖具体 ``StockRepository``；
# 工厂而非 eager 实例是为适配 ``DatabaseManager.reset_instance()`` 生命周期。
# ---------------------------------------------------------------------------
_stock_repository_factory: (
    "Callable[[Optional[Any]], StockRepositoryPort] | None"
) = None


def set_stock_repository_factory(
    factory: "Callable[[Optional[Any]], StockRepositoryPort] | None",
) -> None:
    """装配日线仓储端口工厂（bootstrap 调用；幂等：仅非 None 覆盖）。"""
    global _stock_repository_factory
    if factory is not None:
        _stock_repository_factory = factory


def get_stock_repository(db_manager: Optional[Any] = None) -> StockRepositoryPort:
    """调用已注册工厂现建日线仓储；未装配即 fail-fast（启动链路必经 bootstrap 装配）。"""
    if _stock_repository_factory is None:  # pragma: no cover - 正常启动链路由 bootstrap 装配
        raise RuntimeError(
            "stock repository port is not configured; call "
            "src.bootstrap.quote.configure_stock_repository()"
        )
    return _stock_repository_factory(db_manager)
