# HermesX 测试拆分与目录映射（2026-11-03）

> 作者：Codex；更新时间：2026-11-03（Asia/Shanghai）。当前实施依据：TEST_SUITE_REFACTORING_PLAN.md；对应 ARCHITECTURE_TARGET.md 的职责边界，不等同于服务端源文件第二轮拆分。

## 目录

- [拆分对应](#拆分对应)
- [单文件迁移](#单文件迁移)
- [当前目录统计](#当前目录统计)
- [覆盖与交接](#覆盖与交接)

## 拆分对应

16 个原测试文件拆为 113 个测试模块；共享装配留在各原目录的 16 个 `_…_support.py` 中，私有 fixture mixin 不含测试方法，不继承 unittest.TestCase。方法体、装饰器及参数化定义的 AST 共 1520 项保持一致。

| 原文件 | 新测试模块 | 方法/函数数 |
| --- | --- | ---: |
| `tests/api/alphasift/test_alphasift_api.py` | `tests/api/alphasift/test_alphasift_configuration.py` | 21 |
| `tests/api/alphasift/test_alphasift_api.py` | `tests/api/alphasift/test_alphasift_contracts.py` | 2 |
| `tests/api/alphasift/test_alphasift_api.py` | `tests/api/alphasift/test_alphasift_hotspots.py` | 39 |
| `tests/api/alphasift/test_alphasift_api.py` | `tests/api/alphasift/test_alphasift_screening.py` | 32 |
| `tests/api/decision_signals/test_decision_signal_api.py` | `tests/api/decision_signals/test_decision_signal_contracts.py` | 3 |
| `tests/api/decision_signals/test_decision_signal_api.py` | `tests/api/decision_signals/test_decision_signal_creation.py` | 2 |
| `tests/api/decision_signals/test_decision_signal_api.py` | `tests/api/decision_signals/test_decision_signal_identity.py` | 9 |
| `tests/api/decision_signals/test_decision_signal_api.py` | `tests/api/decision_signals/test_decision_signal_lifecycle.py` | 9 |
| `tests/api/decision_signals/test_decision_signal_api.py` | `tests/api/decision_signals/test_decision_signal_reassessment.py` | 23 |
| `tests/api/decision_signals/test_decision_signal_api.py` | `tests/api/decision_signals/test_decision_signal_security.py` | 3 |
| `tests/application/agent/test_agent_executor.py` | `tests/application/agent/conversation/test_agent_executor_messages.py` | 14 |
| `tests/application/agent/test_agent_executor.py` | `tests/application/agent/execution/test_agent_executor_execution.py` | 21 |
| `tests/application/agent/test_agent_executor.py` | `tests/application/agent/execution/test_agent_executor_failures.py` | 5 |
| `tests/application/agent/test_agent_executor.py` | `tests/application/agent/results/test_agent_executor_results.py` | 8 |
| `tests/application/agent/test_agent_executor.py` | `tests/application/agent/tools/test_agent_executor_tools.py` | 16 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/assembly/test_agent_pipeline_analysis.py` | 8 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/assembly/test_agent_pipeline_factory.py` | 8 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/assembly/test_agent_pipeline_factory_configuration.py` | 2 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/assembly/test_agent_pipeline_factory_context.py` | 1 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/assembly/test_agent_pipeline_factory_failure.py` | 3 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/assembly/test_agent_pipeline_factory_flow.py` | 10 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/configuration/test_agent_pipeline_config.py` | 11 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/execution/test_agent_pipeline_routing.py` | 3 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/results/test_agent_pipeline_results.py` | 9 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/results/test_agent_pipeline_results_context.py` | 3 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/results/test_agent_pipeline_results_failure.py` | 7 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/results/test_agent_pipeline_results_flow.py` | 14 |
| `tests/application/agent/test_agent_pipeline.py` | `tests/application/agent/strategies/test_agent_pipeline_skills.py` | 6 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/conversation/test_multi_agent_stock_scope.py` | 50 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/events/test_multi_agent_events.py` | 18 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/execution/test_multi_agent_assembly.py` | 7 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/execution/test_multi_agent_orchestration.py` | 29 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/execution/test_multi_agent_orchestration_context.py` | 2 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/execution/test_multi_agent_orchestration_failures.py` | 16 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/execution/test_multi_agent_orchestration_flow.py` | 15 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/execution/test_multi_agent_orchestration_results.py` | 1 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/execution/test_multi_agent_protocols.py` | 9 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/memory/test_multi_agent_memory.py` | 9 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/research/test_multi_agent_research.py` | 9 |
| `tests/application/agent/test_multi_agent.py` | `tests/application/agent/strategies/test_multi_agent_strategies.py` | 35 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/analysis/generation/test_analyzer_generation_fallback.py` | 25 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/analysis/generation/test_analyzer_generation_prompts.py` | 5 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/analysis/generation/test_analyzer_generation_responses.py` | 20 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/analysis/generation/test_analyzer_generation_routing.py` | 8 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/analysis/generation/test_analyzer_generation_usage.py` | 13 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/market/generation/test_market_generation_fallback.py` | 7 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/market/generation/test_market_generation_prompts.py` | 7 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/market/generation/test_market_generation_responses.py` | 15 |
| `tests/application/analysis/test_market_analyzer_generate_text.py` | `tests/application/market/generation/test_market_generation_routing.py` | 1 |
| `tests/application/backtest/test_backtest_service.py` | `tests/application/backtest/service/test_backtest_contracts.py` | 21 |
| `tests/application/backtest/test_backtest_service.py` | `tests/application/backtest/service/test_backtest_evaluation.py` | 1 |
| `tests/application/backtest/test_backtest_service.py` | `tests/application/backtest/service/test_backtest_phases.py` | 10 |
| `tests/application/backtest/test_backtest_service.py` | `tests/application/backtest/service/test_backtest_refill.py` | 21 |
| `tests/application/backtest/test_backtest_service.py` | `tests/application/backtest/service/test_backtest_storage.py` | 1 |
| `tests/application/backtest/test_backtest_service.py` | `tests/application/backtest/service/test_backtest_summaries.py` | 14 |
| `tests/application/history/test_analysis_history.py` | `tests/application/history/read_model/test_analysis_history_context.py` | 13 |
| `tests/application/history/test_analysis_history.py` | `tests/application/history/read_model/test_analysis_history_contracts.py` | 4 |
| `tests/application/history/test_analysis_history.py` | `tests/application/history/read_model/test_analysis_history_lifecycle.py` | 27 |
| `tests/application/history/test_analysis_history.py` | `tests/application/history/read_model/test_analysis_history_reports.py` | 13 |
| `tests/application/history/test_analysis_history.py` | `tests/application/history/read_model/test_analysis_history_schema.py` | 3 |
| `tests/application/intelligence/test_search_news_freshness.py` | `tests/application/intelligence/search/test_search_news_content.py` | 7 |
| `tests/application/intelligence/test_search_news_freshness.py` | `tests/application/intelligence/search/test_search_news_contracts.py` | 53 |
| `tests/application/intelligence/test_search_news_freshness.py` | `tests/application/intelligence/search/test_search_news_dates.py` | 9 |
| `tests/application/intelligence/test_search_news_freshness.py` | `tests/application/intelligence/search/test_search_news_providers.py` | 9 |
| `tests/application/intelligence/test_search_news_freshness.py` | `tests/application/intelligence/search/test_search_news_routing.py` | 1 |
| `tests/application/notification/test_notification.py` | `tests/application/notification/service/test_notification_contracts.py` | 11 |
| `tests/application/notification/test_notification.py` | `tests/application/notification/service/test_notification_dispatch.py` | 46 |
| `tests/application/notification/test_notification.py` | `tests/application/notification/service/test_notification_language.py` | 3 |
| `tests/application/notification/test_notification.py` | `tests/application/notification/service/test_notification_reports.py` | 24 |
| `tests/application/notification/test_notification.py` | `tests/application/notification/service/test_notification_signals.py` | 4 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_backends.py` | 21 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_channels.py` | 65 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_env_transfer.py` | 11 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_notifications.py` | 10 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_read.py` | 13 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_runtime.py` | 1 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_save.py` | 15 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_secrets.py` | 31 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_setup.py` | 21 |
| `tests/application/runtime/test_system_config_service.py` | `tests/application/runtime/configuration/test_system_config_validation.py` | 34 |
| `tests/bootstrap/entrypoints/test_main_schedule_mode.py` | `tests/bootstrap/entrypoints/test_main_analysis.py` | 10 |
| `tests/bootstrap/entrypoints/test_main_schedule_mode.py` | `tests/bootstrap/entrypoints/test_main_bootstrap.py` | 10 |
| `tests/bootstrap/entrypoints/test_main_schedule_mode.py` | `tests/bootstrap/entrypoints/test_main_cli.py` | 6 |
| `tests/bootstrap/entrypoints/test_main_schedule_mode.py` | `tests/bootstrap/entrypoints/test_main_scheduler.py` | 16 |
| `tests/bootstrap/entrypoints/test_main_schedule_mode.py` | `tests/bootstrap/entrypoints/test_main_server.py` | 20 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_agent.py` | 11 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_defaults.py` | 7 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_generation.py` | 14 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_help.py` | 15 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_notifications.py` | 34 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_portfolio.py` | 8 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_providers.py` | 9 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_reports.py` | 2 |
| `tests/config/settings/test_config_registry.py` | `tests/config/settings/registry/test_config_registry_runtime.py` | 8 |
| `tests/infrastructure/generation/telemetry/test_llm_usage.py` | `tests/infrastructure/generation/telemetry/test_llm_usage_normalization.py` | 13 |
| `tests/infrastructure/generation/telemetry/test_llm_usage.py` | `tests/infrastructure/generation/telemetry/test_llm_usage_normalization_payloads.py` | 10 |
| `tests/infrastructure/generation/telemetry/test_llm_usage.py` | `tests/infrastructure/generation/telemetry/test_llm_usage_normalization_providers.py` | 28 |
| `tests/infrastructure/generation/telemetry/test_llm_usage.py` | `tests/infrastructure/generation/telemetry/test_llm_usage_persistence.py` | 17 |
| `tests/infrastructure/generation/telemetry/test_llm_usage.py` | `tests/infrastructure/generation/telemetry/test_llm_usage_security.py` | 13 |
| `tests/infrastructure/generation/telemetry/test_llm_usage.py` | `tests/infrastructure/generation/telemetry/test_llm_usage_summary.py` | 6 |
| `tests/integration/alert/test_alert_worker.py` | `tests/integration/alert/test_alert_worker_analysis.py` | 5 |
| `tests/integration/alert/test_alert_worker.py` | `tests/integration/alert/test_alert_worker_contracts.py` | 23 |
| `tests/integration/alert/test_alert_worker.py` | `tests/integration/alert/test_alert_worker_indicators.py` | 16 |
| `tests/integration/alert/test_alert_worker.py` | `tests/integration/alert/test_alert_worker_lifecycle.py` | 10 |
| `tests/integration/alert/test_alert_worker.py` | `tests/integration/alert/test_alert_worker_notifications.py` | 3 |
| `tests/integration/analysis/test_analysis_api_contract.py` | `tests/integration/analysis/test_analysis_assets_contract.py` | 2 |
| `tests/integration/analysis/test_analysis_api_contract.py` | `tests/integration/analysis/test_analysis_market_review_contract.py` | 19 |
| `tests/integration/analysis/test_analysis_api_contract.py` | `tests/integration/analysis/test_analysis_queue_contract.py` | 7 |
| `tests/integration/analysis/test_analysis_api_contract.py` | `tests/integration/analysis/test_analysis_reports_contract.py` | 24 |
| `tests/integration/analysis/test_analysis_api_contract.py` | `tests/integration/analysis/test_analysis_services_contract.py` | 10 |
| `tests/integration/analysis/test_analysis_api_contract.py` | `tests/integration/analysis/test_analysis_status_contract.py` | 17 |
| `tests/integration/analysis/test_analysis_api_contract.py` | `tests/integration/analysis/test_analysis_stream_contract.py` | 1 |
| `tests/integration/analysis/test_analysis_api_contract.py` | `tests/integration/analysis/test_analysis_submission_contract.py` | 16 |

## 单文件迁移

以下文件保留内容，按受测能力细分落点。

| 原文件 | 新文件 |
| --- | --- |
| `tests/application/agent/test_agent_backend.py` | `tests/application/agent/execution/test_agent_backend.py` |
| `tests/application/agent/test_agent_chat_executor.py` | `tests/application/agent/conversation/test_agent_chat_executor.py` |
| `tests/application/agent/test_agent_conversation_port_seam.py` | `tests/application/agent/conversation/test_agent_conversation_port_seam.py` |
| `tests/application/agent/test_agent_frozen_context.py` | `tests/application/agent/execution/test_agent_frozen_context.py` |
| `tests/application/agent/test_agent_litellm_route_resolution.py` | `tests/application/agent/execution/test_agent_litellm_route_resolution.py` |
| `tests/application/agent/test_agent_orchestrator_sniper_fallback.py` | `tests/application/agent/execution/test_agent_orchestrator_sniper_fallback.py` |
| `tests/application/agent/test_agent_registry.py` | `tests/application/agent/strategies/test_agent_registry.py` |
| `tests/application/agent/test_agent_stream_events.py` | `tests/application/agent/conversation/test_agent_stream_events.py` |
| `tests/application/agent/test_agent_tool_surface.py` | `tests/application/agent/tools/test_agent_tool_surface.py` |
| `tests/application/agent/test_agent_tools_db_seam.py` | `tests/application/agent/tools/test_agent_tools_db_seam.py` |
| `tests/application/agent/test_chat_context.py` | `tests/application/agent/conversation/test_chat_context.py` |
| `tests/application/agent/test_conversation_manager.py` | `tests/application/agent/conversation/test_conversation_manager.py` |
| `tests/application/agent/test_data_tools_daily_history_cache.py` | `tests/application/agent/tools/test_data_tools_daily_history_cache.py` |
| `tests/application/agent/test_data_tools_get_capital_flow.py` | `tests/application/agent/tools/test_data_tools_get_capital_flow.py` |
| `tests/application/agent/test_data_tools_get_stock_info.py` | `tests/application/agent/tools/test_data_tools_get_stock_info.py` |
| `tests/application/agent/test_data_tools_portfolio_snapshot.py` | `tests/application/agent/tools/test_data_tools_portfolio_snapshot.py` |
| `tests/application/agent/test_provider_trace.py` | `tests/application/agent/execution/test_provider_trace.py` |
| `tests/application/agent/test_search_tools_persistence.py` | `tests/application/agent/tools/test_search_tools_persistence.py` |
| `tests/application/agent/test_skill_load_warning.py` | `tests/application/agent/strategies/test_skill_load_warning.py` |
| `tests/application/agent/test_strategy_deliberation.py` | `tests/application/agent/strategies/test_strategy_deliberation.py` |
| `tests/application/agent/test_strategy_scheduler.py` | `tests/application/agent/strategies/test_strategy_scheduler.py` |
| `tests/application/analysis/test_analysis_context_builder.py` | `tests/application/analysis/context/test_analysis_context_builder.py` |
| `tests/application/analysis/test_analysis_context_pack_overview.py` | `tests/application/analysis/context/test_analysis_context_pack_overview.py` |
| `tests/application/analysis/test_analyzer_news_prompt.py` | `tests/application/analysis/generation/test_analyzer_news_prompt.py` |
| `tests/application/analysis/test_chip_structure_fallback.py` | `tests/application/analysis/signals/test_chip_structure_fallback.py` |
| `tests/application/analysis/test_decision_stability.py` | `tests/application/analysis/signals/test_decision_stability.py` |
| `tests/application/analysis/test_eod_picker_service.py` | `tests/application/analysis/screening/test_eod_picker_service.py` |
| `tests/application/analysis/test_image_stock_extractor_litellm.py` | `tests/application/analysis/vision/test_image_stock_extractor_litellm.py` |
| `tests/application/analysis/test_image_stock_extractor_vision_port.py` | `tests/application/analysis/vision/test_image_stock_extractor_vision_port.py` |
| `tests/application/analysis/test_phase_decision_guardrail.py` | `tests/application/analysis/signals/test_phase_decision_guardrail.py` |
| `tests/application/analysis/test_pipeline_augment_realtime.py` | `tests/application/analysis/pipeline/test_pipeline_augment_realtime.py` |
| `tests/application/analysis/test_pipeline_daily_market_context.py` | `tests/application/analysis/pipeline/test_pipeline_daily_market_context.py` |
| `tests/application/analysis/test_pipeline_fetch_error.py` | `tests/application/analysis/pipeline/test_pipeline_fetch_error.py` |
| `tests/application/analysis/test_pipeline_market_phase_context.py` | `tests/application/analysis/pipeline/test_pipeline_market_phase_context.py` |
| `tests/application/analysis/test_pipeline_notification_image_routing.py` | `tests/application/analysis/pipeline/test_pipeline_notification_image_routing.py` |
| `tests/application/analysis/test_pipeline_optional_service_resilience.py` | `tests/application/analysis/pipeline/test_pipeline_optional_service_resilience.py` |
| `tests/application/analysis/test_pipeline_persistence_port.py` | `tests/application/analysis/pipeline/test_pipeline_persistence_port.py` |
| `tests/application/analysis/test_pipeline_prefetch_dry_run.py` | `tests/application/analysis/pipeline/test_pipeline_prefetch_dry_run.py` |
| `tests/application/analysis/test_pipeline_realtime_indicators.py` | `tests/application/analysis/pipeline/test_pipeline_realtime_indicators.py` |
| `tests/application/analysis/test_pipeline_related_boards.py` | `tests/application/analysis/pipeline/test_pipeline_related_boards.py` |
| `tests/application/analysis/test_pipeline_single_notify_thread_safety.py` | `tests/application/analysis/pipeline/test_pipeline_single_notify_thread_safety.py` |
| `tests/application/analysis/test_pipeline_single_stock_notify.py` | `tests/application/analysis/pipeline/test_pipeline_single_stock_notify.py` |
| `tests/application/analysis/test_report_integrity.py` | `tests/application/analysis/generation/test_report_integrity.py` |
| `tests/application/analysis/test_report_schema.py` | `tests/application/analysis/generation/test_report_schema.py` |
| `tests/application/analysis/test_signal_attribution.py` | `tests/application/analysis/signals/test_signal_attribution.py` |
| `tests/application/analysis/test_stock_data_port.py` | `tests/application/analysis/pipeline/test_stock_data_port.py` |
| `tests/application/analysis/test_tickflow_pipeline_prefetch.py` | `tests/application/analysis/pipeline/test_tickflow_pipeline_prefetch.py` |
| `tests/infrastructure/providers/common/test_a_share_fetcher_code_conversion.py` | `tests/infrastructure/providers/catalog/test_a_share_fetcher_code_conversion.py` |
| `tests/infrastructure/providers/common/test_alphavantage_fetcher.py` | `tests/infrastructure/providers/fundamentals/test_alphavantage_fetcher.py` |
| `tests/infrastructure/providers/common/test_chip_distribution_manager.py` | `tests/infrastructure/providers/routing/test_chip_distribution_manager.py` |
| `tests/infrastructure/providers/common/test_data_fetcher_manager_hk_bare_code.py` | `tests/infrastructure/providers/routing/test_data_fetcher_manager_hk_bare_code.py` |
| `tests/infrastructure/providers/common/test_data_fetcher_prefetch_stock_names.py` | `tests/infrastructure/providers/routing/test_data_fetcher_prefetch_stock_names.py` |
| `tests/infrastructure/providers/common/test_fetcher_source_optimization.py` | `tests/infrastructure/providers/routing/test_fetcher_source_optimization.py` |
| `tests/infrastructure/providers/common/test_finnhub_fetcher.py` | `tests/infrastructure/providers/fundamentals/test_finnhub_fetcher.py` |
| `tests/infrastructure/providers/common/test_jp_kr_market_support.py` | `tests/infrastructure/providers/routing/test_jp_kr_market_support.py` |
| `tests/infrastructure/providers/common/test_provider_cache.py` | `tests/infrastructure/providers/cache/test_provider_cache.py` |
| `tests/infrastructure/providers/common/test_realtime_quote_fallback_logging.py` | `tests/infrastructure/providers/routing/test_realtime_quote_fallback_logging.py` |
| `tests/infrastructure/providers/common/test_stocksdk_bridge_and_sources.py` | `tests/infrastructure/providers/routing/test_stocksdk_bridge_and_sources.py` |
| `tests/infrastructure/providers/common/test_tickflow_manager_routing.py` | `tests/infrastructure/providers/routing/test_tickflow_manager_routing.py` |
| `tests/infrastructure/providers/common/test_tickflow_market_review_fallback.py` | `tests/infrastructure/providers/routing/test_tickflow_market_review_fallback.py` |
| `tests/infrastructure/providers/common/test_tushare_fetcher_followups.py` | `tests/infrastructure/providers/catalog/test_tushare_fetcher_followups.py` |
| `tests/infrastructure/providers/common/test_tushare_fetcher_get_stock_list.py` | `tests/infrastructure/providers/catalog/test_tushare_fetcher_get_stock_list.py` |
| `tests/infrastructure/providers/common/test_tushare_fetcher_http_client.py` | `tests/infrastructure/providers/http/test_tushare_fetcher_http_client.py` |
| `tests/infrastructure/providers/common/test_tw_market_support.py` | `tests/infrastructure/providers/routing/test_tw_market_support.py` |

## 当前目录统计

按 `test_*.py` 统计，不含 support/conftest/样本。三级是相对 tests/ 的目录深度。

| 一级 | 二级 | 三级 | 测试文件数 |
| --- | --- | --- | ---: |
| agent | — | — | 4 |
| api | agent | — | 4 |
| api | alerts | — | 1 |
| api | alphasift | — | 4 |
| api | analysis | — | 1 |
| api | auth | — | 2 |
| api | backtest | — | 1 |
| api | common | — | 5 |
| api | contract | — | 3 |
| api | decision_signals | — | 7 |
| api | intelligence | — | 1 |
| api | kline | — | 1 |
| api | limit_pool | — | 1 |
| api | portfolio | — | 1 |
| api | quote | — | 2 |
| api | sector | — | 1 |
| api | stocks | — | 1 |
| api | system_config | — | 1 |
| api | usage | — | 1 |
| api | watchlist | — | 1 |
| application | agent | assembly | 6 |
| application | agent | configuration | 1 |
| application | agent | conversation | 7 |
| application | agent | events | 1 |
| application | agent | execution | 15 |
| application | agent | memory | 1 |
| application | agent | research | 1 |
| application | agent | results | 5 |
| application | agent | strategies | 6 |
| application | agent | tools | 8 |
| application | analysis | context | 2 |
| application | analysis | generation | 8 |
| application | analysis | pipeline | 14 |
| application | analysis | screening | 1 |
| application | analysis | signals | 4 |
| application | analysis | vision | 2 |
| application | backtest | service | 6 |
| application | decision | — | 4 |
| application | history | — | 4 |
| application | history | read_model | 5 |
| application | intelligence | — | 4 |
| application | intelligence | search | 5 |
| application | market | — | 9 |
| application | market | generation | 4 |
| application | notification | — | 3 |
| application | notification | service | 5 |
| application | portfolio | — | 3 |
| application | quote | — | 8 |
| application | reporting | — | 4 |
| application | runtime | — | 12 |
| application | runtime | configuration | 10 |
| application | usage | — | 1 |
| application | watchlist | — | 1 |
| bootstrap | — | — | 4 |
| bootstrap | entrypoints | — | 8 |
| bot | — | — | 7 |
| config | deployment | — | 1 |
| config | settings | — | 5 |
| config | settings | registry | 9 |
| domain | analysis | — | 5 |
| domain | backtest | — | 3 |
| domain | decision | — | 4 |
| domain | generation | — | 1 |
| domain | market | — | 5 |
| domain | notification | — | 2 |
| domain | portfolio | — | 1 |
| domain | shared | — | 4 |
| infrastructure | agent_runtime | — | 3 |
| infrastructure | brokers | — | 1 |
| infrastructure | generation | — | 2 |
| infrastructure | generation | backends | 1 |
| infrastructure | generation | telemetry | 7 |
| infrastructure | indexing | — | 1 |
| infrastructure | notification | senders | 3 |
| infrastructure | observability | — | 1 |
| infrastructure | persistence | — | 7 |
| infrastructure | providers | cache | 1 |
| infrastructure | providers | catalog | 3 |
| infrastructure | providers | code_search | 2 |
| infrastructure | providers | common | 1 |
| infrastructure | providers | fundamentals | 5 |
| infrastructure | providers | http | 1 |
| infrastructure | providers | institutional | 3 |
| infrastructure | providers | kline | 13 |
| infrastructure | providers | realtime | 5 |
| infrastructure | providers | routing | 10 |
| infrastructure | providers | stock_info | 1 |
| infrastructure | search | — | 4 |
| infrastructure | security | — | 3 |
| integration | alert | — | 5 |
| integration | analysis | — | 13 |
| integration | decision | — | 2 |
| integration | generation | — | 1 |
| integration | intelligence | — | 3 |
| integration | portfolio | — | 2 |
| tooling | docs | — | 5 |
| tooling | packaging | — | 4 |
| tooling | scripts | — | 7 |
| tooling | test_runtime | — | 1 |
| tooling | workflows | — | 3 |
| utils | — | — | 1 |

合计 **397 个测试模块**；tests/ 顶层测试为 **0**。叶目录文件数是软约束，优先保持同一业务行为的聚合。

## 覆盖与交接

- 收集前后均为 5725 项；依据旧→新节点映射逐项核对 nodeid（含参数后缀）及重复次数，而非仅比较总数。
- 16 个原拆分组分别在独立 pytest 进程运行，各组全部新模块均通过，未依赖其他拆分组先行装配。
- 1520 个拆分方法/函数逐项 AST 校验；拆分不修改断言、不增减 skip/xfail/network 标记。
- 共享支持模块只供相邻业务测试使用；不要把带 test_ 方法的原测试类作为跨模块父类。
- analysis API 导入期临时 ENV_FILE 限定在 patch.dict 作用域内，不在模块退出时覆盖整个进程环境。
- 真实框架生命周期保持启用；静态资源启动测试仅隔离不属于其契约的调度器与行情预热，并验证 scheduler.stop 被调用。
- 随机验证结果、根因与平台验收限制见 [迁移台账 §10](./TEST_SUITE_MIGRATION_PROGRESS.md#10-测试文件内部拆分目录细分与验收2026-11-03)。
- 原文件恢复时必须同步撤回对应新模块和活动文档引用；禁止同时保留新旧测试导致重复收集。
