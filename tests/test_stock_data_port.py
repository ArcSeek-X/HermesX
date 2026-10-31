"""R3-S15b 回归：``StockDataPort`` 装配语义与 pipeline 注入路径。

覆盖三个真实风险面：

1. seam 未注册时必须**显式抛错**，不能静默降级为空数据（与 ImageRenderPort 的
   None 回退语义相反）；
2. 出厂适配器满足端口方法面，且每次构造都是新实例（保持“一条流水线一个
   ``DataFetcherManager``”的既有预热缓存语义）；
3. ``StockAnalysisPipeline`` 的 ``stock_data`` 形参优先于 bootstrap 工厂，未注入时
   才走工厂 —— 这是 16 处 ``patch(...build_stock_data_port)`` 测试的语义基础。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.litellm_stub import ensure_litellm_stub

ensure_litellm_stub()

from src.application.analysis.stock_data_port import (
    StockDataPort,
    build_stock_data_port,
    set_stock_data_port_factory,
)

PORT_METHODS = (
    "get_stock_name",
    "get_daily_data",
    "get_realtime_quote",
    "get_chip_distribution",
    "get_fundamental_context",
    "build_failed_fundamental_context",
    "get_belong_boards",
    "prefetch_daily_klines",
    "prefetch_realtime_quotes",
    "prefetch_stock_names",
)


class StockDataPortSeamTests(unittest.TestCase):
    def tearDown(self):
        # 会话级 conftest 已注册默认工厂；用例内撤销后必须复原，避免污染后续用例。
        from src.bootstrap.analysis import configure_stock_data_port

        configure_stock_data_port()

    def test_unregistered_factory_raises_instead_of_degrading(self):
        set_stock_data_port_factory(None)

        with self.assertRaises(RuntimeError):
            build_stock_data_port()

    def test_bootstrap_factory_builds_port_with_full_method_surface(self):
        from src.bootstrap.analysis import configure_stock_data_port

        configure_stock_data_port()
        port = build_stock_data_port()

        self.assertIsInstance(port, StockDataPort)
        for name in PORT_METHODS:
            self.assertTrue(callable(getattr(port, name)), f"{name} should be callable")

        # 每条流水线一个管理器：工厂不得退化为共享单例。
        self.assertIsNot(build_stock_data_port(), build_stock_data_port())

    def test_unknown_capability_probe_returns_none_like_before(self):
        from src.bootstrap.analysis import configure_stock_data_port

        configure_stock_data_port()
        port = build_stock_data_port()

        # MarketHotspotService 以 getattr(..., None) 探测可选能力，缺失必须是 AttributeError。
        self.assertIsNone(getattr(port, "definitely_not_a_real_capability", None))


class PipelineStockDataInjectionTests(unittest.TestCase):
    def _build_pipeline(self, **kwargs):
        from src.application.analysis import pipeline as pipeline_module

        with patch.object(
            pipeline_module, "build_pipeline_persistence_port", return_value=MagicMock()
        ), patch.object(
            pipeline_module, "GeminiAnalyzer", return_value=MagicMock()
        ), patch.object(
            pipeline_module, "NotificationService", return_value=MagicMock()
        ), patch.object(
            pipeline_module, "SearchService", return_value=MagicMock()
        ):
            return pipeline_module.StockAnalysisPipeline(config=MagicMock(), **kwargs)

    def test_injected_stock_data_takes_precedence_over_factory(self):
        fake = MagicMock()

        pipeline = self._build_pipeline(stock_data=fake)

        self.assertIs(pipeline.fetcher_manager, fake)

    def test_default_stock_data_comes_from_bootstrap_factory(self):
        from src.application.analysis import pipeline as pipeline_module

        fake = MagicMock()
        with patch.object(
            pipeline_module, "build_stock_data_port", return_value=fake
        ) as factory:
            pipeline = self._build_pipeline()

        factory.assert_called_once_with()
        self.assertIs(pipeline.fetcher_manager, fake)


if __name__ == "__main__":
    unittest.main()
