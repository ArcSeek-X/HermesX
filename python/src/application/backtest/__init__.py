# -*- coding: utf-8 -*-
"""回测用例包：编排实现与端口。

回测编排实现落在 :mod:`src.application.backtest.service`
（:class:`BacktestService`），本包同时声明用例对外需要的端口
:class:`DailyBarRefillPort`，其数据源适配器实现落在
:mod:`src.infrastructure.providers.backtest_daily_refill`，由
:mod:`src.bootstrap.backtest` 装配注入。
"""

from __future__ import annotations

from src.application.backtest.ports import DailyBarRefillPort

__all__ = ["DailyBarRefillPort"]
