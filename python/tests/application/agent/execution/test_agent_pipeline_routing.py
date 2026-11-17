"""Tests for agent pipeline routing."""

from tests.application.agent._agent_pipeline_support import (
    MagicMock,
    _TestPipelineRoutingFixture,
    patch,
    unittest,
)


class TestPipelineRouting(_TestPipelineRoutingFixture, unittest.TestCase):
    def test_agent_mode_routes_to_agent(self):
        """When agent_mode=True, analyze_stock should call _analyze_with_agent."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'):

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 5
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_config.return_value = mock_cfg

            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.domain.shared.enums import ReportType
            pipeline = StockAnalysisPipeline(config=mock_cfg)

            # Mock _analyze_with_agent to verify it gets called
            pipeline._analyze_with_agent = MagicMock(return_value=None)

            pipeline.analyze_stock("600519", ReportType.SIMPLE, "q1")

            pipeline._analyze_with_agent.assert_called_once()
            call_args = pipeline._analyze_with_agent.call_args
            # Positional args: code, report_type, query_id, stock_name, realtime_quote, chip_data, fundamental_context, trend_result
            self.assertEqual(call_args[0][0], "600519")
            self.assertEqual(call_args[0][1], ReportType.SIMPLE)
            self.assertEqual(call_args[0][2], "q1")
            # trend_result (8th arg) should be present (may be a TrendAnalysisResult or None)
            self.assertEqual(len(call_args[0]), 8)

    def test_legacy_mode_does_not_call_agent(self):
        """When agent_mode=False, analyze_stock should NOT call _analyze_with_agent."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port') as mock_db, \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()) as mock_fm, \
             patch('src.application.analysis.pipeline.GeminiAnalyzer') as mock_analyzer, \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService') as mock_search:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = False
            mock_cfg.is_agent_available.return_value = False
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_config.return_value = mock_cfg

            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.domain.shared.enums import ReportType
            pipeline = StockAnalysisPipeline(config=mock_cfg)

            # Mock the fetcher_manager to return None for realtime
            pipeline.fetcher_manager.get_realtime_quote.return_value = None
            pipeline.fetcher_manager.get_chip_distribution.return_value = None
            # Mock search service
            pipeline.search_service.is_available = False
            # Mock DB context
            pipeline.db.get_analysis_context.return_value = None
            # Mock analyzer
            pipeline.analyzer.analyze.return_value = None

            result = pipeline.analyze_stock("600519", ReportType.SIMPLE, "q1")

            # _analyze_with_agent should NOT exist as a mock (it's the real method)
            # Instead, verify analyzer.analyze was called (legacy path)
            pipeline.analyzer.analyze.assert_called_once()

    def test_request_skills_auto_enable_agent_mode(self):
        """Request-specific skills should route the stock analysis through Agent mode."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'):

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = False
            mock_cfg.agent_max_steps = 5
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_config.return_value = mock_cfg

            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.domain.shared.enums import ReportType
            pipeline = StockAnalysisPipeline(
                config=mock_cfg,
                analysis_skills=["growth_quality"],
            )
            pipeline._analyze_with_agent = MagicMock(return_value=None)

            pipeline.analyze_stock("600519", ReportType.SIMPLE, "q1")

            pipeline._analyze_with_agent.assert_called_once()
            self.assertEqual(pipeline.analysis_skills, ["growth_quality"])
