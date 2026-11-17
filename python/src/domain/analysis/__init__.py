# -*- coding: utf-8 -*-
"""分析领域包。

对外暴露可离线纯算的分析指标与业务规则（无框架 / ORM / 存储 / IO / 数据源依赖）。
当前成员：

- :mod:`src.domain.analysis.scanner_indicators`：技术信号扫描的 8 个信号判定纯函数
  （MA/MACD 金叉死叉、RSI 超买超卖、BOLL 上下轨），入参为升序日 K 序列。
"""

from __future__ import annotations

from src.domain.analysis.scanner_indicators import (
    MIN_BARS,
    SIGNAL_KEYS,
    SIGNAL_LABELS,
    detect_signals,
)

__all__ = [
    "MIN_BARS",
    "SIGNAL_KEYS",
    "SIGNAL_LABELS",
    "detect_signals",
]
