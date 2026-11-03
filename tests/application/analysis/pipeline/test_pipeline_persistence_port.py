# -*- coding: utf-8 -*-
"""个股分析持久化端口回归（W4.2）。

覆盖三件事：

- 适配器对 ``DatabaseManager`` 逐方法委托的形状与 kwargs 透传；
- 端口声明的方法面被实现完整覆盖（含 ``analyze_ma_status`` 这类宿主独有方法）；
- ``src.application.analysis.pipeline`` 不再直连 ``src.storage``，且未装配时显式报错。
"""

from __future__ import annotations

import inspect
import unittest
from datetime import date
from pathlib import Path

from src.application.analysis.persistence_port import (
    AnalysisPipelinePersistencePort,
    build_pipeline_persistence_port,
    set_analysis_pipeline_persistence_port_factory,
)
from src.infrastructure.persistence.repositories.pipeline_persistence_adapter import (
    DatabaseManagerPipelinePersistenceAdapter,
)


class _RecordingDb:
    """记录调用参数的最小假宿主，避免触碰真实数据库。"""

    def __init__(self) -> None:
        self.calls = []

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return 0

    def has_today_data(self, code, target_date=None):
        return self._record("has_today_data", code, target_date)

    def save_daily_data(self, df, code, data_source="Unknown"):
        return self._record("save_daily_data", df, code, data_source)

    def save_fundamental_snapshot(self, query_id, code, payload, source_chain=None, coverage=None):
        return self._record(
            "save_fundamental_snapshot", query_id, code, payload, source_chain, coverage
        )

    def get_data_range(self, code, start_date, end_date):
        return self._record("get_data_range", code, start_date, end_date)

    def save_news_intel(self, code, name, dimension, query, response, query_context=None):
        return self._record(
            "save_news_intel", code, name, dimension, query, response, query_context
        )

    def save_analysis_history(
        self,
        result,
        query_id,
        report_type,
        news_content,
        context_snapshot=None,
        save_snapshot=True,
    ):
        return self._record(
            "save_analysis_history",
            result,
            query_id,
            report_type,
            news_content,
            context_snapshot,
            save_snapshot,
        )

    def get_analysis_history(
        self, code=None, query_id=None, days=30, limit=50, exclude_query_id=None
    ):
        return self._record(
            "get_analysis_history", code, query_id, days, limit, exclude_query_id
        )

    def update_analysis_history_diagnostics(
        self, *, query_id, code=None, diagnostics=None, notification_runs=None
    ):
        return self._record(
            "update_analysis_history_diagnostics",
            query_id=query_id,
            code=code,
            diagnostics=diagnostics,
            notification_runs=notification_runs,
        )

    def get_analysis_context(self, code, target_date=None):
        return self._record("get_analysis_context", code, target_date)

    def analyze_ma_status(self, data):
        return "bull"


class TestPipelinePersistenceAdapter(unittest.TestCase):
    def test_adapter_satisfies_protocol_and_delegates(self) -> None:
        db = _RecordingDb()
        adapter = DatabaseManagerPipelinePersistenceAdapter(db)
        self.assertIsInstance(adapter, AnalysisPipelinePersistencePort)

        self.assertFalse(adapter.has_today_data("600519", date(2026, 10, 30)))
        adapter.save_daily_data("df", "600519", "akshare")
        adapter.save_fundamental_snapshot("q1", "600519", {"a": 1}, ["s"], {"c": 1})
        self.assertEqual(adapter.get_data_range("600519", date(2026, 1, 1), date(2026, 2, 1)), 0)
        adapter.save_news_intel("600519", "贵州茅台", "latest_news", "q", "resp", {"k": "v"})
        adapter.save_analysis_history("result", "q1", "simple", None, {"snap": 1}, False)
        adapter.get_analysis_history(query_id="q1", days=7)
        adapter.update_analysis_history_diagnostics(
            query_id="q1", code="600519", diagnostics={"d": 1}, notification_runs=[]
        )
        adapter.get_analysis_context("600519", date(2026, 10, 30))
        self.assertEqual(adapter.analyze_ma_status("row"), "bull")

        names = [call[0] for call in db.calls]
        self.assertEqual(
            names,
            [
                "has_today_data",
                "save_daily_data",
                "save_fundamental_snapshot",
                "get_data_range",
                "save_news_intel",
                "save_analysis_history",
                "get_analysis_history",
                "update_analysis_history_diagnostics",
                "get_analysis_context",
            ],
        )
        diagnostics_call = db.calls[7]
        self.assertEqual(diagnostics_call[2]["query_id"], "q1")
        self.assertEqual(diagnostics_call[2]["diagnostics"], {"d": 1})

    def test_adapter_explicit_constructor_uses_injected_manager(self) -> None:
        db = _RecordingDb()
        self.assertIs(DatabaseManagerPipelinePersistenceAdapter(db)._db, db)

    def test_port_methods_are_covered_by_repository_signature(self) -> None:
        from src.storage import DatabaseManager

        for name, member in inspect.getmembers(
            AnalysisPipelinePersistencePort, predicate=inspect.isfunction
        ):
            if name.startswith("_"):
                continue
            port_params = list(inspect.signature(member).parameters)
            adapter_params = list(
                inspect.signature(getattr(DatabaseManagerPipelinePersistenceAdapter, name)).parameters
            )
            self.assertEqual(port_params, adapter_params, f"{name} 参数面不一致")
            host_params = inspect.signature(getattr(DatabaseManager, name)).parameters
            for param in port_params:
                self.assertIn(param, host_params, f"宿主缺少 {name} 的参数 {param}")


class TestPipelinePersistenceSeam(unittest.TestCase):
    def tearDown(self) -> None:
        # 恢复生产等价装配（而非留 None）：本模块用例会临时清空全局 seam，
        # 若不复位会污染同一进程里后续未 patch 构造入口的 pipeline 用例。
        from src.bootstrap.analysis import configure_analysis_pipeline_persistence

        configure_analysis_pipeline_persistence()

    def test_unconfigured_seam_raises_with_bootstrap_hint(self) -> None:
        set_analysis_pipeline_persistence_port_factory(None)
        with self.assertRaises(RuntimeError) as ctx:
            build_pipeline_persistence_port()
        self.assertIn("configure_analysis_pipeline_persistence", str(ctx.exception))

    def test_registered_factory_is_invoked_per_build(self) -> None:
        created = []

        def factory():
            adapter = DatabaseManagerPipelinePersistenceAdapter(_RecordingDb())
            created.append(adapter)
            return adapter

        set_analysis_pipeline_persistence_port_factory(factory)
        first = build_pipeline_persistence_port()
        second = build_pipeline_persistence_port()
        self.assertIsNot(first, second)
        self.assertEqual(len(created), 2)

    def test_pipeline_module_has_no_storage_import(self) -> None:
        from src.application.analysis import pipeline as pipeline_module

        source = Path(pipeline_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from src.storage", source)
        self.assertNotIn("import src.storage", source)
        self.assertFalse(hasattr(pipeline_module, "get_db"))


if __name__ == "__main__":
    unittest.main()
