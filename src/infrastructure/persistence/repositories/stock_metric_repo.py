# -*- coding: utf-8 -*-
"""股票度量视图离线因子仓储。

只做 ``stock_metric_*`` 表的读写，写事务统一走
:class:`~src.storage.DatabaseManager` 的 ``_run_write_transaction``。
离线因子缺失时（表未建 / 任务未跑）调用方应优雅降级——本仓储的读取方法
均吞掉异常并返回空结果，不在查询主链路上抛错。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.infrastructure.persistence.base import Base
from src.infrastructure.persistence.models.stock_metric import (
    StockMetricCalcRun,
    StockMetricDaily,
    StockMetricPeriod,
)

if TYPE_CHECKING:
    from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

STOCK_METRIC_MODELS = (StockMetricPeriod, StockMetricCalcRun, StockMetricDaily)


class StockMetricRepository:
    """``stock_metric_*`` 表读写入口。"""

    def __init__(self, db_manager: "DatabaseManager") -> None:
        self._db = db_manager

    def init_tables(self) -> None:
        """幂等建表（委托给 DatabaseManager 引擎）。失败仅记录，不阻断主链路。"""
        try:
            with self._db.get_session() as session:
                Base.metadata.create_all(
                    bind=session.get_bind(),
                    tables=[m.__table__ for m in STOCK_METRIC_MODELS],
                )
        except Exception as exc:  # pragma: no cover - 建表兜底
            logger.warning("[stock_metric] 建表失败(可忽略，启动期会再次尝试): %s", exc)

    def fetch_latest_factors(self, market: str) -> Dict[str, Dict[str, Optional[float]]]:
        """取某市场 is_latest 离线因子，返回 {code: {eps_ttm_yoy_pct, analyst_rating}}。"""
        result: Dict[str, Dict[str, Optional[float]]] = {}
        try:
            with self._db.get_session() as session:
                rows = session.execute(
                    select(StockMetricPeriod).where(
                        and_(
                            StockMetricPeriod.market == market,
                            StockMetricPeriod.is_latest.is_(True),
                        )
                    )
                ).scalars().all()
                for r in rows:
                    result[r.code] = {
                        "eps_ttm_yoy_pct": r.eps_ttm_yoy_pct,
                        "analyst_rating": r.analyst_rating,
                    }
        except Exception as exc:  # 表不存在 / 连接异常 -> 优雅降级
            logger.info("[stock_metric] 读取离线因子失败，按无离线数据降级: %s", exc)
        return result

    def fetch_latest_as_of_date(self, market: str) -> Optional[str]:
        """取某市场 is_latest 行的最新报告期（ISO 日期串）；无数据返回 None。"""
        try:
            with self._db.get_session() as session:
                value = session.execute(
                    select(func.max(StockMetricPeriod.report_date)).where(
                        and_(
                            StockMetricPeriod.market == market,
                            StockMetricPeriod.is_latest.is_(True),
                        )
                    )
                ).scalar_one_or_none()
                if value is None:
                    return None
                return value.isoformat() if hasattr(value, "isoformat") else str(value)[:10]
        except Exception as exc:  # 表不存在 / 连接异常 -> 优雅降级
            logger.info("[stock_metric] 读取离线因子基准日失败，按无数据降级: %s", exc)
            return None

    def upsert_periods(self, rows: List[Dict[str, object]]) -> int:
        """批量 upsert ``stock_metric_period``，返回写入行数。"""
        if not rows:
            return 0
        market = str(rows[0].get("market", "cn"))

        def _write(session: Session) -> int:
            codes = {str(r.get("code")) for r in rows}
            # 先把同 (market, code) 的旧 is_latest 置否，保证每代码仅一条最新
            session.execute(
                update(StockMetricPeriod)
                .where(
                    and_(
                        StockMetricPeriod.market == market,
                        StockMetricPeriod.code.in_(codes),
                        StockMetricPeriod.is_latest.is_(True),
                    )
                )
                .values(is_latest=False)
            )
            written = 0
            for i in range(0, len(rows), 50):
                chunk = rows[i : i + 50]
                stmt = sqlite_insert(StockMetricPeriod).values(chunk)
                excluded = stmt.excluded
                session.execute(
                    stmt.on_conflict_do_update(
                        index_elements=["market", "code", "report_date"],
                        set_={
                            "eps_diluted": excluded.eps_diluted,
                            "eps_ttm_yoy_pct": excluded.eps_ttm_yoy_pct,
                            "revenue": excluded.revenue,
                            "revenue_yoy_pct": excluded.revenue_yoy_pct,
                            "roe_pct": excluded.roe_pct,
                            "pb_ratio": excluded.pb_ratio,
                            "ps_ratio_ttm": excluded.ps_ratio_ttm,
                            "dividend_yield_pct": excluded.dividend_yield_pct,
                            "analyst_rating": excluded.analyst_rating,
                            "is_latest": excluded.is_latest,
                            "created_at": excluded.created_at,
                        },
                    )
                )
                written += len(chunk)
            return written

        try:
            return self._db._run_write_transaction("stock_metric_upsert_periods", _write)
        except Exception as exc:
            logger.error("[stock_metric] upsert_periods 失败: %s", exc)
            raise

    def record_calc_run(
        self, status: str, rows_written: int, note: Optional[str] = None, market: str = "cn"
    ) -> None:
        """写入一条 ``stock_metric_calc_run`` 跑批记录。"""
        try:
            with self._db.get_session() as session:
                session.add(
                    StockMetricCalcRun(
                        market=market, status=status, rows_written=rows_written, note=note
                    )
                )
                session.commit()
        except Exception as exc:  # pragma: no cover - 记录失败不影响主流程
            logger.warning("[stock_metric] 写 calc_run 失败: %s", exc)
