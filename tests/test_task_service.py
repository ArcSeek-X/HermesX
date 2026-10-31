# -*- coding: utf-8 -*-
"""
Regression tests for TaskService failure handling.
测试task服务相关功能测试
"""

import os
import sys
import unittest
import threading
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.litellm_stub import ensure_litellm_stub

ensure_litellm_stub()

from src.application.analysis.analyzer import AnalysisResult
from src.application.runtime.task_service import TaskService


def _make_failed_result(code: str) -> AnalysisResult:
    return AnalysisResult(
        code=code,
        name=f"股票{code}",
        sentiment_score=80,
        trend_prediction="看多",
        operation_advice="持有",
        analysis_summary="解析失败",
        success=False,
        error_message="JSON 解析失败",
    )


class _FakePipeline:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def process_single_stock(self, *args, **kwargs):
        return _make_failed_result(kwargs["code"])


class TestTaskService(unittest.TestCase):
    def test_run_analysis_marks_failed_for_unsuccessful_result(self):
        service = TaskService()
        service._tasks = {}
        service._tasks_lock = threading.Lock()

        fake_main = ModuleType("main")
        fake_main.StockAnalysisPipeline = _FakePipeline

        with patch.dict("sys.modules", {"main": fake_main}), patch(
            "src.config.get_config", return_value=SimpleNamespace()
        ):
            result = service._run_analysis(code="600519", task_id="task-1")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "JSON 解析失败")
        task = service.get_task_status("task-1")
        self.assertIsNotNone(task)
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["error"], "JSON 解析失败")
        self.assertIsNone(task["result"])

    def test_submit_analysis_resolves_bare_jp_kr_code_before_submit(self):
        service = TaskService()
        service._tasks = {}
        service._tasks_lock = threading.Lock()
        captured = {}

        executor = MagicMock()

        def capture_submit(*args, **kwargs):
            captured["args"] = args
            return "future"

        executor.submit.side_effect = capture_submit
        service._executor = executor

        with patch("src.application.runtime.task_service.resolve_index_stock_code_for_analysis", return_value="005930.KS"):
            result = service.submit_analysis("005930", report_type="simple", query_source="cli")

        self.assertEqual(result["code"], "005930.KS")
        self.assertIn("args", captured)
        self.assertEqual(captured["args"][1], "005930.KS")

    def test_get_analysis_history_uses_injected_history_repo_seam(self):
        """W4.2: get_analysis_history 经模块 seam 取历史仓储端口，不再依赖 src.storage。"""
        fake_repo = MagicMock()
        record = MagicMock()
        record.to_dict.return_value = {"code": "600519"}
        fake_repo.get_analysis_history.return_value = [record]
        service = TaskService()
        with patch(
            "src.application.runtime.task_service._get_history_repo",
            return_value=fake_repo,
        ):
            records = service.get_analysis_history(code="600519", days=7, limit=10)
        self.assertEqual(records, [{"code": "600519"}])
        fake_repo.get_analysis_history.assert_called_once_with(
            code="600519", query_id=None, days=7, limit=10
        )

    def test_configure_task_service_wires_database_manager_adapter(self):
        """W4.2: bootstrap.configure_task_service 以 DatabaseManager 门面装配 seam。"""
        from src.application.runtime import task_service as ts
        from src.bootstrap.runtime import configure_task_service

        sentinel = object()
        with patch(
            "src.bootstrap.runtime.DatabaseManager.get_instance", return_value=sentinel
        ), patch.object(ts, "set_history_repo") as mock_set:
            configure_task_service()
        mock_set.assert_called_once_with(sentinel)


if __name__ == "__main__":
    import unittest

    unittest.main()
