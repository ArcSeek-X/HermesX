# -*- coding: utf-8 -*-
# 本文件主要测试：测试自动补全 PR0 的请求 -> 任务队列端到端链路
"""
===================================
Autocomplete PR0 - End-to-End Integration Tests
===================================

Cross-boundary flow spanning ``api.v1.schemas.analysis.AnalyzeRequest`` and
``src.application.runtime.task_queue``: request fields must propagate intact
through batch task submission.
"""

from concurrent.futures import Future
from api.v1.schemas.analysis import AnalyzeRequest
from src.application.runtime.task_queue import get_task_queue, AnalysisTaskQueue


class TestIntegration:
    """Integration Tests"""

    def setup_method(self):
        self._original_instance = AnalysisTaskQueue._instance
        AnalysisTaskQueue._instance = None

    def teardown_method(self):
        queue = AnalysisTaskQueue._instance
        if queue is not None and queue is not self._original_instance:
            executor = getattr(queue, "_executor", None)
            if executor is not None and hasattr(executor, "shutdown"):
                executor.shutdown(wait=False, cancel_futures=True)
        AnalysisTaskQueue._instance = self._original_instance

    def test_end_to_end_flow_with_autocomplete(self):
        """Test end-to-end flow: autocomplete -> analysis request -> task creation"""
        # Simulate request after autocomplete
        request = AnalyzeRequest(
            stock_code="600519.SH",
            async_mode=True,
            stock_name="贵州茅台",
            original_query="茅台",
            selection_source="autocomplete",
            report_type="detailed",
        )

        # Submit to task queue
        queue = get_task_queue()
        queue._executor = type("ExecutorStub", (), {"submit": lambda self, *args, **kwargs: Future()})()
        tasks, _duplicates = queue.submit_tasks_batch(
            stock_codes=[request.stock_code],
            stock_name=request.stock_name,
            original_query=request.original_query,
            selection_source=request.selection_source,
            report_type=request.report_type,
        )

        assert len(tasks) == 1
        task = tasks[0]
        assert task.stock_code == "600519.SH"
        assert task.stock_name == "贵州茅台"
        assert task.original_query == "茅台"
        assert task.selection_source == "autocomplete"
        assert task.report_type == "detailed"

    def test_end_to_end_flow_manual_input(self):
        """Test end-to-end flow: manual input -> analysis request -> task creation"""
        # Simulate manual input request
        request = AnalyzeRequest(
            stock_code="600519",
            async_mode=True,
            selection_source="manual",
        )

        # Submit to task queue
        queue = get_task_queue()
        queue._executor = type("ExecutorStub", (), {"submit": lambda self, *args, **kwargs: Future()})()
        tasks, _duplicates = queue.submit_tasks_batch(
            stock_codes=[request.stock_code],
            selection_source=request.selection_source,
            report_type=request.report_type,
        )

        assert len(tasks) == 1
        task = tasks[0]
        assert task.stock_code == "600519"
        assert task.selection_source == "manual"
