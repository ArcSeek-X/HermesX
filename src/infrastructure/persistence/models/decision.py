# -*- coding: utf-8 -*-
"""决策信号域模型：信号本体、结果、反馈与 skill 观点样本/结果。

本模块只声明 ORM 表结构；全部模型注册在 `src.infrastructure.persistence.base.Base`
这唯一一个 metadata 上。导入本模块即完成注册，不要在别处再建 Base。
"""


from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    Text,
)

from src.infrastructure.persistence.base import Base, utc_naive_now


class DecisionSignalRecord(Base):
    """AI 决策信号资产。

    记录一次决策信号的核心结论与上下文，供后续结果回填
    （:class:`DecisionSignalOutcomeRecord`）与人工反馈
    （:class:`DecisionSignalFeedbackRecord`）关联，形成「信号 -> 结果 -> 反馈」闭环。

    信号一旦落库即视为**不可变快照**：后续行情变化不回改本表，
    而是写入对应的结果表，以保证事后复盘能还原当时的判断依据。
    """

    __tablename__ = 'decision_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(16), nullable=False, index=True)
    stock_name = Column(String(64))
    market = Column(String(8), nullable=False, index=True)
    source_type = Column(String(32), nullable=False, index=True)
    source_agent = Column(String(64))
    source_report_id = Column(Integer, index=True)
    trace_id = Column(String(64), index=True)
    decision_profile = Column(String(16), index=True)
    market_phase = Column(String(24), index=True)
    trigger_source = Column(String(64), nullable=False, index=True)
    action = Column(String(16), nullable=False, index=True)
    action_label = Column(String(32))
    confidence = Column(Float)
    score = Column(Integer)
    horizon = Column(String(16), index=True)
    entry_low = Column(Float)
    entry_high = Column(Float)
    stop_loss = Column(Float)
    target_price = Column(Float)
    invalidation = Column(Text)
    watch_conditions = Column(Text)
    reason = Column(Text)
    risk_summary = Column(Text)
    catalyst_summary = Column(Text)
    evidence_json = Column(Text)
    data_quality_summary_json = Column(Text)
    plan_quality = Column(String(16), nullable=False, default='unknown', index=True)
    status = Column(String(16), nullable=False, default='active', index=True)
    expires_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=utc_naive_now, index=True)
    updated_at = Column(DateTime, default=utc_naive_now, onupdate=utc_naive_now, index=True)
    metadata_json = Column(Text)

    __table_args__ = (
        Index('ix_decision_signal_stock_status_time', 'stock_code', 'status', 'created_at'),
        Index('ix_decision_signal_market_status_time', 'market', 'status', 'created_at'),
        Index(
            'ix_decision_signal_report_type_market_stock_action_horizon_phase',
            'source_report_id',
            'source_type',
            'market',
            'stock_code',
            'action',
            'horizon',
            'market_phase',
        ),
        Index(
            'ix_decision_signal_trace_type_market_stock_action_horizon_phase',
            'trace_id',
            'source_type',
            'market',
            'stock_code',
            'action',
            'horizon',
            'market_phase',
        ),
        Index(
            'ix_decision_signal_report_type_market_stock_profile_action_horizon_phase',
            'source_report_id',
            'source_type',
            'market',
            'stock_code',
            'decision_profile',
            'action',
            'horizon',
            'market_phase',
        ),
        Index(
            'ix_decision_signal_trace_type_market_stock_profile_action_horizon_phase',
            'trace_id',
            'source_type',
            'market',
            'stock_code',
            'decision_profile',
            'action',
            'horizon',
            'market_phase',
        ),
        Index(
            'ix_decision_signal_market_stock_profile_created',
            'market',
            'stock_code',
            'decision_profile',
            'created_at',
        ),
    )


class DecisionSignalOutcomeRecord(Base):
    """单条决策信号的前瞻表现（按评估周期记录）。

    与 :class:`DecisionSignalRecord` 为多对一：一条信号可有多个评估周期
    （如 T+5 / T+10）的结果。
    """

    __tablename__ = 'decision_signal_outcomes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, nullable=False, index=True)
    horizon = Column(String(16), nullable=False, index=True)
    engine_version = Column(String(32), nullable=False, index=True)
    eval_status = Column(String(24), nullable=False, default='unable', index=True)
    outcome = Column(String(16), index=True)
    direction_expected = Column(String(16), index=True)
    direction_correct = Column(Boolean)
    unable_reason = Column(String(64), index=True)
    anchor_date = Column(Date, index=True)
    eval_window_days = Column(Integer)
    start_price = Column(Float)
    end_close = Column(Float)
    max_high = Column(Float)
    min_low = Column(Float)
    stock_return_pct = Column(Float)

    action = Column(String(16), index=True)
    market = Column(String(8), index=True)
    market_phase = Column(String(24), index=True)
    source_type = Column(String(32), index=True)
    source_agent = Column(String(64), index=True)
    plan_quality = Column(String(16), index=True)
    data_quality_level = Column(String(24), index=True)
    holding_state = Column(String(16), nullable=False, default='unknown', index=True)

    created_at = Column(DateTime, default=utc_naive_now, index=True)
    updated_at = Column(DateTime, default=utc_naive_now, onupdate=utc_naive_now, index=True)

    __table_args__ = (
        UniqueConstraint('signal_id', 'horizon', 'engine_version', name='uix_decision_signal_outcome_key'),
        Index('ix_decision_signal_outcome_stats_action', 'engine_version', 'action', 'horizon'),
        Index('ix_decision_signal_outcome_stats_market', 'engine_version', 'market', 'horizon'),
    )


