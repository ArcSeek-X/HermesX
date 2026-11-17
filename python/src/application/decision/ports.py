# -*- coding: utf-8 -*-
"""决策信号用例的外部能力端口与持久化行读形端口。

以下 6 个 ``*Row`` Protocol 是 decision 域服务序列化/评估逻辑所需的 ORM 行
**读形端口**（structural typing）：``decision_signal_service`` 及其
outcome/reassess/skill_opinion 变体只按名读取行上的字段，不实例化 ORM 类、
不做 ``isinstance`` 判断（守卫 AST 全量探测证实，§0.71/D3）；因此以只读
``@property`` Protocol 描述行形，使应用层不直接依赖
``src.infrastructure.persistence.models.{analysis,decision}`` 中的具体 ORM 类
（搬入 ``src/application/decision/`` 的禁入前置，B4d/§0.53 先例同型）。

属性集按各服务实际读取字段的**并集**声明（跨服务共用同一行形时取最大面）：
- ``AnalysisHistoryRow``：decision_signal_service / reassess / skill_opinion_outcome 三件并集；
- ``DecisionSignalRow`` / ``DecisionSignalOutcomeRow`` / ``DecisionSignalFeedbackRow``：
  decision_signal_service 与 outcome_service 并集；
- ``SkillOpinionOutcomeRow`` / ``SkillOpinionSampleRow``：skill_opinion_outcome_service。

仓储返回的 SQLAlchemy ORM 行结构性满足这些 Protocol（属性名逐一对应）。
注意：``from __future__ import annotations`` 使注解不求值，运行时按 duck typing
消费；本仓 CI 不跑严格 mypy，若将来启用需保证仓储 ORM 属性名与此处声明对齐。

除行读形外，本模块还集中 decision 域四个仓储的**读写端口**（decision_signal /
decision_signal_outcome / skill_opinion_outcome / skill_opinion_sample）与
同名的**工厂 seam**（与 PP-1/PP-4 同型：持可调用工厂而非 eager 实例，以适配
``DatabaseManager.reset_instance()`` 生命周期）。三个仓储返回的 DTO
（:class:`DecisionSignalCreateResult` / :class:`OutcomeStatsRow` /
:class:`SkillOpinionOutcomeCandidate`）原定义于仓储模块、被用例层消费，按 PP-4
异常上收配方一并上收为本模块的**单一真源**（字段以 ``Any`` 松类型承装 ORM 行，
避免 application 反向依赖 ``src.infrastructure.persistence.models``），
``src.infrastructure.persistence.repositories.*`` 反向 import。

日线读取复用 ``src.application.backtest.ports.StockRepositoryPort``（跨域共享端口）；
纯函数 ``parse_analysis_date_from_snapshot`` 归 ``src.domain.analysis.analysis_context_snapshot``，
不再经仓储类静态方法调用。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
)

from src.domain.decision.profile import (
    DECISION_PROFILE_FILTER_ALL,
    DecisionProfileFilter,
)



class AnalysisHistoryRow(Protocol):
    """分析历史行的只读形（决策信号提取/复评从 history 行读取的字段面）。"""

    @property
    def id(self) -> int:
        """返回记录 ID。"""
        ...
    @property
    def code(self) -> str:
        """返回股票代码。"""
        ...
    @property
    def name(self) -> Optional[str]:
        """返回名称。"""
        ...
    @property
    def report_type(self) -> Optional[str]:
        """返回报告类型。"""
        ...
    @property
    def sentiment_score(self) -> Optional[int]:
        """返回情绪评分。"""
        ...
    @property
    def operation_advice(self) -> Optional[str]:
        """返回操作建议。"""
        ...
    @property
    def trend_prediction(self) -> Optional[str]:
        """返回趋势预测。"""
        ...
    @property
    def analysis_summary(self) -> Optional[str]:
        """返回分析摘要。"""
        ...
    @property
    def raw_result(self) -> Optional[str]:
        """返回原始分析结果。"""
        ...
    @property
    def context_snapshot(self) -> Optional[str]:
        """返回上下文快照。"""
        ...
    @property
    def ideal_buy(self) -> Optional[float]:
        """返回理想买入价。"""
        ...
    @property
    def secondary_buy(self) -> Optional[float]:
        """返回次优买入价。"""
        ...
    @property
    def stop_loss(self) -> Optional[float]:
        """返回止损价。"""
        ...
    @property
    def take_profit(self) -> Optional[float]:
        """返回止盈价。"""
        ...
    @property
    def created_at(self) -> Optional[datetime]:
        """返回创建时间。"""
        ...


class DecisionSignalRow(Protocol):
    """决策信号行的只读形（序列化/有效期/去重逻辑读取的字段面）。"""

    @property
    def id(self) -> int:
        """返回记录 ID。"""
        ...
    @property
    def stock_code(self) -> str:
        """返回股票代码。"""
        ...
    @property
    def stock_name(self) -> Optional[str]:
        """返回股票名称。"""
        ...
    @property
    def market(self) -> str:
        """返回所属市场。"""
        ...
    @property
    def source_type(self) -> str:
        """返回来源类型。"""
        ...
    @property
    def source_agent(self) -> Optional[str]:
        """返回来源 Agent。"""
        ...
    @property
    def source_report_id(self) -> Optional[int]:
        """返回来源报告 ID。"""
        ...
    @property
    def trace_id(self) -> Optional[str]:
        """返回链路追踪 ID。"""
        ...
    @property
    def decision_profile(self) -> Optional[str]:
        """返回决策档案标识。"""
        ...
    @property
    def market_phase(self) -> Optional[str]:
        """返回大盘阶段。"""
        ...
    @property
    def trigger_source(self) -> str:
        """返回触发来源。"""
        ...
    @property
    def action(self) -> str:
        """返回动作标识。"""
        ...
    @property
    def action_label(self) -> Optional[str]:
        """返回动作展示名称。"""
        ...
    @property
    def confidence(self) -> Optional[float]:
        """返回置信度。"""
        ...
    @property
    def score(self) -> Optional[int]:
        """返回评分。"""
        ...
    @property
    def horizon(self) -> Optional[str]:
        """返回持有周期。"""
        ...
    @property
    def entry_low(self) -> Optional[float]:
        """返回入场区间下界。"""
        ...
    @property
    def entry_high(self) -> Optional[float]:
        """返回入场区间上界。"""
        ...
    @property
    def stop_loss(self) -> Optional[float]:
        """返回止损价。"""
        ...
    @property
    def target_price(self) -> Optional[float]:
        """返回目标价。"""
        ...
    @property
    def invalidation(self) -> Optional[str]:
        """返回失效条件。"""
        ...
    @property
    def watch_conditions(self) -> Optional[str]:
        """返回观察条件。"""
        ...
    @property
    def reason(self) -> Optional[str]:
        """返回理由说明。"""
        ...
    @property
    def risk_summary(self) -> Optional[str]:
        """返回风险摘要。"""
        ...
    @property
    def catalyst_summary(self) -> Optional[str]:
        """返回催化剂摘要。"""
        ...
    @property
    def evidence_json(self) -> Optional[str]:
        """返回证据数据（JSON 字符串）。"""
        ...
    @property
    def data_quality_summary_json(self) -> Optional[str]:
        """返回数据质量摘要（JSON 字符串）。"""
        ...
    @property
    def plan_quality(self) -> str:
        """返回计划质量评估。"""
        ...
    @property
    def status(self) -> str:
        """返回状态。"""
        ...
    @property
    def expires_at(self) -> Optional[datetime]:
        """返回过期时间。"""
        ...
    @property
    def created_at(self) -> Optional[datetime]:
        """返回创建时间。"""
        ...
    @property
    def updated_at(self) -> Optional[datetime]:
        """返回更新时间。"""
        ...
    @property
    def metadata_json(self) -> Optional[str]:
        """返回元数据（JSON 字符串）。"""
        ...


class DecisionSignalOutcomeRow(Protocol):
    """决策信号结果行的只读形（结果序列化/聚合/重算判定读取的字段面）。"""

    @property
    def id(self) -> int:
        """返回记录 ID。"""
        ...
    @property
    def signal_id(self) -> int:
        """返回信号 ID。"""
        ...
    @property
    def horizon(self) -> str:
        """返回持有周期。"""
        ...
    @property
    def engine_version(self) -> str:
        """返回引擎版本。"""
        ...
    @property
    def eval_status(self) -> str:
        """返回评估状态。"""
        ...
    @property
    def outcome(self) -> Optional[str]:
        """返回结果。"""
        ...
    @property
    def direction_expected(self) -> Optional[str]:
        """返回预期方向。"""
        ...
    @property
    def direction_correct(self) -> Optional[bool]:
        """返回方向是否正确。"""
        ...
    @property
    def unable_reason(self) -> Optional[str]:
        """返回无法评估的原因。"""
        ...
    @property
    def anchor_date(self) -> Optional[date]:
        """返回锚定日期。"""
        ...
    @property
    def eval_window_days(self) -> Optional[int]:
        """返回评估窗口天数。"""
        ...
    @property
    def start_price(self) -> Optional[float]:
        """返回起始价格。"""
        ...
    @property
    def end_close(self) -> Optional[float]:
        """返回结束收盘价。"""
        ...
    @property
    def max_high(self) -> Optional[float]:
        """返回区间最高价。"""
        ...
    @property
    def min_low(self) -> Optional[float]:
        """返回区间最低价。"""
        ...
    @property
    def stock_return_pct(self) -> Optional[float]:
        """返回区间涨跌幅（百分比）。"""
        ...
    @property
    def action(self) -> Optional[str]:
        """返回动作标识。"""
        ...
    @property
    def market(self) -> Optional[str]:
        """返回所属市场。"""
        ...
    @property
    def market_phase(self) -> Optional[str]:
        """返回大盘阶段。"""
        ...
    @property
    def source_type(self) -> Optional[str]:
        """返回来源类型。"""
        ...
    @property
    def source_agent(self) -> Optional[str]:
        """返回来源 Agent。"""
        ...
    @property
    def plan_quality(self) -> Optional[str]:
        """返回计划质量评估。"""
        ...
    @property
    def data_quality_level(self) -> Optional[str]:
        """返回数据质量等级。"""
        ...
    @property
    def holding_state(self) -> str:
        """返回持仓状态。"""
        ...
    @property
    def created_at(self) -> Optional[datetime]:
        """返回创建时间。"""
        ...
    @property
    def updated_at(self) -> Optional[datetime]:
        """返回更新时间。"""
        ...


class DecisionSignalFeedbackRow(Protocol):
    """决策信号反馈行的只读形（反馈序列化读取的字段面）。"""

    @property
    def signal_id(self) -> int:
        """返回信号 ID。"""
        ...
    @property
    def feedback_value(self) -> str:
        """返回反馈取值。"""
        ...
    @property
    def reason_code(self) -> Optional[str]:
        """返回原因码。"""
        ...
    @property
    def note(self) -> Optional[str]:
        """返回备注。"""
        ...
    @property
    def source(self) -> str:
        """返回来源。"""
        ...
    @property
    def created_at(self) -> Optional[datetime]:
        """返回创建时间。"""
        ...
    @property
    def updated_at(self) -> Optional[datetime]:
        """返回更新时间。"""
        ...


class SkillOpinionOutcomeRow(Protocol):
    """SkillAgent 观点结果行的只读形（表现评估与序列化读取的字段面）。"""

    @property
    def id(self) -> int:
        """返回记录 ID。"""
        ...
    @property
    def skill_opinion_sample_id(self) -> int:
        """返回技能观点样本 ID。"""
        ...
    @property
    def horizon(self) -> str:
        """返回持有周期。"""
        ...
    @property
    def engine_version(self) -> str:
        """返回引擎版本。"""
        ...
    @property
    def eval_status(self) -> str:
        """返回评估状态。"""
        ...
    @property
    def outcome(self) -> Optional[str]:
        """返回结果。"""
        ...
    @property
    def direction_correct(self) -> Optional[bool]:
        """返回方向是否正确。"""
        ...
    @property
    def unable_reason(self) -> Optional[str]:
        """返回无法评估的原因。"""
        ...
    @property
    def analysis_date(self) -> Optional[date]:
        """返回分析日期。"""
        ...
    @property
    def start_trade_date(self) -> Optional[date]:
        """返回起始交易日。"""
        ...
    @property
    def end_trade_date(self) -> Optional[date]:
        """返回结束交易日。"""
        ...
    @property
    def start_price(self) -> Optional[float]:
        """返回起始价格。"""
        ...
    @property
    def end_close(self) -> Optional[float]:
        """返回结束收盘价。"""
        ...
    @property
    def stock_return_pct(self) -> Optional[float]:
        """返回区间涨跌幅（百分比）。"""
        ...
    @property
    def directional_return_pct(self) -> Optional[float]:
        """返回方向性收益（百分比）。"""
        ...
    @property
    def created_at(self) -> Optional[datetime]:
        """返回创建时间。"""
        ...
    @property
    def updated_at(self) -> Optional[datetime]:
        """返回更新时间。"""
        ...


class SkillOpinionSampleRow(Protocol):
    """SkillAgent 观点样本行的只读形（结果评估关联样本读取的字段面）。"""

    @property
    def analysis_history_id(self) -> int:
        """返回分析历史记录 ID。"""
        ...
    @property
    def stock_code(self) -> str:
        """返回股票代码。"""
        ...
    @property
    def skill_id(self) -> str:
        """返回技能 ID。"""
        ...
    @property
    def signal(self) -> str:
        """返回信号对象。"""
        ...


@dataclass
class DecisionSignalCreateResult:
    """幂等创建 DecisionSignal 的结果（仓储产出、用例消费的 DTO）。"""

    row: Any
    created: bool
    refreshed: bool = False
    duplicate: bool = False
    invalidation_reference_at: Optional[datetime] = None

    def __iter__(self):
        """返回迭代器。"""
        yield self.row
        yield self.created


@dataclass(frozen=True)
class OutcomeStatsRow:
    """结果行 + 画像标定所需的实时信号字段。"""

    outcome: Any
    decision_profile: Optional[str]
    metadata_json: Optional[str]


@dataclass(frozen=True)
class SkillOpinionOutcomeCandidate:
    """样本观点结果评估的候选键（样本 + 分析历史 + 窗口 + 既有结果）。"""

    sample: Any
    history: Any
    horizon: str
    existing_outcome: Optional[Any]


class DecisionSignalRepositoryPort(Protocol):
    """DecisionSignal 仓储端口（用例层实际消费的读写方法集）。"""

    def create_if_absent(
        self,
        fields: Dict[str, Any],
        *,
        allow_relaxed_horizon_fill: bool = False,
    ) -> DecisionSignalCreateResult:
        """在记录不存在时创建。"""
        ...

    def get(self, signal_id: int) -> Optional[Any]:
        """按标识获取记录。"""
        ...

    def list(
        self,
        *,
        stock_codes: Optional[List[str]] = None,
        stock_identities: Optional[List[Tuple[str, str]]] = None,
        market: Optional[str] = None,
        action: Optional[str] = None,
        market_phase: Optional[str] = None,
        decision_profile_filter: DecisionProfileFilter = DECISION_PROFILE_FILTER_ALL,
        source_type: Optional[str] = None,
        source_report_id: Optional[int] = None,
        trace_id: Optional[str] = None,
        trigger_source: Optional[str] = None,
        status: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        expires_from: Optional[datetime] = None,
        expires_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Any], int]:
        """列出记录。"""
        ...

    def get_latest_active(
        self,
        *,
        stock_codes: List[str],
        market: Optional[str] = None,
        limit: int = 1,
    ) -> List[Any]:
        """获取最新一条有效记录。"""
        ...

    def list_active_by_stock_actions(
        self,
        *,
        market: str,
        stock_code: str,
        actions: List[str],
        decision_profile: Optional[str],
        exclude_signal_id: Optional[int] = None,
    ) -> List[Any]:
        """按股票与动作筛选有效记录。"""
        ...

    def update_status(
        self,
        signal_id: int,
        *,
        status: str,
        metadata_json: Optional[str] = None,
        replace_metadata: bool = False,
    ) -> Optional[Any]:
        """更新记录状态。"""
        ...


class DecisionSignalOutcomeRepositoryPort(Protocol):
    """DecisionSignal 结果/反馈旁表仓储端口。"""

    def list_candidate_signals(
        self,
        *,
        signal_id: Optional[int] = None,
        stock_codes: Optional[List[str]] = None,
        market: Optional[str] = None,
        action: Optional[str] = None,
        source_type: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Any]:
        """列出待评估的候选信号。"""
        ...

    def list_outcomes_for_signals(
        self, *, signal_ids: List[int], engine_version: str
    ) -> List[Any]:
        """按信号批量列出评估结果。"""
        ...

    def get_outcome(
        self, *, signal_id: int, horizon: str, engine_version: str
    ) -> Optional[Any]:
        """按标识获取评估结果。"""
        ...

    def upsert_outcome(self, fields: Dict[str, Any]) -> Tuple[Any, bool]:
        """新增或更新评估结果。"""
        ...

    def list_outcomes(
        self,
        *,
        signal_id: Optional[int] = None,
        horizon: Optional[str] = None,
        engine_version: Optional[str] = None,
        eval_status: Optional[str] = None,
        outcome: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Any], int]:
        """列出评估结果。"""
        ...

    def list_stats_rows(
        self,
        *,
        engine_version: str,
        horizons: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
    ) -> List[OutcomeStatsRow]:
        """列出统计明细行。"""
        ...

    def get_feedback(self, *, signal_id: int) -> Optional[Any]:
        """获取反馈记录。"""
        ...

    def upsert_feedback(self, fields: Dict[str, Any]) -> Any:
        """新增或更新反馈记录。"""
        ...


class SkillOpinionOutcomeRepositoryPort(Protocol):
    """技能观点结果仓储端口。"""

    def list_candidate_keys(
        self,
        *,
        horizons: Sequence[str],
        engine_version: str,
        limit: int,
        sample_id: Optional[int] = None,
        analysis_history_id: Optional[int] = None,
        skill_id: Optional[str] = None,
        stock_code: Optional[str] = None,
    ) -> List[SkillOpinionOutcomeCandidate]:
        """列出候选键集合。"""
        ...

    def persist_outcome(self, fields: Dict[str, Any]) -> Tuple[Optional[int], str]:
        """持久化评估结果。"""
        ...

    def get_outcome(
        self, *, sample_id: int, horizon: str, engine_version: str
    ) -> Optional[Any]:
        """按标识获取评估结果。"""
        ...


class SkillOpinionSampleRepositoryPort(Protocol):
    """技能观点样本仓储端口（只写不重写）。"""

    def insert_missing(self, rows: Iterable[Dict[str, Any]]) -> int:
        """批量插入尚不存在的记录。"""
        ...


# ---------------------------------------------------------------------------
# 仓储工厂 seam（PP-1/PP-4 同型）：持**可调用工厂**而非已构造实例。
# ---------------------------------------------------------------------------
_decision_signal_repository_factory: (
    "Callable[[Optional[Any]], DecisionSignalRepositoryPort] | None"
) = None
_decision_signal_outcome_repository_factory: (
    "Callable[[Optional[Any]], DecisionSignalOutcomeRepositoryPort] | None"
) = None
_skill_opinion_outcome_repository_factory: (
    "Callable[[Optional[Any]], SkillOpinionOutcomeRepositoryPort] | None"
) = None
_skill_opinion_sample_repository_factory: (
    "Callable[[Optional[Any]], SkillOpinionSampleRepositoryPort] | None"
) = None
# 默认分析历史仓储来源 seam：仅在调用方既未显式传句柄、仓储也未携带 db 时生效，
# 与 W4.2 收敛前 ``DatabaseManager.get_instance()`` 的兜底语义逐字等价。
_default_history_repo_factory: "Callable[[], Any] | None" = None


def set_default_history_repo_factory(
    factory: "Callable[[], Any] | None",
) -> None:
    """装配 decision 域默认分析历史仓储工厂（bootstrap 传 ``DatabaseManager.get_instance``）。"""
    global _default_history_repo_factory
    _default_history_repo_factory = factory


def get_default_history_repo() -> Optional[Any]:
    """返回默认分析历史仓储；未装配即 ``None``，由调用方按既有降级语义处理。"""
    factory = _default_history_repo_factory
    return factory() if factory is not None else None


def set_decision_signal_repository_factory(
    factory: "Callable[[Optional[Any]], DecisionSignalRepositoryPort] | None",
) -> None:
    """装配 DecisionSignal 仓储端口工厂（bootstrap 调用；幂等：仅非 None 覆盖）。"""
    global _decision_signal_repository_factory
    if factory is not None:
        _decision_signal_repository_factory = factory


def get_decision_signal_repository(
    db_manager: Optional[Any] = None,
) -> DecisionSignalRepositoryPort:
    """调用已注册工厂现建仓储；未装配即 fail-fast（正常启动链路由 bootstrap 装配）。"""
    if _decision_signal_repository_factory is None:  # pragma: no cover
        raise RuntimeError(
            "decision signal repository port is not configured; call "
            "src.bootstrap.decision.configure_decision_repositories()"
        )
    return _decision_signal_repository_factory(db_manager)


def set_decision_signal_outcome_repository_factory(
    factory: "Callable[[Optional[Any]], DecisionSignalOutcomeRepositoryPort] | None",
) -> None:
    """装配结果/反馈仓储端口工厂（bootstrap 调用；幂等）。"""
    global _decision_signal_outcome_repository_factory
    if factory is not None:
        _decision_signal_outcome_repository_factory = factory


def get_decision_signal_outcome_repository(
    db_manager: Optional[Any] = None,
) -> DecisionSignalOutcomeRepositoryPort:
    """调用已注册工厂现建仓储；未装配即 fail-fast。"""
    if _decision_signal_outcome_repository_factory is None:  # pragma: no cover
        raise RuntimeError(
            "decision signal outcome repository port is not configured; call "
            "src.bootstrap.decision.configure_decision_repositories()"
        )
    return _decision_signal_outcome_repository_factory(db_manager)


def set_skill_opinion_outcome_repository_factory(
    factory: "Callable[[Optional[Any]], SkillOpinionOutcomeRepositoryPort] | None",
) -> None:
    """装配技能观点结果仓储端口工厂（bootstrap 调用；幂等）。"""
    global _skill_opinion_outcome_repository_factory
    if factory is not None:
        _skill_opinion_outcome_repository_factory = factory


def get_skill_opinion_outcome_repository(
    db_manager: Optional[Any] = None,
) -> SkillOpinionOutcomeRepositoryPort:
    """调用已注册工厂现建仓储；未装配即 fail-fast。"""
    if _skill_opinion_outcome_repository_factory is None:  # pragma: no cover
        raise RuntimeError(
            "skill opinion outcome repository port is not configured; call "
            "src.bootstrap.decision.configure_decision_repositories()"
        )
    return _skill_opinion_outcome_repository_factory(db_manager)


def set_skill_opinion_sample_repository_factory(
    factory: "Callable[[Optional[Any]], SkillOpinionSampleRepositoryPort] | None",
) -> None:
    """装配技能观点样本仓储端口工厂（bootstrap 调用；幂等）。"""
    global _skill_opinion_sample_repository_factory
    if factory is not None:
        _skill_opinion_sample_repository_factory = factory


def get_skill_opinion_sample_repository(
    db_manager: Optional[Any] = None,
) -> SkillOpinionSampleRepositoryPort:
    """调用已注册工厂现建仓储；未装配即 fail-fast。"""
    if _skill_opinion_sample_repository_factory is None:  # pragma: no cover
        raise RuntimeError(
            "skill opinion sample repository port is not configured; call "
            "src.bootstrap.decision.configure_decision_repositories()"
        )
    return _skill_opinion_sample_repository_factory(db_manager)

