# -*- coding: utf-8 -*-
"""
@file: decision_signals.py
@description: 决策信号接口契约：信号创建/重评估/状态更新、护栏与预览、结果回测与多维统计、决策画像校准及用户反馈；由 api.v1.endpoints.decision_signals 使用，动作与画像枚举来自 src.domain.decision。
@author: Lensgcx (GaoCangxiong)

DecisionSignal API schemas.

Defines signal creation, reassessment and status payloads, guardrail
and preview results, outcome evaluation with multi-dimensional stats,
profile calibration buckets and user feedback records.

决策信号相关 API 的 Pydantic 请求/响应模型，涵盖信号创建与重评估、护栏与预览、结果回测与统计、画像校准及反馈。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from api.v1.schemas.market_phase import MarketPhaseValue
from src.domain.decision.action import DecisionAction
from src.domain.decision.profile import DecisionProfile


# 信号来源取值：analysis 个股分析 / agent 会话 / alert 告警 / market_review 大盘复盘 / manual 手工录入。
DecisionSignalSourceType = Literal["analysis", "agent", "alert", "market_review", "manual"]
# 信号状态取值：active 生效 / expired 过期 / invalidated 失效 / closed 结束 / archived 归档。
DecisionSignalStatus = Literal["active", "expired", "invalidated", "closed", "archived"]
# 交易计划完整度：complete 完整 / partial 部分 / minimal 极少 / unknown 未知。
DecisionSignalPlanQuality = Literal["complete", "partial", "minimal", "unknown"]
# 持有周期：intraday 日内 / 1d / 3d / 5d / 10d 交易日 / swing 波段 / long 长期。
DecisionSignalHorizon = Literal["intraday", "1d", "3d", "5d", "10d", "swing", "long"]
# 市场标识：cn / hk / us / jp / kr / tw。
DecisionSignalMarket = Literal["cn", "hk", "us", "jp", "kr", "tw"]
# 结果评估状态：completed 已完成 / unable 无法评估。
DecisionSignalOutcomeStatus = Literal["completed", "unable"]
# 结果取值：hit 命中 / miss 未命中 / neutral 中性。
DecisionSignalOutcomeValue = Literal["hit", "miss", "neutral"]
# 反馈取值：useful 有用 / not_useful 无用。
DecisionSignalFeedbackValue = Literal["useful", "not_useful"]
# 反馈来源：web 前端页面 / api 接口调用。
DecisionSignalFeedbackSource = Literal["web", "api"]


class DecisionSignalCreateRequest(BaseModel):
    """创建决策信号的请求体。

    使用场景：外部系统或手动入口写入信号；价格字段要求正数且拒绝 inf/nan，decision_profile 省略时由服务端回退默认值，但显式传 null 会被拒绝。

    @author: Lensgcx (GaoCangxiong)
    """

    # 信号关联股票代码，长度 1~32，必填。
    stock_code: str = Field(..., min_length=1, max_length=32)
    # 股票名称；未取到或历史记录未保存时为 None。
    stock_name: Optional[str] = Field(None, json_schema_extra={"maxLength": 64})
    # 标的市场，必填；取值受 DecisionSignalMarket 约束。
    market: DecisionSignalMarket
    # 信号来源类型，必填；决定后续统计的分桶维度。
    source_type: DecisionSignalSourceType
    # 产生信号的 Agent 标识；非 Agent 来源为 None。
    source_agent: Optional[str] = Field(None, json_schema_extra={"maxLength": 64})
    # 关联的分析报告 ID；无报告来源时为 None。
    source_report_id: Optional[int] = None
    # 诊断 trace ID，用于串联信号与原始分析链路。
    trace_id: Optional[str] = Field(None, json_schema_extra={"maxLength": 64})
    # 决策画像；省略时服务端使用默认/回退画像，显式传 null 会被拒绝。
    decision_profile: DecisionProfile = Field(
        default=None,
        description="Optional decision profile. Omit to use server-side default/fallback; explicit null is rejected.",
    )
    # 信号产生时的市场阶段。
    market_phase: Optional[MarketPhaseValue] = None
    # 触发来源标识，长度至少 1，必填。
    trigger_source: str = Field(..., min_length=1, json_schema_extra={"maxLength": 64})
    # 决策动作枚举，必填。
    action: DecisionAction
    # 决策动作的展示文案，前端无需自行翻译枚举。
    action_label: Optional[str] = Field(None, json_schema_extra={"maxLength": 32})
    # 信号置信度，范围 0~1；无法给出时为 None。
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    # 信号评分，范围 0~100；无法给出时为 None。
    score: Optional[int] = Field(None, ge=0, le=100)
    # 信号适用的持有周期。
    horizon: Optional[DecisionSignalHorizon] = None
    # 计划建仓区间下沿，必须大于 0 且非 inf/nan。
    entry_low: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    # 计划建仓区间上沿，必须大于 0 且非 inf/nan。
    entry_high: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    # 止损价，必须大于 0 且非 inf/nan。
    stop_loss: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    # 目标价，必须大于 0 且非 inf/nan。
    target_price: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    # 信号失效条件的结构化描述；未给出时为 None。
    invalidation: Optional[Any] = None
    # 继续观察的条件；未给出时为 None。
    watch_conditions: Optional[Any] = None
    # 给出该决策的理由；未给出时为 None。
    reason: Optional[Any] = None
    # 风险提示摘要；未给出时为 None。
    risk_summary: Optional[Any] = None
    # 催化剂摘要；未给出时为 None。
    catalyst_summary: Optional[Any] = None
    # 支撑结论的证据集合；结构随来源变化。
    evidence: Optional[Any] = None
    # 输入数据质量摘要；旧记录为 None。
    data_quality_summary: Optional[Any] = None
    # 交易计划完整度：complete / partial / minimal / unknown。
    plan_quality: Optional[DecisionSignalPlanQuality] = None
    # 信号生命周期状态：active / expired / invalidated / closed / archived。
    status: Optional[DecisionSignalStatus] = None
    # 信号过期时间；不过期时为 None。
    expires_at: Optional[datetime] = None
    # 附加元数据对象；省略或 null 都按未提供处理。
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata object. Omitted or null values are treated as absent.",
    )
    # 生成信号时所采用的报告语言 zh / en / ko。
    report_language: Optional[Literal["zh", "en", "ko"]] = None


class DecisionSignalReassessRequest(BaseModel):
    """重新评估决策信号的请求体。

    使用场景：基于指定历史报告重新生成信号；extra=forbid 拒绝未知字段，避免调用方误以为传了会生效的参数。

    @author: Lensgcx (GaoCangxiong)
    """

    # extra=forbid：拒绝未声明字段，避免重评估调用方误传不生效的参数。
    model_config = ConfigDict(extra="forbid")

    # 用于重评估的分析报告 ID，必须大于 0。
    source_report_id: int = Field(..., gt=0)
    # 本次重评估采用的决策画像，必填；不回退默认画像以保证结果可复现。
    decision_profile: DecisionProfile
    # 是否把重评估结果落库，默认 False；False 时只返回 preview。
    persist: bool = False


class DecisionSignalWarning(BaseModel):
    """决策信号生成或重评估过程中的警告项。

    使用场景：非阻断性问题（如快照缺字段）以警告码回传，params 提供模板参数，前端可本地化展示。

    @author: Lensgcx (GaoCangxiong)
    """

    # 警告码，供前端按码本地化文案。
    code: str
    # 面向用户的说明文案。
    message: Optional[str] = None
    # 警告文案的模板参数字典；无参数时为 None。
    params: Optional[Dict[str, Any]] = None


class DecisionSignalGuardrailResult(BaseModel):
    """决策信号护栏（guardrail）校验结果。

    使用场景：说明原始动作如何被规则修正；violations 与 adjustments 分开，便于审计是拦截还是降级。

    @author: Lensgcx (GaoCangxiong)
    """

    # 护栏校验前的原始决策动作。
    raw_action: str
    # 护栏校验后的最终决策动作。
    final_action: str
    # 是否通过护栏校验。
    passed: bool
    # 违反的护栏规则列表，默认空列表。
    violations: List[str] = Field(default_factory=list)
    # 护栏对结果做出的调整列表，默认空列表。
    adjustments: List[str] = Field(default_factory=list)
    # 最终动作是否相对原始动作被调整过。
    adjusted: bool


class DecisionSignalPreview(BaseModel):
    """决策信号预览结果（尚未落库）。

    使用场景：重评估的 dry-run 与前端确认页；结构贴近信号详情但不含数据库主键与时间戳。

    @author: Lensgcx (GaoCangxiong)
    """

    # 规范化的决策动作。
    action: str
    # 信号评分，范围 0~100；无法给出时为 None。
    score: Optional[int] = None
    # 信号置信度，范围 0~1；无法给出时为 None。
    confidence: Optional[float] = None
    # 信号适用的持有周期。
    horizon: Optional[str] = None
    # 计划建仓区间下沿，必须大于 0 且非 inf/nan。
    entry_low: Optional[float] = None
    # 计划建仓区间上沿，必须大于 0 且非 inf/nan。
    entry_high: Optional[float] = None
    # 止损价，必须大于 0 且非 inf/nan。
    stop_loss: Optional[float] = None
    # 目标价，必须大于 0 且非 inf/nan。
    target_price: Optional[float] = None
    # 信号失效条件的结构化描述；未给出时为 None。
    invalidation: Optional[str] = None
    # 给出该决策的理由；未给出时为 None。
    reason: Optional[str] = None
    # 风险提示摘要；未给出时为 None。
    risk_summary: Optional[str] = None
    # 继续观察的条件；未给出时为 None。
    watch_conditions: Optional[str] = None
    # 附加元数据字典；省略或 null 均视为未提供。
    metadata: Dict[str, Any]


class DecisionSignalStatusUpdateRequest(BaseModel):
    """更新决策信号状态的请求体。

    使用场景：手动归档、作废或关闭信号；metadata 省略保留原值、显式 null 清空、对象则整体替换，三种语义不可混淆。

    @author: Lensgcx (GaoCangxiong)
    """

    # 目标状态，必填；取值受 DecisionSignalStatus 约束。
    status: DecisionSignalStatus
    # 替换用元数据：省略保留原值、null 清空、对象整体替换，同时保留正式画像标识。
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional replacement metadata. Omit to preserve the stored value; "
            "null clears it; an object replaces it while preserving the formal "
            "decision_profile identity."
        ),
    )


class DecisionSignalOutcomeRunRequest(BaseModel):
    """触发决策信号结果回测评估的请求体。

    使用场景：批量评估信号在其后行情中的表现；各筛选条件可组合，未指定 signal_id 时按条件扫描，limit 上限 500。

    @author: Lensgcx (GaoCangxiong)
    """

    # 指定单个信号 ID（须大于 0）；为空时按其余条件批量扫描。
    signal_id: Optional[int] = Field(None, gt=0)
    # 待评估的持有周期列表；为空表示评估全部适用周期。
    horizons: Optional[List[DecisionSignalHorizon]] = None
    # 是否强制重算已有结果，默认 False。
    force: bool = False
    # 标的市场标识，取值受 DecisionSignalMarket 约束。
    market: Optional[DecisionSignalMarket] = None
    # 规范股票代码，标识信号或评估关联的标的。
    stock_code: Optional[str] = Field(None, json_schema_extra={"maxLength": 32})
    # 规范化的决策动作。
    action: Optional[DecisionAction] = None
    # 信号来源类型：analysis / agent / alert / market_review / manual。
    source_type: Optional[DecisionSignalSourceType] = None
    # 信号生命周期状态：active / expired / invalidated / closed / archived。
    status: Optional[DecisionSignalStatus] = None
    # 批量扫描上限，默认 100、范围 1~500。
    limit: int = Field(100, ge=1, le=500)


class DecisionSignalOutcomeItem(BaseModel):
    """单条决策信号的结果评估记录。

    使用场景：结果列表与统计明细；除状态与引擎版本外均为可选，因为历史数据或缺行情时会无法评估。

    @author: Lensgcx (GaoCangxiong)
    """

    # 结果评估记录主键。
    id: int
    # 被评估的信号 ID。
    signal_id: int
    # 本次评估采用的持有周期。
    horizon: str
    # 结果回测引擎版本，用于区分不同口径的统计结果。
    engine_version: str
    # 评估状态 completed / unable，决定结果字段是否可信。
    eval_status: str
    # 评估结果 hit / miss / neutral；无法评估时为 None。
    outcome: Optional[str] = None
    # 信号预期的价格方向，用于与实际走势比对。
    direction_expected: Optional[str] = None
    # 方向是否正确；方向不明确时为 None，不计入准确率。
    direction_correct: Optional[bool] = None
    # 无法评估的原因码；仅 eval_status=unable 时有值。
    unable_reason: Optional[str] = None
    # 评估窗口的锚定日期，通常为信号产生日。
    anchor_date: Optional[str] = None
    # 评估窗口覆盖的交易日数；无法评估时为 None。
    eval_window_days: Optional[int] = None
    # 窗口起点的基准价格。
    start_price: Optional[float] = None
    # 窗口终点收盘价。
    end_close: Optional[float] = None
    # 窗口内最高价，用于判定目标价是否触及。
    max_high: Optional[float] = None
    # 窗口内最低价，用于判定止损是否触及。
    min_low: Optional[float] = None
    # 窗口内标的涨跌幅百分比，作为对照基线。
    stock_return_pct: Optional[float] = None
    # 规范化的决策动作。
    action: Optional[str] = None
    # 标的市场标识，取值受 DecisionSignalMarket 约束。
    market: Optional[str] = None
    # 信号产生时的市场阶段。
    market_phase: Optional[str] = None
    # 信号来源类型：analysis / agent / alert / market_review / manual。
    source_type: Optional[str] = None
    # 产生信号的 Agent 标识；非 Agent 来源为 None。
    source_agent: Optional[str] = None
    # 交易计划完整度：complete / partial / minimal / unknown。
    plan_quality: Optional[str] = None
    # 信号产生时输入数据的质量等级，用于按质量分层统计命中率；旧记录为 None。
    data_quality_level: Optional[str] = None
    # 评估时的持仓状态，影响收益口径。
    holding_state: str
    # 评估记录创建时间；旧记录为 None。
    created_at: Optional[str] = None
    # 评估记录更新时间；旧记录为 None。
    updated_at: Optional[str] = None


class DecisionSignalOutcomeRunResponse(BaseModel):
    """结果回测运行响应（含处理键数与各状态计数）。

    使用场景：一次评估任务的结果汇总；created / updated / skipped 之和对应处理的信号数。

    @author: Lensgcx (GaoCangxiong)
    """

    # 本次产生的结果评估明细列表，默认空列表。
    items: List[DecisionSignalOutcomeItem] = Field(default_factory=list)
    # 本次参与评估的信号数。
    evaluated: int
    # 新建的结果评估记录数。
    created: int
    # 被刷新的结果评估记录数。
    updated: int
    # 因条件不满足或已完成而跳过的信号数。
    skipped: int
    # 结果回测引擎版本，用于区分不同口径的统计结果。
    engine_version: str


class DecisionSignalOutcomeListResponse(BaseModel):
    """结果评估记录的分页列表响应。

    使用场景：结果页按页拉取，total 为记录总数。

    @author: Lensgcx (GaoCangxiong)
    """

    # 结果或信号列表；无数据为空列表。
    items: List[DecisionSignalOutcomeItem] = Field(default_factory=list)
    # 符合条件的记录总数或分桶样本总数。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int


class DecisionSignalOutcomeStatsBucket(BaseModel):
    """结果统计中的单个分桶指标。

    使用场景：按维度（市场、动作、周期等）聚合命中率；比率类字段无样本时为 None，避免用 0 掩盖空样本。

    @author: Lensgcx (GaoCangxiong)
    """

    # 分桶所依据的维度名称，如 market、action。
    dimension: str
    # 该分桶对应的维度取值。
    value: str
    # 符合条件的记录总数或分桶样本总数。
    total: int
    # 已成功完成评估的样本数。
    completed: int
    # 因数据不足等原因无法评估的样本数。
    unable: int
    # 结果为命中的样本数。
    hit: int
    # 结果为未命中的样本数。
    miss: int
    # 结果为中性的样本数，不计入命中率分子。
    neutral: int
    # 命中率百分比；无有效样本时为 None。
    hit_rate_pct: Optional[float] = None
    # 标的平均涨跌幅百分比，作为策略表现对照基线。
    avg_stock_return_pct: Optional[float] = None
    # 无法评估原因码到出现次数的映射，默认空字典。
    unable_reasons: Dict[str, int] = Field(default_factory=dict)


class DecisionSignalProfileCalibrationBucket(BaseModel):
    """按决策画像划分的校准统计分桶。

    使用场景：评估不同画像口径的信号质量；sample_sufficient 标记样本量是否达到可解释门槛。

    @author: Lensgcx (GaoCangxiong)
    """

    # 画像校准分桶的多维取值字典，默认空字典。
    dimensions: Dict[str, str] = Field(default_factory=dict)
    # 符合条件的记录总数或分桶样本总数。
    total: int
    # 已成功完成评估的样本数。
    completed: int
    # 因数据不足等原因无法评估的样本数。
    unable: int
    # 结果为命中的样本数。
    hit: int
    # 结果为未命中的样本数。
    miss: int
    # 结果为中性的样本数，不计入命中率分子。
    neutral: int
    # 样本量是否达到可解释门槛；不足时前端应弱化展示结论。
    sample_sufficient: bool
    # 命中率百分比；无有效样本时为 None。
    hit_rate_pct: Optional[float] = None
    # 标的平均涨跌幅百分比，作为策略表现对照基线。
    avg_stock_return_pct: Optional[float] = None
    # 未命中率百分比；无有效样本时为 None。
    miss_rate_pct: Optional[float] = None
    # 无法评估样本占比百分比；无有效样本时为 None。
    unable_rate_pct: Optional[float] = None
    # 最大不利偏移百分比，衡量信号期间的最大回撤风险。
    max_adverse_excursion_pct: Optional[float] = None


class DecisionSignalProfileCalibrationBreakdowns(BaseModel):
    """画像校准结果的多维分解明细。

    使用场景：同一批样本按画像、动作、周期、阶段、数据质量与画像来源分别分桶，便于定位偏差来源。

    @author: Lensgcx (GaoCangxiong)
    """

    # 按决策画像单独分桶的结果列表，默认空列表。
    decision_profile: List[DecisionSignalProfileCalibrationBucket] = Field(default_factory=list)
    # 按画像 + 动作组合分桶的结果列表，默认空列表。
    decision_profile_action: List[DecisionSignalProfileCalibrationBucket] = Field(default_factory=list)
    # 按画像 + 持有周期组合分桶的结果列表，默认空列表。
    decision_profile_horizon: List[DecisionSignalProfileCalibrationBucket] = Field(default_factory=list)
    # 按画像 + 市场阶段组合分桶的结果列表，默认空列表。
    decision_profile_market_phase: List[DecisionSignalProfileCalibrationBucket] = Field(default_factory=list)
    # 按画像 + 数据质量等级组合分桶的结果列表，默认空列表。
    decision_profile_data_quality_level: List[DecisionSignalProfileCalibrationBucket] = Field(default_factory=list)
    # 按画像来源分桶的结果列表，默认空列表。
    profile_source: List[DecisionSignalProfileCalibrationBucket] = Field(default_factory=list)


class DecisionSignalProfileCalibration(BaseModel):
    """决策信号的画像校准结果。

    使用场景：统计接口返回样本量门槛与各维分解，门槛用于判断分桶结论是否具备统计意义。

    @author: Lensgcx (GaoCangxiong)
    """

    # 分桶结论被认为可解释所需的最小已完成样本数，至少 1。
    minimum_completed_sample_size: int = Field(..., ge=1)
    # 各维度的校准分桶明细，必填。
    breakdowns: DecisionSignalProfileCalibrationBreakdowns


class DecisionSignalOutcomeStatsResponse(BaseModel):
    """结果回测统计汇总响应（含引擎版本、跨度与完成度）。

    使用场景：统计页一次返回总体指标、按维度分桶与画像校准结果；engine_version 提示不同版本结果不可直接混合比较。

    @author: Lensgcx (GaoCangxiong)
    """

    # 结果回测引擎版本，用于区分不同口径的统计结果。
    engine_version: str
    # 本次统计覆盖的持有周期列表；未筛选时为 None。
    horizons: Optional[List[str]] = None
    # 本次统计覆盖的信号状态列表，默认空列表表示不限。
    statuses: List[str] = Field(default_factory=list)
    # 符合条件的记录总数或分桶样本总数。
    total: int
    # 已成功完成评估的样本数。
    completed: int
    # 因数据不足等原因无法评估的样本数。
    unable: int
    # 结果为命中的样本数。
    hit: int
    # 结果为未命中的样本数。
    miss: int
    # 结果为中性的样本数，不计入命中率分子。
    neutral: int
    # 命中率百分比；无有效样本时为 None。
    hit_rate_pct: Optional[float] = None
    # 标的平均涨跌幅百分比，作为策略表现对照基线。
    avg_stock_return_pct: Optional[float] = None
    # 无法评估原因码到出现次数的映射，默认空字典。
    unable_reasons: Dict[str, int] = Field(default_factory=dict)
    # 按维度名索引的统计分桶，默认空字典。
    breakdowns: Dict[str, List[DecisionSignalOutcomeStatsBucket]] = Field(default_factory=dict)
    # 决策画像校准结果，必填。
    profile_calibration: DecisionSignalProfileCalibration


class DecisionSignalFeedbackRequest(BaseModel):
    """提交决策信号反馈的请求体（反馈值、原因码与备注）。

    使用场景：用户对信号质量做有用/无用评价；source 标注 web 或 api，便于区分反馈入口。

    @author: Lensgcx (GaoCangxiong)
    """

    # 反馈值 useful / not_useful。
    feedback_value: DecisionSignalFeedbackValue
    # 反馈原因码，最长 64 字符；可选。
    reason_code: Optional[str] = Field(None, json_schema_extra={"maxLength": 64})
    # 用户填写的备注，最长 1000 字符；可选。
    note: Optional[str] = Field(None, json_schema_extra={"maxLength": 1000})
    # 反馈来源，默认 api；Web 前端应显式传 web。
    source: DecisionSignalFeedbackSource = "api"


class DecisionSignalFeedbackItem(BaseModel):
    """单条决策信号反馈记录。

    使用场景：反馈历史展示；旧记录可能只保留部分字段，故均可为 None。

    @author: Lensgcx (GaoCangxiong)
    """

    # 被反馈的信号 ID。
    signal_id: int
    # 反馈值 useful / not_useful。
    feedback_value: Optional[DecisionSignalFeedbackValue] = None
    # 反馈原因码，最长 64 字符；可选。
    reason_code: Optional[str] = None
    # 用户填写的备注，最长 1000 字符；可选。
    note: Optional[str] = None
    # 反馈来源 web / api，默认 api。
    source: Optional[DecisionSignalFeedbackSource] = None
    # 反馈创建时间；旧记录为 None。
    created_at: Optional[str] = None
    # 反馈更新时间；同一信号重复反馈会被刷新。
    updated_at: Optional[str] = None


class DecisionSignalItem(BaseModel):
    """决策信号详情项。

    使用场景：信号列表与详情；同时包含原始结论、交易计划、质量标记与生命周期状态，供前端完整还原一条信号。

    @author: Lensgcx (GaoCangxiong)
    """

    # 信号主键，供详情、状态更新与反馈关联。
    id: int
    # 规范股票代码，标识信号或评估关联的标的。
    stock_code: str
    # 股票名称；未取到或历史记录未保存时为 None。
    stock_name: Optional[str] = None
    # 标的市场标识，取值受 DecisionSignalMarket 约束。
    market: str
    # 信号来源类型：analysis / agent / alert / market_review / manual。
    source_type: str
    # 产生信号的 Agent 标识；非 Agent 来源为 None。
    source_agent: Optional[str] = None
    # 关联的分析报告 ID；无报告来源时为 None。
    source_report_id: Optional[int] = None
    # 诊断 trace ID，用于串联信号与原始分析链路。
    trace_id: Optional[str] = None
    # 决策画像，决定护栏与评分口径；省略时服务端回退默认画像。
    decision_profile: Optional[DecisionProfile] = None
    # 信号产生时的市场阶段。
    market_phase: Optional[str] = None
    # 触发信号生成的来源标识，用于追溯入口。
    trigger_source: str
    # 规范化的决策动作。
    action: str
    # 决策动作的展示文案，前端无需自行翻译枚举。
    action_label: Optional[str] = None
    # 信号置信度，范围 0~1；无法给出时为 None。
    confidence: Optional[float] = None
    # 信号评分，范围 0~100；无法给出时为 None。
    score: Optional[int] = None
    # 信号适用的持有周期。
    horizon: Optional[str] = None
    # 计划建仓区间下沿，必须大于 0 且非 inf/nan。
    entry_low: Optional[float] = None
    # 计划建仓区间上沿，必须大于 0 且非 inf/nan。
    entry_high: Optional[float] = None
    # 止损价，必须大于 0 且非 inf/nan。
    stop_loss: Optional[float] = None
    # 目标价，必须大于 0 且非 inf/nan。
    target_price: Optional[float] = None
    # 信号失效条件的结构化描述；未给出时为 None。
    invalidation: Optional[str] = None
    # 继续观察的条件；未给出时为 None。
    watch_conditions: Optional[str] = None
    # 给出该决策的理由；未给出时为 None。
    reason: Optional[str] = None
    # 风险提示摘要；未给出时为 None。
    risk_summary: Optional[str] = None
    # 催化剂摘要；未给出时为 None。
    catalyst_summary: Optional[str] = None
    # 支撑结论的证据集合；结构随来源变化。
    evidence: Optional[Any] = None
    # 输入数据质量摘要；旧记录为 None。
    data_quality_summary: Optional[Any] = None
    # 交易计划完整度，必填；unknown 用于旧数据。
    plan_quality: str
    # 信号当前状态，必填。
    status: str
    # 信号过期时间；不过期时为 None。
    expires_at: Optional[str] = None
    # 信号创建时间；旧记录为 None。
    created_at: Optional[str] = None
    # 信号更新时间；旧记录为 None。
    updated_at: Optional[str] = None
    # 附加元数据；结构不固定故保持 Any。
    metadata: Optional[Any] = None


class DecisionSignalMutationResponse(BaseModel):
    """决策信号创建或变更响应（含是否为新建）。

    使用场景：幂等写入端点返回，created 区分新建与命中已有记录。

    @author: Lensgcx (GaoCangxiong)
    """

    # 创建或复用后的信号详情，必填。
    item: DecisionSignalItem
    # 是否新建了信号；False 表示命中已有记录并复用。
    created: bool


class DecisionSignalReassessResponse(BaseModel):
    """决策信号重评估响应（预览、落库项与持久化状态）。

    使用场景：重评估端点；未要求持久化时只有 preview，blocked_reason 说明护栏为何拒绝落库。

    @author: Lensgcx (GaoCangxiong)
    """

    # 重评估预览结果；持久化后也可能一并返回供前端对照。
    preview: Optional[DecisionSignalPreview] = None
    # 落库后的信号详情；未持久化时为 None。
    item: Optional[DecisionSignalItem] = None
    # 是否新建了信号记录；默认 False。
    created: bool = False
    # 持久化结果 created / existing / refreshed；未要求持久化为 None。
    persist_status: Optional[Literal["created", "existing", "refreshed"]] = None
    # 非阻断性警告项列表，默认空列表。
    warnings: List[DecisionSignalWarning] = Field(default_factory=list)
    # 护栏或前置校验拒绝落库的原因；正常时为 None。
    blocked_reason: Optional[str] = None


class DecisionSignalReassessErrorResponse(BaseModel):
    """决策信号重评估的错误响应（不支持的报告类型/快照或护栏拦截）。

    使用场景：重评估失败时返回具名错误码；error 限定三种原因，便于前端给出针对性提示。

    @author: Lensgcx (GaoCangxiong)
    """

    # 具名错误码，限定三种重评估失败原因，便于前端分支提示。
    error: Literal[
        "unsupported_report_type",
        "unsupported_report_snapshot",
        "guardrail_blocked",
    ]
    # 面向用户的说明文案。
    message: str
    # 护栏或前置校验拒绝落库的原因；正常时为 None。
    blocked_reason: Optional[str] = None
    # 非阻断性警告项列表，默认空列表。
    warnings: List[DecisionSignalWarning] = Field(default_factory=list)


class DecisionSignalListResponse(BaseModel):
    """决策信号分页列表响应。

    使用场景：信号列表按页拉取，total 为符合条件的信号总数。

    @author: Lensgcx (GaoCangxiong)
    """

    # 结果或信号列表；无数据为空列表。
    items: List[DecisionSignalItem] = Field(default_factory=list)
    # 符合条件的记录总数或分桶样本总数。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int