class DecisionSignalFeedbackRecord(Base):
    """用户对决策信号的最新反馈（每条信号至多一条，以最后反馈为准）。"""

    __tablename__ = 'decision_signal_feedback'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, nullable=False, unique=True, index=True)
    feedback_value = Column(String(16), nullable=False, index=True)
    reason_code = Column(String(64), index=True)
    note = Column(Text)
    source = Column(String(16), nullable=False, default='api', index=True)
    created_at = Column(DateTime, default=utc_naive_now, index=True)
    updated_at = Column(DateTime, default=utc_naive_now, onupdate=utc_naive_now, index=True)


class SkillOpinionSampleRecord(Base):
    """SkillAgent 观点样本（不可变、低敏感度）。

    只记录观点本身与归因所需的最小字段，不落敏感上下文；
    样本写入后不再修改，表现评估由 :class:`SkillOpinionOutcomeRecord` 另行记录。
    """

    __tablename__ = 'skill_opinion_samples'

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_history_id = Column(
        Integer,
        ForeignKey('analysis_history.id'),
        nullable=False,
        index=True,
    )
    stock_code = Column(String(16), nullable=False, index=True)
    skill_id = Column(String(128), nullable=False, index=True)
    skill_version = Column(String(64), index=True)
    signal = Column(String(16), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    horizon = Column(String(16), index=True)
    data_quality_level = Column(String(24), index=True)
    opinion_created_at = Column(DateTime, index=True)
    sample_schema_version = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_naive_now, index=True)

    __table_args__ = (
        UniqueConstraint(
            'analysis_history_id',
            'skill_id',
            'sample_schema_version',
            name='uix_skill_opinion_sample_key',
        ),
        Index(
            'ix_skill_opinion_sample_skill_horizon_created',
            'skill_id',
            'horizon',
            'created_at',
        ),
        Index(
            'ix_skill_opinion_sample_stock_created',
            'stock_code',
            'created_at',
        ),
    )


class SkillOpinionOutcomeRecord(Base):
    """单条 SkillAgent 观点样本在某一评估周期下的前瞻表现。

    与 :class:`SkillOpinionSampleRecord` 为多对一：一个观点样本可对应
    多个评估周期的结果，用于评估该 SkillAgent 的实际表现。
    """

    __tablename__ = 'skill_opinion_outcomes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_opinion_sample_id = Column(
        Integer,
        ForeignKey('skill_opinion_samples.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    horizon = Column(String(16), nullable=False, index=True)
    engine_version = Column(String(32), nullable=False, index=True)
    eval_status = Column(String(24), nullable=False, default='pending', index=True)
    outcome = Column(String(16), index=True)
    direction_correct = Column(Boolean)
    unable_reason = Column(String(64), index=True)
    analysis_date = Column(Date, index=True)
    start_trade_date = Column(Date, index=True)
    end_trade_date = Column(Date, index=True)
    start_price = Column(Float)
    end_close = Column(Float)
    stock_return_pct = Column(Float)
    directional_return_pct = Column(Float)
    created_at = Column(DateTime, default=utc_naive_now, index=True)
    updated_at = Column(DateTime, default=utc_naive_now, onupdate=utc_naive_now, index=True)

    __table_args__ = (
        UniqueConstraint(
            'skill_opinion_sample_id',
            'horizon',
            'engine_version',
            name='uix_skill_opinion_outcome_key',
        ),
        CheckConstraint(
            "horizon IN ('1d', '3d', '5d', '10d')",
            name='ck_skill_opinion_outcome_horizon',
        ),
        CheckConstraint(
            "eval_status IN ('pending', 'evaluated', 'observational', 'unable')",
            name='ck_skill_opinion_outcome_eval_status',
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('hit', 'miss', 'observational')",
            name='ck_skill_opinion_outcome_value',
        ),
        CheckConstraint(
            "(eval_status IN ('pending', 'unable') "
            "AND outcome IS NULL "
            "AND direction_correct IS NULL "
            "AND directional_return_pct IS NULL) "
            "OR (eval_status = 'observational' "
            "AND outcome = 'observational' "
            "AND direction_correct IS NULL "
            "AND directional_return_pct IS NULL) "
            "OR (eval_status = 'evaluated' "
            "AND outcome IN ('hit', 'miss') "
            "AND direction_correct IS NOT NULL "
            "AND directional_return_pct IS NOT NULL)",
            name='ck_skill_opinion_outcome_state_fields',
        ),
        Index(
            'ix_skill_opinion_outcome_candidate',
            'engine_version',
            'eval_status',
            'updated_at',
        ),
        Index(
            'ix_skill_opinion_outcome_horizon_status',
            'engine_version',
            'horizon',
            'eval_status',
        ),
    )
