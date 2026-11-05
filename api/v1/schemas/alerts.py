# -*- coding: utf-8 -*-
"""
@file: alerts.py
@description: 告警接口契约：规则的创建/更新/列表、试运行、触发记录与通知投递记录；由 api.v1.endpoints.alerts 返回，并复用 history 与 market_phase 中的上下文摘要模型。
@author: Lensgcx (GaoCangxiong)

Alert API schemas.

Defines rule configuration payloads, dry-run evaluation results,
trigger records with public analysis context, and per-channel
notification delivery attempts.

告警规则按 target_scope 决定求值范围；触发记录只暴露可公开的分析上下文，通知记录用于排查投递失败与重试。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from api.v1.schemas.history import AnalysisContextPackOverview
from api.v1.schemas.market_phase import MarketPhaseSummary


# 规则求值范围取值：single_symbol 单只股票 / watchlist 自选股分组 / portfolio_holdings 持仓标的 / portfolio_account 单个账户 / market 全市场。
TargetScopeValue = Literal["single_symbol", "watchlist", "portfolio_holdings", "portfolio_account", "market"]
# 告警级别取值：info 提示 / warning 警告 / critical 严重，影响通知渠道与展示样式。
SeverityValue = Literal["info", "warning", "critical"]
# 试运行结果取值：triggered 已触发 / not_triggered 未触发 / evaluation_error 求值失败。
DryRunStatusValue = Literal["triggered", "not_triggered", "evaluation_error"]
# 单目标求值状态：triggered 触发 / skipped 跳过 / degraded 降级 / failed 失败。
TargetRecordStatusValue = Literal["triggered", "skipped", "degraded", "failed"]


class AlertRuleCreateRequest(BaseModel):
    """创建告警规则的请求体。

    使用场景：用户在前端配置条件告警；默认作用于单只股票、warning 级别且立即启用，冷却与通知策略可后置配置。

    @author: Lensgcx (GaoCangxiong)
    """
    # 规则名称，最长 64 字符；为空时由服务端生成默认名。
    name: Optional[str] = Field(None, max_length=64)
    # 求值范围，默认 single_symbol；决定 target 字段如何被解释。
    target_scope: TargetScopeValue = "single_symbol"
    # 求值目标，长度 1~64；含义随 target_scope 变化（代码、分组或账户标识）。
    target: str = Field(..., min_length=1, max_length=64)
    # 告警类型标识，长度 1~32，决定使用哪个求值器与参数集合。
    alert_type: str = Field(..., min_length=1, max_length=32)
    # 告警类型的参数字典（阈值、指标等），默认空字典；结构由 alert_type 约定。
    parameters: Dict[str, Any] = Field(default_factory=dict)
    # 告警级别，默认 warning。
    severity: SeverityValue = "warning"
    # 是否启用，默认 True；关闭后不参与定时求值但配置保留。
    enabled: bool = True
    # 冷却策略配置（时间窗、最大触发次数）；None 表示使用默认冷却。
    cooldown_policy: Optional[Dict[str, Any]] = None
    # 通知渠道与模板配置；None 表示使用系统默认通知设置。
    notification_policy: Optional[Dict[str, Any]] = None


class AlertRuleUpdateRequest(BaseModel):
    """更新告警规则的请求体。

    使用场景：局部修改规则；所有字段可选，None 表示保持原值，规则 ID 由路径参数传入。

    @author: Lensgcx (GaoCangxiong)
    """
    # 新的规则名称；None 表示不修改，最长 64 字符。
    name: Optional[str] = Field(None, max_length=64)
    # 新的求值范围；None 表示不修改，修改后原 target 需同步校验。
    target_scope: Optional[TargetScopeValue] = None
    # 新的求值目标；None 表示不修改，长度 1~64。
    target: Optional[str] = Field(None, min_length=1, max_length=64)
    # 新的告警类型；None 表示不修改，变更类型时 parameters 需一并提交。
    alert_type: Optional[str] = Field(None, min_length=1, max_length=32)
    # 新的参数字典；None 表示不修改，整体替换而非合并。
    parameters: Optional[Dict[str, Any]] = None
    # 新的告警级别；None 表示不修改。
    severity: Optional[SeverityValue] = None
    # 新的启用状态；None 表示不修改。
    enabled: Optional[bool] = None
    # 新的冷却策略；None 表示不修改。
    cooldown_policy: Optional[Dict[str, Any]] = None
    # 新的通知策略；None 表示不修改。
    notification_policy: Optional[Dict[str, Any]] = None


class AlertRuleItem(BaseModel):
    """告警规则列表项。

    使用场景：规则管理页；除配置字段外还带出冷却状态与最近触发时间，避免前端为展示状态再查触发记录。

    @author: Lensgcx (GaoCangxiong)
    """
    # 规则主键，更新、删除与试运行据此定位。
    id: int
    # 规则名称，用于列表展示。
    name: str
    # 当前求值范围，决定前端如何解释 target。
    target_scope: str
    # 当前求值目标值。
    target: str
    # 当前告警类型标识。
    alert_type: str
    # 当前生效的参数字典，默认空字典。
    parameters: Dict[str, Any] = Field(default_factory=dict)
    # 当前告警级别。
    severity: str
    # 当前是否参与定时求值。
    enabled: bool
    # 规则来源（用户创建、系统内置或导入），决定能否被删除或改写。
    source: str
    # 当前冷却策略；未单独配置时为 None。
    cooldown_policy: Optional[Dict[str, Any]] = None
    # 当前通知策略；使用系统默认时为 None。
    notification_policy: Optional[Dict[str, Any]] = None
    # 最近一次触发时间；从未触发时为 None。
    last_triggered_at: Optional[str] = None
    # 冷却截止时间；不在冷却期时为 None。
    cooldown_until: Optional[str] = None
    # 当前是否处于冷却中；状态未知时为 None。
    cooldown_active: Optional[bool] = None
    # 规则创建时间字符串。
    created_at: Optional[str] = None
    # 规则最后更新时间字符串。
    updated_at: Optional[str] = None


class AlertRuleListResponse(BaseModel):
    """告警规则分页列表响应体。

    使用场景：规则管理页按页拉取，total 为规则总数。

    @author: Lensgcx (GaoCangxiong)
    """
    # 当前页规则列表；无规则时为空列表。
    items: List[AlertRuleItem] = Field(default_factory=list)
    # 规则总数，用于分页计算。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int


class AlertDeleteResponse(BaseModel):
    """告警规则删除响应体。

    使用场景：删除端点返回实际删除条数，便于前端判断是否命中。

    @author: Lensgcx (GaoCangxiong)
    """
    # 实际删除的规则数；0 表示规则不存在或无权删除。
    deleted: int


class AlertRuleTargetResult(BaseModel):
    """单目标规则试运行结果。

    使用场景：多目标规则（自选股、持仓）试运行时逐标的展开，区分整体触发与单个目标的降级/跳过。

    @author: Lensgcx (GaoCangxiong)
    """
    # 被求值的标的代码或目标标识，用于与请求范围核对。
    target: str
    # 目标的可读展示名（股票名称、账户名）；缺失时为 None。
    display_target: Optional[str] = None
    # 该目标的试运行结果（触发 / 未触发 / 求值失败）。
    status: DryRunStatusValue
    # 该目标在真实求值链路中应有的记录状态；试运行无记录时为 None。
    record_status: Optional[TargetRecordStatusValue] = None
    # 该目标是否满足条件，供前端逐项高亮。
    triggered: bool
    # 求值得到的实际观测值；失败或不可得时为 None。
    observed_value: Optional[Any] = None
    # 本次比较使用的阈值；无需阈值的规则为 None。
    threshold: Optional[Any] = None
    # 该目标的结果说明或失败原因。
    message: str


class AlertRuleTestResponse(BaseModel):
    """告警规则试运行响应体。

    使用场景：保存前验证规则是否按预期触发；试运行不产生真实通知，计数用于说明各状态目标分布。

    @author: Lensgcx (GaoCangxiong)
    """
    # 被试运行的规则主键；支持对未保存的临时规则回传占位 ID。
    rule_id: int
    # 本次试运行采用的求值范围；单目标规则可为 None。
    target_scope: Optional[str] = None
    # 整体试运行结果；任一目标求值失败时优先反映失败状态。
    status: DryRunStatusValue
    # 整体是否触发，多目标场景下与单个目标结果可能不同。
    triggered: bool
    # 整体观测值；多目标或无观测值时为 None。
    observed_value: Optional[Any] = None
    # 整体结果说明，含降级或失败原因。
    message: str
    # 实际参与求值的目标数，默认 0。
    evaluated_count: int = 0
    # 其中满足条件的目标数，默认 0。
    triggered_count: int = 0
    # 因数据源降级而结果可信度下降的目标数，默认 0。
    degraded_count: int = 0
    # 被冷却或过滤规则跳过的目标数，默认 0。
    skipped_count: int = 0
    # 逐目标明细列表，默认空列表；单目标规则也可为空。
    target_results: List[AlertRuleTargetResult] = Field(default_factory=list)


class AlertTriggerItem(BaseModel):
    """告警触发记录条目。

    使用场景：触发历史页；只暴露可公开的分析上下文摘要，analysis_visibility_source 说明摘要来源，便于判断可信度。

    @author: Lensgcx (GaoCangxiong)
    """
    # 触发记录主键，通知记录通过 trigger_id 关联到它。
    id: int
    # 触发该记录的规则主键；规则被删除后可能为 None。
    rule_id: Optional[int] = None
    # 触发时的标的代码或目标标识，保留快照不受后续规则修改影响。
    target: str
    # 触发时的实际观测值；非数值型规则无法落库时为 None。
    observed_value: Optional[float] = None
    # 触发时使用的阈值快照；无阈值规则为 None。
    threshold: Optional[float] = None
    # 触发原因的可读说明，供通知文案与历史页展示。
    reason: Optional[str] = None
    # 本次求值实际使用的数据源标识；多源降级时用于追溯。
    data_source: Optional[str] = None
    # 所用行情数据的时间戳，用于判断触发时数据是否新鲜。
    data_timestamp: Optional[str] = None
    # 触发发生时间字符串。
    triggered_at: Optional[str] = None
    # 触发记录状态（如已通知、已抑制、失败），决定后续重试策略。
    status: str
    # 结构化诊断信息的字符串形式；正常触发时为 None。
    diagnostics: Optional[str] = None
    # 触发时的市场阶段摘要；旧记录或推断失败时为 None。
    market_phase_summary: Optional[MarketPhaseSummary] = None
    # 触发时关联分析上下文包的公开概览；无关联分析时为 None。
    analysis_context_pack_overview: Optional[AnalysisContextPackOverview] = None
    # 公开摘要的取值来源：alert_trigger_market_context / analysis_history_snapshot / evaluator_snapshot / legacy_text / null；用于区分新结构化数据与旧文本回退。
    analysis_visibility_source: Optional[str] = Field(
        None,
        description=(
            "公开摘要来源：alert_trigger_market_context / analysis_history_snapshot / "
            "evaluator_snapshot / legacy_text / null"
        ),
    )
    # 关联决策信号的摘要字典；无关联信号时为 None。
    decision_signal_summary: Optional[Dict[str, Any]] = None


class AlertTriggerListResponse(BaseModel):
    """告警触发记录分页列表响应体。

    使用场景：触发历史按页拉取，total 为记录总数。

    @author: Lensgcx (GaoCangxiong)
    """
    # 当前页触发记录列表；无记录为空列表。
    items: List[AlertTriggerItem] = Field(default_factory=list)
    # 触发记录总数，用于分页计算。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int


class AlertNotificationItem(BaseModel):
    """告警通知投递记录条目。

    使用场景：排查某个渠道为何未送达；attempt 与 retryable 决定是否还有重试空间。

    @author: Lensgcx (GaoCangxiong)
    """
    # 通知投递记录主键。
    id: int
    # 关联的触发记录主键；系统级通知可为 None。
    trigger_id: Optional[int] = None
    # 投递渠道标识（如邮件、Webhook、机器人）。
    channel: str
    # 第几次投递尝试，从 1 开始，用于观察重试次数。
    attempt: int
    # 本次投递是否成功。
    success: bool
    # 失败时的渠道错误码；成功时为 None。
    error_code: Optional[str] = None
    # 失败是否可重试，决定调度器是否继续安排重试。
    retryable: bool
    # 本次投递耗时毫秒数；超时未返回时为 None。
    latency_ms: Optional[int] = None
    # 渠道返回的诊断信息字符串；无额外信息时为 None。
    diagnostics: Optional[str] = None
    # 投递记录创建时间字符串。
    created_at: Optional[str] = None


class AlertNotificationListResponse(BaseModel):
    """告警通知记录分页列表响应体。

    使用场景：投递历史按页拉取，可按触发记录关联查询。

    @author: Lensgcx (GaoCangxiong)
    """
    # 当前页投递记录列表；无记录为空列表。
    items: List[AlertNotificationItem] = Field(default_factory=list)
    # 投递记录总数，用于分页计算。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int
