# -*- coding: utf-8 -*-
"""回测领域的记录类型（领域 DTO）。

镜像持久化模型 ``BacktestResult`` / ``BacktestSummary`` 的字段形状，但**不依赖
SQLAlchemy**：属性名与 ORM 列名逐一对齐，使 ``src/core/backtest_engine.py`` 的
``BacktestResultLike`` Protocol（鸭子类型消费）与用例层的读取无需改名。

归属与边界（ARCHITECTURE_TARGET §2）：
- 用例层（``src/application/backtest/service``）只构造 / 读取这些记录，不引用 ORM；
- ORM ↔ 记录的双向映射集中在
  ``src/infrastructure/persistence/repositories/backtest_repository.py``（仓储层允许
  同时认识 ORM 与领域）；
- 默认值对齐 ORM 列默认（计数为 0；``eval_window_days=10`` / ``engine_version='v1'`` /
  ``eval_status='pending'`` 为列默认，其余可空字段默认 ``None``），保证服务层按
  关键字部分构造时其余字段仍与建列默认一致。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class BacktestResultRecord:
    """单条分析记录的回测结果（领域记录，非 ORM 对象）。"""

    id: Optional[int] = None
    analysis_history_id: Optional[int] = None
    code: Optional[str] = None
    analysis_date: Optional[date] = None
    eval_window_days: int = 10
    engine_version: str = "v1"
    eval_status: str = "pending"
    evaluated_at: Optional[datetime] = None
    operation_advice: Optional[str] = None
    position_recommendation: Optional[str] = None
    start_price: Optional[float] = None
    end_close: Optional[float] = None
    max_high: Optional[float] = None
    min_low: Optional[float] = None
    stock_return_pct: Optional[float] = None
    direction_expected: Optional[str] = None
    direction_correct: Optional[bool] = None
    outcome: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    hit_stop_loss: Optional[bool] = None
    hit_take_profit: Optional[bool] = None
    first_hit: Optional[str] = None
    first_hit_date: Optional[date] = None
    first_hit_trading_days: Optional[int] = None
    simulated_entry_price: Optional[float] = None
    simulated_exit_price: Optional[float] = None
    simulated_exit_reason: Optional[str] = None
    simulated_return_pct: Optional[float] = None


@dataclass
class BacktestSummaryRecord:
    """回测汇总指标（按股票或全局，领域记录，非 ORM 对象）。"""

    id: Optional[int] = None
    scope: Optional[str] = None
    code: Optional[str] = None
    eval_window_days: int = 10
    engine_version: str = "v1"
    computed_at: Optional[datetime] = None
    total_evaluations: int = 0
    completed_count: int = 0
    insufficient_count: int = 0
    long_count: int = 0
    cash_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    neutral_count: int = 0
    direction_accuracy_pct: Optional[float] = None
    win_rate_pct: Optional[float] = None
    neutral_rate_pct: Optional[float] = None
    avg_stock_return_pct: Optional[float] = None
    avg_simulated_return_pct: Optional[float] = None
    stop_loss_trigger_rate: Optional[float] = None
    take_profit_trigger_rate: Optional[float] = None
    ambiguous_rate: Optional[float] = None
    avg_days_to_first_hit: Optional[float] = None
    advice_breakdown_json: Optional[str] = None
    diagnostics_json: Optional[str] = None
