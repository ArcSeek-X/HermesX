# -*- coding: utf-8 -*-
"""分析主流程持久化适配器：实现 ``AnalysisPipelinePersistencePort``。

逐方法委托 ``DatabaseManager`` 的公开面，不重新聚合仓储：

- 宿主上的 ``has_today_data`` / ``save_daily_data`` / ``get_analysis_context`` 等本身
  已是薄委托（内部转 ``MarketDataRepository`` 等），再包一层会引入双重装配点；
- ``analyze_ma_status`` 只存在于宿主公开面（仓储层无同名方法，仅内部复用
  ``_analyze_ma_status``），单独用仓储拼装会改变均线判定口径。

因此本适配器把“与原 ``get_db()`` 逐字一致”作为首要约束，只承担依赖方向倒置：
``src.application`` 不 import ``src.storage``，由本适配器与
``src.bootstrap.analysis.configure_analysis_pipeline_persistence()`` 承接。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from src.storage import DatabaseManager


class DatabaseManagerPipelinePersistenceAdapter:
    """把 ``DatabaseManager`` 适配为 pipeline 所需的持久化端口。"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self._db = db_manager or DatabaseManager.get_instance()

    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        return self._db.has_today_data(code, target_date)

    def save_daily_data(self, df: Any, code: str, data_source: str = "Unknown") -> int:
        return self._db.save_daily_data(df, code, data_source)

    def save_fundamental_snapshot(
        self,
        query_id: str,
        code: str,
        payload: Optional[Dict[str, Any]],
        source_chain: Optional[Any] = None,
        coverage: Optional[Any] = None,
    ) -> int:
        return self._db.save_fundamental_snapshot(
            query_id=query_id,
            code=code,
            payload=payload,
            source_chain=source_chain,
            coverage=coverage,
        )

    def get_data_range(
        self, code: str, start_date: date, end_date: date
    ) -> List[Any]:
        return self._db.get_data_range(code, start_date, end_date)

    def save_news_intel(
        self,
        code: str,
        name: str,
        dimension: str,
        query: str,
        response: Any,
        query_context: Optional[Dict[str, str]] = None,
    ) -> int:
        return self._db.save_news_intel(
            code=code,
            name=name,
            dimension=dimension,
            query=query,
            response=response,
            query_context=query_context,
        )

    def save_analysis_history(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str],
        context_snapshot: Optional[Dict[str, Any]] = None,
        save_snapshot: bool = True,
    ) -> int:
        return self._db.save_analysis_history(
            result=result,
            query_id=query_id,
            report_type=report_type,
            news_content=news_content,
            context_snapshot=context_snapshot,
            save_snapshot=save_snapshot,
        )

    def get_analysis_history(
        self,
        code: Optional[str] = None,
        query_id: Optional[str] = None,
        days: int = 30,
        limit: int = 50,
        exclude_query_id: Optional[str] = None,
    ) -> List[Any]:
        return self._db.get_analysis_history(
            code=code,
            query_id=query_id,
            days=days,
            limit=limit,
            exclude_query_id=exclude_query_id,
        )

    def update_analysis_history_diagnostics(
        self,
        *,
        query_id: str,
        code: Optional[str] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        notification_runs: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        return self._db.update_analysis_history_diagnostics(
            query_id=query_id,
            code=code,
            diagnostics=diagnostics,
            notification_runs=notification_runs,
        )

    def get_analysis_context(
        self, code: str, target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        return self._db.get_analysis_context(code, target_date)

    def analyze_ma_status(self, data: Any) -> str:
        return self._db.analyze_ma_status(data)
