# -*- coding: utf-8 -*-
"""股票度量视图离线因子 ORM 模型。

一期仅 ``stock_metric_period``（财报期离线因子）与 ``stock_metric_calc_run``
（跑批记录）会被写入；``stock_metric_daily``（每日复算）按设计文档 §6.1 列为二期。
所有模型注册在 ``src.infrastructure.persistence.base.Base`` 唯一 metadata 上。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.base import Base, utc_naive_now

TABLE_PREFIX = "stock_metric"


class StockMetricPeriod(Base):
    """财报期离线因子（cn 专属；epsGrowthTtmYoyPct / analystRating 等离线列来源）。"""

    __tablename__ = f"{TABLE_PREFIX}_period"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False, default="cn")
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    eps_diluted: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eps_ttm_yoy_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    revenue_yoy_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roe_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ps_ratio_ttm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dividend_yield_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analyst_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_naive_now)

    __table_args__ = (
        UniqueConstraint("market", "code", "report_date", name="uq_stock_metric_period_mc_rpt"),
    )


class StockMetricCalcRun(Base):
    """离线因子跑批记录（季频任务写入，便于可观测与降级判定）。"""

    __tablename__ = f"{TABLE_PREFIX}_calc_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_naive_now)
    market: Mapped[str] = mapped_column(String(8), nullable=False, default="cn")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="eastmoney")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class StockMetricDaily(Base):
    """每日复算离线因子（二期；一期不写入）。"""

    __tablename__ = f"{TABLE_PREFIX}_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False, default="cn")
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    eps_growth_ttm_yoy_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analyst_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_naive_now)

    __table_args__ = (
        UniqueConstraint("market", "code", "as_of_date", name="uq_stock_metric_daily_mc_date"),
    )
