# -*- coding: utf-8 -*-
# 本文件主要测试：测试自动补全 PR0 的 TaskInfo / 任务队列字段扩展
"""
===================================
Autocomplete PR0 - TaskQueue Runtime Tests
===================================

Test the ``src.application.runtime.task_queue`` data contract extension:
- TaskInfo dataclass new fields + ``to_dict``/``copy``
- backward compatibility when new fields are omitted
- task queue batch submission accepts / propagates new fields
- duplicate detection unaffected by new fields
"""

from concurrent.futures import Future
from src.application.runtime.task_queue import TaskInfo, DuplicateTaskError, AnalysisTaskQueue


class TestTaskInfo:
    """Test TaskInfo dataclass"""

    def test_task_info_with_new_fields(self):
        """Test that TaskInfo contains new fields"""
        task = TaskInfo(
            task_id="test123",
            stock_code="600519",
            stock_name="贵州茅台",
            original_query="茅台",
            selection_source="autocomplete",
        )
        d = task.to_dict()
        assert "original_query" in d
        assert "selection_source" in d
        assert d["original_query"] == "茅台"
        assert d["selection_source"] == "autocomplete"

    def test_task_info_backward_compatible(self):
        """Test TaskInfo backward compatibility: works fine without new fields"""
        task = TaskInfo(
            task_id="test123",
            stock_code="600519",
        )
        d = task.to_dict()
        assert d["original_query"] is None
        assert d["selection_source"] is None

    def test_task_info_copy_includes_new_fields(self):
        """Test that TaskInfo.copy() includes new fields"""
        task = TaskInfo(
            task_id="test123",
            stock_code="600519",
            stock_name="贵州茅台",
            original_query="茅台",
            selection_source="autocomplete",
        )
        copied = task.copy()
        assert copied.original_query == "茅台"
        assert copied.selection_source == "autocomplete"


class TestTaskQueue:
    """Test task queue"""

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

    @staticmethod
    def _build_queue():
        queue = AnalysisTaskQueue(max_workers=1)
        queue._executor = type("ExecutorStub", (), {"submit": lambda self, *args, **kwargs: Future()})()
        return queue

    def test_task_queue_accepts_new_fields(self):
        """Test task queue accepts new fields"""
        queue = self._build_queue()
        tasks, _duplicates = queue.submit_tasks_batch(
            stock_codes=["600519"],
            stock_name="贵州茅台",
            original_query="茅台",
            selection_source="autocomplete",
        )
        assert len(tasks) == 1
        assert tasks[0].stock_name == "贵州茅台"
        assert tasks[0].original_query == "茅台"
        assert tasks[0].selection_source == "autocomplete"

    def test_task_queue_backward_compatible(self):
        """Test task queue backward compatibility: works fine without new fields"""
        queue = self._build_queue()
        tasks, _duplicates = queue.submit_tasks_batch(
            stock_codes=["600519"],
        )
        assert len(tasks) == 1
        assert tasks[0].original_query is None
        assert tasks[0].selection_source is None

    def test_task_queue_batch_with_new_fields(self):
        """Test support for new fields during batch submission"""
        queue = self._build_queue()
        tasks, _duplicates = queue.submit_tasks_batch(
            stock_codes=["600519", "000001"],
            stock_name="批量股票",
            original_query="600519,000001",
            selection_source="import",
        )
        assert len(tasks) == 2
        for task in tasks:
            assert task.stock_name == "批量股票"
            assert task.original_query == "600519,000001"
            assert task.selection_source == "import"

    def test_task_queue_duplicate_detection_with_new_fields(self):
        """Test that new fields do not affect duplicate submission detection logic"""
        queue = self._build_queue()
        stock_code = "600519"

        # First submission
        tasks1, dups1 = queue.submit_tasks_batch(
            stock_codes=[stock_code],
            stock_name="贵州茅台",
            original_query="茅台",
            selection_source="autocomplete",
        )
        assert len(tasks1) == 1
        assert len(dups1) == 0

        # Second submission (should be rejected)
        tasks2, dups2 = queue.submit_tasks_batch(
            stock_codes=[stock_code],
            stock_name="贵州茅台",
            original_query="茅台",
            selection_source="manual",  # Rejection still applies even if selection_source differs
        )
        assert len(tasks2) == 0
        assert len(dups2) == 1
        assert isinstance(dups2[0], DuplicateTaskError)
