# -*- coding: utf-8 -*-
"""回测路由依赖接线与契约回归测试。

``api/v1/endpoints/backtest.py`` 曾直接 ``Depends(get_database_manager)`` 并自行
构造 ``BacktestService``，使端点同时依赖 ``src.storage``。现在路由只依赖
``Depends(get_backtest_service)``，装配收敛到 ``src.bootstrap.backtest``，本文件
锁定该契约，避免回退到直连持久化层。
"""

from __future__ import annotations

import inspect
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import HTTPException

from api.deps import get_backtest_service
from api.v1.endpoints import backtest
from api.v1.schemas.backtest import BacktestRunRequest


def _run_stats(**overrides):
    """构造一份 ``BacktestRunResponse`` 可接受的统计载荷。"""
    stats = {
        "processed": 3,
        "saved": 2,
        "completed": 2,
        "insufficient": 0,
        "errors": 1,
        "applied_eval_window_days": 10,
        "message": None,
        "diagnostics": {"candidates": 3},
    }
    stats.update(overrides)
    return stats


def _performance_summary(**overrides):
    """构造一份 ``PerformanceMetrics`` 可接受的汇总载荷。"""
    summary = {
        "scope": "overall",
        "code": None,
        "eval_window_days": 10,
        "engine_version": "v1",
        "computed_at": None,
        "total_evaluations": 4,
        "completed_count": 3,
        "insufficient_count": 1,
        "long_count": 2,
        "cash_count": 1,
        "win_count": 2,
        "loss_count": 1,
        "neutral_count": 0,
    }
    summary.update(overrides)
    return summary


class BacktestDependencyTestCase(unittest.TestCase):
    def test_endpoint_module_does_not_import_storage(self) -> None:
        source = Path(backtest.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from src.storage import", source)
        self.assertNotIn("DatabaseManager", source)

    def test_every_route_injects_the_backtest_service_dependency(self) -> None:
        routes = [route for route in backtest.router.routes if hasattr(route, "endpoint")]
        self.assertEqual(len(routes), 4, "backtest router must expose four routes")
        for route in routes:
            parameters = inspect.signature(route.endpoint).parameters
            self.assertIn(
                "service",
                parameters,
                f"{route.path} must receive BacktestService via dependency injection",
            )
            dependency = parameters["service"].default
            self.assertIs(
                getattr(dependency, "dependency", None),
                get_backtest_service,
                f"{route.path} must depend on api.deps.get_backtest_service",
            )


class BacktestRunEndpointTestCase(unittest.TestCase):
    def test_forwards_request_payload_to_service(self) -> None:
        service = MagicMock()
        service.run_backtest.return_value = _run_stats()
        request = BacktestRunRequest(
            code="600519",
            force=True,
            eval_window_days=15,
            min_age_days=3,
            analysis_date_from=date(2026, 1, 2),
            analysis_date_to=date(2026, 1, 20),
            limit=50,
        )

        response = backtest.run_backtest(request=request, service=service)

        service.run_backtest.assert_called_once_with(
            code="600519",
            force=True,
            eval_window_days=15,
            min_age_days=3,
            analysis_date_from=date(2026, 1, 2),
            analysis_date_to=date(2026, 1, 20),
            limit=50,
        )
        self.assertEqual(response.processed, 3)
        self.assertEqual(response.applied_eval_window_days, 10)
        self.assertEqual(response.diagnostics, {"candidates": 3})

    def test_rejects_inverted_date_range_before_calling_service(self) -> None:
        service = MagicMock()
        request = BacktestRunRequest(
            analysis_date_from=date(2026, 2, 1),
            analysis_date_to=date(2026, 1, 1),
        )

        with self.assertRaises(HTTPException) as ctx:
            backtest.run_backtest(request=request, service=service)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail["error"], "invalid_params")
        service.run_backtest.assert_not_called()

    def test_maps_service_value_error_to_400(self) -> None:
        service = MagicMock()
        service.run_backtest.side_effect = ValueError("eval_window_days 必须为正整数")

        with self.assertRaises(HTTPException) as ctx:
            backtest.run_backtest(request=BacktestRunRequest(), service=service)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail["error"], "invalid_params")
        self.assertIn("eval_window_days", ctx.exception.detail["message"])

    def test_maps_unexpected_error_to_500(self) -> None:
        service = MagicMock()
        service.run_backtest.side_effect = RuntimeError("boom")

        with self.assertRaises(HTTPException) as ctx:
            backtest.run_backtest(request=BacktestRunRequest(), service=service)

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail["error"], "internal_error")
        self.assertIn("boom", ctx.exception.detail["message"])


class BacktestQueryEndpointTestCase(unittest.TestCase):
    def test_results_echo_pagination_while_total_comes_from_service(self) -> None:
        service = MagicMock()
        service.get_recent_evaluations.return_value = {
            "total": 7,
            "items": [
                {
                    "analysis_history_id": 11,
                    "code": "600519",
                    "eval_window_days": 10,
                    "engine_version": "v1",
                    "eval_status": "completed",
                }
            ],
        }

        response = backtest.get_backtest_results(
            code=None,
            eval_window_days=None,
            analysis_date_from=None,
            analysis_date_to=None,
            analysis_phase=None,
            page=2,
            limit=1,
            service=service,
        )

        self.assertEqual(response.total, 7)
        self.assertEqual(response.page, 2)
        self.assertEqual(response.limit, 1)
        self.assertEqual([item.analysis_history_id for item in response.items], [11])

    def test_overall_performance_returns_404_when_summary_missing(self) -> None:
        service = MagicMock()
        service.get_summary.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            backtest.get_overall_performance(
                eval_window_days=None,
                analysis_date_from=None,
                analysis_date_to=None,
                analysis_phase=None,
                service=service,
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail["error"], "not_found")

    def test_stock_performance_forwards_scope_and_code(self) -> None:
        service = MagicMock()
        service.get_summary.return_value = _performance_summary(scope="stock", code="601318")

        response = backtest.get_stock_performance(
            code="601318",
            eval_window_days=20,
            analysis_date_from=date(2026, 1, 5),
            analysis_date_to=date(2026, 2, 5),
            analysis_phase="postmarket",
            service=service,
        )

        kwargs = service.get_summary.call_args.kwargs
        self.assertEqual(kwargs["scope"], "stock")
        self.assertEqual(kwargs["code"], "601318")
        self.assertEqual(kwargs["eval_window_days"], 20)
        self.assertEqual(kwargs["analysis_phase"], "postmarket")
        self.assertEqual(response.scope, "stock")
        self.assertEqual(response.code, "601318")


if __name__ == "__main__":
    unittest.main()
