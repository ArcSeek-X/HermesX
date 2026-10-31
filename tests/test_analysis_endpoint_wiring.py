# -*- coding: utf-8 -*-
"""``api/v1/endpoints/analysis.py`` 的依赖接线与端口语义回归。

该文件曾有 4 处跨层依赖：3 处 ``from src.storage import DatabaseManager``
（历史运行流、状态查询、同步分析回填）与 1 处 ``data_provider.base``
（股票代码归一化）。现在它们分别收敛到
``HistoryQueryService``（经 ``Depends(get_history_query_service)`` 注入）和
``src.application.quote.stock_code_utils`` 的两个包装函数。本文件锁定这条契约。
"""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from api.deps import get_history_query_service
from api.v1.endpoints import analysis
from data_provider.base import canonical_stock_code, normalize_stock_code
from src.application.history import HistoryQueryService
from src.infrastructure.indexing.stock_code_normalizer import (
    DataProviderStockCodeNormalizer,
)
from src.application.quote.stock_code_utils import (
    canonical_stock_code_for_analysis,
    normalize_stock_code_for_analysis,
)


class FakeHistoryRepository:
    """记录调用参数的端口替身。"""

    def __init__(self, record: Optional[Any] = None, fundamental: Optional[Dict[str, Any]] = None) -> None:
        self.record = record
        self.fundamental = fundamental
        self.calls: List[tuple] = []

    def get_latest_analysis_by_query_id(
        self,
        query_id: str,
        *,
        code: Optional[str] = None,
        report_type: Optional[str] = None,
    ):
        self.calls.append(("get_latest_analysis_by_query_id", query_id, code, report_type))
        return self.record

    def get_latest_fundamental_snapshot(self, *, query_id: str, code: str):
        self.calls.append(("get_latest_fundamental_snapshot", query_id, code))
        return self.fundamental


class AnalysisEndpointWiringTestCase(unittest.TestCase):
    def _service(self, **kwargs) -> tuple[HistoryQueryService, FakeHistoryRepository]:
        repository = FakeHistoryRepository(**kwargs)
        return (
            HistoryQueryService(
                repository=repository,
                code_normalizer=DataProviderStockCodeNormalizer(),
            ),
            repository,
        )

    def test_endpoint_module_has_no_direct_persistence_or_provider_import(self) -> None:
        source = Path(analysis.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "from src.storage import",
            "from src.repositories import",
            "from src.infrastructure import",
            "from data_provider.base import",
            "DatabaseManager",
        ):
            self.assertNotIn(forbidden, source)

    def test_status_and_flow_routes_depend_on_history_query_service(self) -> None:
        for endpoint in (analysis.get_analysis_status, analysis.get_task_run_flow):
            param = inspect.signature(endpoint).parameters.get("history_service")
            self.assertIsNotNone(param, endpoint.__name__)
            self.assertEqual(param.default.dependency, get_history_query_service)

    def test_load_run_flow_forwards_filters_to_service(self) -> None:
        service, repository = self._service()

        result = analysis._load_history_run_flow_by_query_id(
            "q-flow",
            history_service=service,
            code="600519",
            report_type="full",
        )

        self.assertIsNone(result)
        # 运行流记录解析复用 HistoryService，最终落到端口的 query_id 查询
        self.assertEqual(
            repository.calls,
            [("get_latest_analysis_by_query_id", "q-flow", "600519", "full")],
        )

    def test_load_run_flow_fails_open_only_when_requested(self) -> None:
        service, _ = self._service()
        service.get_run_flow = MagicMock(side_effect=RuntimeError("boom"))

        self.assertIsNone(
            analysis._load_history_run_flow_by_query_id(
                "q-flow", history_service=service, fail_open=True
            )
        )
        with self.assertRaises(RuntimeError):
            analysis._load_history_run_flow_by_query_id("q-flow", history_service=service)

    def test_load_sync_sources_maps_record_and_fundamental_snapshot(self) -> None:
        service, repository = self._service(
            record=SimpleNamespace(
                context_snapshot='{"enhanced_context": {}}',
                raw_result='{"model_used": "test-model"}',
            ),
            fundamental={"earnings": {"data": {}}},
        )

        context_snapshot, fundamental, raw_result = analysis._load_sync_fundamental_sources(
            "q-sync", "600519", history_service=service
        )

        self.assertEqual(context_snapshot, {"enhanced_context": {}})
        self.assertEqual(fundamental, {"earnings": {"data": {}}})
        self.assertEqual(raw_result, {"model_used": "test-model"})
        self.assertEqual(
            repository.calls,
            [
                ("get_latest_analysis_by_query_id", "q-sync", "600519", None),
                ("get_latest_fundamental_snapshot", "q-sync", "600519"),
            ],
        )

    def test_load_sync_sources_is_fail_open(self) -> None:
        service, _ = self._service()
        service.get_latest_by_query_id = MagicMock(side_effect=RuntimeError("db down"))

        self.assertEqual(
            analysis._load_sync_fundamental_sources("q-sync", "600519", history_service=service),
            (None, None, None),
        )


class HistoryQueryServicePortTestCase(unittest.TestCase):
    def _service(self) -> tuple[HistoryQueryService, FakeHistoryRepository]:
        repository = FakeHistoryRepository()
        return (
            HistoryQueryService(
                repository=repository,
                code_normalizer=DataProviderStockCodeNormalizer(),
            ),
            repository,
        )

    def test_get_latest_by_query_id_forwards_filters(self) -> None:
        service, repository = self._service()

        service.get_latest_by_query_id("q1", code="600519", report_type="detailed")

        self.assertEqual(
            repository.calls,
            [("get_latest_analysis_by_query_id", "q1", "600519", "detailed")],
        )

    def test_latest_by_query_id_and_run_flow_share_history_service_semantics(self) -> None:
        """``resolve_and_get_run_flow`` 由 ``HistoryService`` 承担，不做二次实现。"""
        service, repository = self._service()

        service.get_run_flow("q1", code="600519")

        self.assertEqual(
            repository.calls,
            [("get_latest_analysis_by_query_id", "q1", "600519", None)],
        )


class StockCodeWrapperTestCase(unittest.TestCase):
    def test_analysis_wrappers_match_data_provider_semantics(self) -> None:
        for raw in ("600519", "600519.SH", "sh600519", "00700", "hk00700", "AAPL", " 600519 ", ""):
            self.assertEqual(canonical_stock_code_for_analysis(raw), canonical_stock_code(raw))
            self.assertEqual(normalize_stock_code_for_analysis(raw), normalize_stock_code(raw))

    def test_analysis_wrappers_tolerate_non_string_input(self) -> None:
        self.assertEqual(canonical_stock_code_for_analysis(None), canonical_stock_code(""))
        self.assertEqual(normalize_stock_code_for_analysis(None), normalize_stock_code(""))


if __name__ == "__main__":
    unittest.main()
