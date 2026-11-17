# -*- coding: utf-8 -*-
"""
@file: market_phase.py
@description: 市场阶段摘要模型：随分析报告 meta 与告警触发记录输出的低敏感度元数据，描述交易时段状态、日线新鲜度与阶段推断降级原因；被 analysis / backtest / alerts / decision_signals 等 schema 复用。
@author: Lensgcx (GaoCangxiong)

Market phase summary schemas.

Defines the low-sensitivity trading-session metadata attached to report
meta and alert triggers, including phase classification, bar freshness
and degraded-inference warning codes.

市场阶段是分析结论时效性判断的依据，前端据此提示「盘中未完成日线」等风险。
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# 市场阶段取值闭包：覆盖盘前、盘中、午休、收盘竞价、盘后、非交易日与未知；unknown 供降级路径兜底。
MarketPhaseValue = Literal[
    "premarket",        # 开盘前集合竞价及等待开盘时段
    "intraday",         # 连续竞价交易时段
    "lunch_break",      # 午间休市，A 股特有
    "closing_auction",  # 收盘集合竞价时段
    "postmarket",       # 收盘后至日线落库完成前
    "non_trading",      # 非交易日（周末、节假日）
    "unknown",          # 信息不足或推断失败时的降级取值
]


class MarketPhaseSummary(BaseModel):
    """Low-sensitivity market phase metadata exposed on report meta.

    使用场景：附加在分析结论与告警记录上，帮助调用方判断数据是否来自未收盘日线、以及阶段推断是否发生降级；仅含公开可展示字段，不携带持仓或账户信息。

    @author: Lensgcx (GaoCangxiong)
    """

    # 市场区域标识（如 CN / HK / US）；无法判定时为 None。
    market: Optional[str] = Field(None, description="市场区域")
    # 当前所处交易阶段，取值受 MarketPhaseValue 约束，是时效性判断的主字段。
    phase: MarketPhaseValue = Field(..., description="市场阶段")
    # 市场所在时区的本地时间，用于解释阶段判定结果；缺失时为 None。
    market_local_time: Optional[str] = Field(None, description="市场本地时间")
    # 市场本地交易日；跨时区场景下可能与系统日期不同。
    session_date: Optional[str] = Field(None, description="市场本地日期")
    # 当前可复用的最新完整日线日期，盘中会滞后于 session_date。
    effective_daily_bar_date: Optional[str] = Field(None, description="最新可复用完整日线日期")
    # 是否为交易日；节假日与周末为 False，判定失败时为 None。
    is_trading_day: Optional[bool] = Field(None, description="是否交易日")
    # 判定时刻是否处于连续交易时段，用于提示行情实时性。
    is_market_open_now: Optional[bool] = Field(None, description="当前是否开市")
    # 最新日线是否可能尚未走完；为 True 时分析结论需标注盘中数据风险。
    is_partial_bar: Optional[bool] = Field(None, description="最新日线是否可能未完成")
    # 距下次开盘的分钟数；已开盘或非交易日时为 None。
    minutes_to_open: Optional[int] = Field(None, description="距离开盘分钟数")
    # 距本次收盘的分钟数；休市时为 None。
    minutes_to_close: Optional[int] = Field(None, description="距离收盘分钟数")
    # 触发本次阶段推断的来源（如定时任务、手动分析），用于问题追溯。
    trigger_source: Optional[str] = Field(None, description="触发来源")
    # 本次分析的意图标识，便于区分盘前预判与盘后复盘。
    analysis_intent: Optional[str] = Field(None, description="分析意图")
    # 阶段推断发生降级时产生的告警码列表；无降级时为空列表，前端可据此显示提示。
    warnings: List[str] = Field(default_factory=list, description="阶段推断降级告警码")
