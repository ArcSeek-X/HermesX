# -*- coding: utf-8 -*-
"""告警领域包。

对外暴露告警条件与判定规则（§3 line 74「alert/ 告警条件与判定」；无框架 / ORM /
存储 / IO / 数据源依赖，仅 stdlib/pandas）。当前成员：

- :mod:`src.domain.alert.alert_indicators`：技术指标类告警（MA/RSI/MACD/KDJ/CCI）
  的参数归一化、所需 K 线量推导与阈值/交叉判定，供 AlertService P5 规则复用。
"""

from __future__ import annotations

from src.domain.alert.alert_indicators import (
    ABOVE_BELOW_DIRECTIONS,
    CROSS_DIRECTIONS,
    TECHNICAL_ALERT_TYPES,
    IndicatorEvaluation,
    TechnicalIndicatorAlert,
    calculate_rsi,
    compute_required_bars,
    compute_requested_days,
    evaluate_indicator_alert,
    normalize_indicator_parameters,
    normalize_ohlcv,
    threshold_for_indicator,
)

__all__ = [
    "ABOVE_BELOW_DIRECTIONS",
    "CROSS_DIRECTIONS",
    "TECHNICAL_ALERT_TYPES",
    "IndicatorEvaluation",
    "TechnicalIndicatorAlert",
    "calculate_rsi",
    "compute_required_bars",
    "compute_requested_days",
    "evaluate_indicator_alert",
    "normalize_indicator_parameters",
    "normalize_ohlcv",
    "threshold_for_indicator",
]
