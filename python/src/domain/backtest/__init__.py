# -*- coding: utf-8 -*-
"""回测领域包。

对外暴露回测用例与仓储共享的记录类型（领域 DTO），供应用层构造 / 读取、
基础设施层做 ORM 映射；本包不含任何框架 / ORM / 存储依赖。
"""

from __future__ import annotations

from src.domain.backtest.records import (
    BacktestResultRecord,
    BacktestSummaryRecord,
)

__all__ = [
    "BacktestResultRecord",
    "BacktestSummaryRecord",
]
