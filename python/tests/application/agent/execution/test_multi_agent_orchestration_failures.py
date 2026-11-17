"""Tests for multi agent orchestration failures."""

from tests.application.agent._multi_agent_support import (
    AgentContext,
    AgentOpinion,
    MagicMock,
    SimpleNamespace,
    StageStatus,
    _TestOrchestratorExecutionFixture,
    json,
    patch,
    unittest,
)


class TestOrchestratorExecution(_TestOrchestratorExecutionFixture, unittest.TestCase):
    def test_execute_pipeline_stops_on_critical_failure(self):
        orch = self._make_orchestrator()
        technical = MagicMock(agent_name="technical")
        technical.run.return_value = self._stage_result("technical", StageStatus.FAILED, error="boom")

        with patch.object(orch, "_build_agent_chain", return_value=[technical]):
            result = orch._execute_pipeline(AgentContext(query="test"))

        self.assertFalse(result.success)
        self.assertIn("technical", result.error)
        self.assertEqual(result.total_tokens, 0)

    def test_execute_pipeline_degrades_on_intel_failure(self):
        orch = self._make_orchestrator()
        ctx = AgentContext(query="test", stock_code="600519")
        ctx.add_opinion(AgentOpinion(agent_name="technical", signal="buy", confidence=0.8, reasoning="Strong trend"))

        intel = MagicMock(agent_name="intel")
        intel.run.return_value = self._stage_result("intel", StageStatus.FAILED, error="news down")
        decision = MagicMock(agent_name="decision")
        decision.run.return_value = self._stage_result("decision")

        with patch.object(orch, "_build_agent_chain", return_value=[intel, decision]):
            result = orch._execute_pipeline(ctx, parse_dashboard=False)

        self.assertTrue(result.success)
        self.assertIn("Analysis Summary", result.content)

    def test_execute_pipeline_degrades_on_skill_agent_failure_and_continues_to_decision(self):
        orch = self._make_orchestrator()
        orch.mode = "specialist"
        ctx = AgentContext(query="test", stock_code="600519")
        ctx.add_opinion(AgentOpinion(agent_name="technical", signal="buy", confidence=0.8, reasoning="Strong trend"))

        technical = MagicMock(agent_name="technical")
        technical.run.return_value = self._stage_result("technical")
        intel = MagicMock(agent_name="intel")
        intel.run.return_value = self._stage_result("intel")
        risk = MagicMock(agent_name="risk")
        risk.run.return_value = self._stage_result("risk")
        skill = MagicMock(agent_name="strategy_bull_trend")
        skill.run.return_value = self._stage_result("strategy_bull_trend", StageStatus.FAILED, error="skill boom")
        decision = MagicMock(agent_name="decision")
        decision.run.return_value = self._stage_result("decision")

        with patch.object(orch, "_build_agent_chain", return_value=[technical, intel, risk, decision]):
            with patch.object(orch, "_build_specialist_agents", return_value=[skill]):
                result = orch._execute_pipeline(ctx, parse_dashboard=False)

        self.assertTrue(result.success)
        self.assertIn("Analysis Summary", result.content)
        skill.run.assert_called_once()
        decision.run.assert_called_once()

    def test_pipeline_specialist_failure_uses_runtime_non_critical_contract_in_summary(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_risk_override=True))
        orch.mode = "specialist"
        ctx = AgentContext(query="test", stock_code="600519")
        captured_messages = []

        def fake_run_agent_loop(messages, **kwargs):
            captured_messages.append(messages)
            return SimpleNamespace(
                success=True,
                content=self._dashboard_json(decision_type="sell"),
                total_tokens=11,
                tool_calls_log=[],
                models_used=["test/model"],
            )

        technical = self._OpinionStage("technical", signal="sell", confidence=0.8)
        intel = self._OpinionStage("intel", signal="hold", confidence=0.5)
        risk = self._OpinionStage("risk", signal="hold", confidence=0.5)
        specialist = self._FailedStage("chan_theory", error="specialist failed")
        decision = self._decision_agent()

        with patch.object(orch, "_build_agent_chain", return_value=[technical, intel, risk, decision]):
            with patch.object(orch, "_build_specialist_agents", return_value=[specialist]):
                with patch.object(orch, "_aggregate_skill_opinions", return_value=None):
                    with patch("src.application.agent.runner.parse_dashboard_json", side_effect=lambda raw: json.loads(raw)):
                        with patch("src.application.agent.agents.base_agent.run_agent_loop", side_effect=fake_run_agent_loop):
                            result = orch._execute_pipeline(ctx, parse_dashboard=True)

        self.assertTrue(result.success)
        self.assertEqual(ctx.meta["degraded_stages"], [
            {"stage_name": "chan_theory", "status": "failed", "non_critical": True}
        ])

        combined = "\n".join(
            str(message.get("content", ""))
            for messages in captured_messages
            for message in messages
        )
        self.assertEqual(combined.count("## Agent Disagreement Summary"), 1)
        self.assertIn('"conflict_type": "partial_bearish_with_degraded_inputs"', combined)
        self.assertIn('"stage_name": "chan_theory"', combined)
        self.assertIn('"non_critical_stage_present": true', combined)
        self.assertIn('"non_critical": true', combined)

    def test_specialist_batch_timeout_is_split_across_concurrency_waves(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_skill_concurrency=2))

        self.assertEqual(
            orch._skill_batch_timeout_slice(3, timeout_seconds=30),
            15,
        )
        self.assertEqual(
            orch._skill_batch_timeout_slice(4, timeout_seconds=30),
            15,
        )
        self.assertEqual(
            orch._skill_batch_timeout_slice(2, timeout_seconds=30),
            30,
        )

    def test_execute_pipeline_skips_stage_when_remaining_budget_below_minimum(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_orchestrator_timeout_s=20))
        ctx = AgentContext(query="test", stock_code="600519", stock_name="贵州茅台")

        technical = MagicMock(agent_name="technical")

        def _run_technical(run_ctx, progress_callback=None):
            run_ctx.add_opinion(AgentOpinion(
                agent_name="technical",
                signal="buy",
                confidence=0.8,
                reasoning="技术面结构未出现明显拐点，趋势偏强。",
                raw_data={"ma_alignment": "bullish", "trend_score": 82, "volume_status": "normal"},
            ))
            return self._stage_result("technical")

        technical.run.side_effect = _run_technical
        intel = MagicMock(agent_name="intel", tool_names=["news_search"])
        intel.run.side_effect = AssertionError("intel should be skipped due to budget guard")
        times = iter([0.0, 0.2, 0.3, 14.6, 14.7])

        def _next_time():
            return next(times, 100.0)

        with patch.object(orch, "_build_agent_chain", return_value=[technical, intel]):
            with patch("src.application.agent.orchestrator.time.time", side_effect=_next_time):
                result = orch._execute_pipeline(ctx)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.dashboard)
        self.assertIsNotNone(result.content)
        self.assertIn("insufficient budget", (result.error or "").lower())
        self.assertIn("[降级结果]", result.dashboard["analysis_summary"])
        technical.run.assert_called_once()
        intel.run.assert_not_called()

    def test_execute_pipeline_skips_toolless_decision_with_low_remaining_budget(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_orchestrator_timeout_s=20))
        ctx = AgentContext(query="test", stock_code="600519", stock_name="贵州茅台")

        technical = MagicMock(agent_name="technical")

        def _run_technical(run_ctx, progress_callback=None):
            run_ctx.add_opinion(AgentOpinion(
                agent_name="technical",
                signal="buy",
                confidence=0.8,
                reasoning="技术面结构未出现明显拐点，趋势偏强。",
                raw_data={"ma_alignment": "bullish", "trend_score": 82, "volume_status": "normal"},
            ))
            return self._stage_result("technical")

        technical.run.side_effect = _run_technical
        decision = MagicMock(agent_name="decision", tool_names=[])

        def _run_decision(run_ctx, progress_callback=None):
            run_ctx.add_opinion(AgentOpinion(
                agent_name="decision",
                signal="buy",
                confidence=0.87,
                reasoning="综合技术与情绪判断，倾向于买入。",
            ))
            return self._stage_result("decision")

        decision.run.side_effect = _run_decision
        times = iter([0.0, 0.2, 0.3, 14.6, 14.7])

        def _next_time():
            return next(times, 100.0)

        with patch.object(orch, "_build_agent_chain", return_value=[technical, decision]):
            with patch("src.application.agent.orchestrator.time.time", side_effect=_next_time):
                result = orch._execute_pipeline(ctx)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.content)
        self.assertIn("insufficient budget", (result.error or "").lower())
        self.assertEqual(result.total_steps, 1)
        technical.run.assert_called_once()
        decision.run.assert_not_called()

    def test_execute_pipeline_first_stage_still_runs_when_timeout_short(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_orchestrator_timeout_s=10))
        ctx = AgentContext(query="test", stock_code="600519", stock_name="贵州茅台")

        technical = MagicMock(agent_name="technical")
        technical.run.side_effect = lambda run_ctx, progress_callback=None: self._stage_result("technical")
        times = iter([0.0, 0.2, 0.3, 0.4, 0.5])

        def _next_time():
            return next(times, 1.0)

        with patch.object(orch, "_build_agent_chain", return_value=[technical]):
            with patch("src.application.agent.orchestrator.time.time", side_effect=_next_time):
                result = orch._execute_pipeline(ctx)

        self.assertIsNotNone(result.error)
        self.assertEqual(result.total_steps, 1)
        technical.run.assert_called_once()
        self.assertNotIn("insufficient budget", (result.error or "").lower())

    def test_execute_pipeline_timeout_after_decision_preserves_dashboard(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_orchestrator_timeout_s=1, agent_risk_override=True))
        ctx = AgentContext(query="test", stock_code="600519", stock_name="贵州茅台")
        decision = MagicMock(agent_name="decision")

        def _run_decision(run_ctx, progress_callback=None):
            dashboard = {
                "stock_name": "贵州茅台",
                "decision_type": "strong_buy",
                "sentiment_score": 88,
                "operation_advice": {
                    "no_position": "分批布局",
                    "has_position": "继续持有",
                },
                "analysis_summary": "趋势仍强，回踩可观察。",
                "dashboard": {
                    "key_levels": {
                        "support": 1800,
                        "stop_loss": 1760,
                        "resistance": 1900,
                    }
                },
            }
            run_ctx.set_data("final_dashboard", dashboard)
            run_ctx.add_opinion(AgentOpinion(
                agent_name="decision",
                signal="buy",
                confidence=0.88,
                reasoning="趋势仍强，回踩可观察。",
                raw_data=dashboard,
            ))
            return self._stage_result("decision")

        decision.run.side_effect = _run_decision

        with patch.object(orch, "_build_agent_chain", return_value=[decision]):
            with patch("src.application.agent.orchestrator.time.time", side_effect=[0.0, 0.1, 1.2, 1.2, 1.2]):
                result = orch._execute_pipeline(ctx, parse_dashboard=True)

        self.assertTrue(result.success)
        self.assertIn("timed out", result.error)
        self.assertEqual(result.dashboard["decision_type"], "buy")
        self.assertEqual(result.dashboard["operation_advice"], "买入")
        self.assertEqual(
            result.dashboard["dashboard"]["battle_plan"]["sniper_points"]["stop_loss"],
            1760.0,
        )

    def test_execute_pipeline_timeout_after_intel_synthesizes_dashboard(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_orchestrator_timeout_s=1, agent_risk_override=True))
        ctx = AgentContext(query="test", stock_code="301308", stock_name="江波龙")
        ctx.set_data("realtime_quote", {"price": 326.17, "volume_ratio": 1.0, "turnover_rate": 6.77})
        ctx.set_data("chip_distribution", {"profit_ratio": 68.8, "avg_cost": 307.67, "concentration_90": 15.28})

        technical = MagicMock(agent_name="technical")
        intel = MagicMock(agent_name="intel")

        def _run_technical(run_ctx, progress_callback=None):
            run_ctx.add_opinion(AgentOpinion(
                agent_name="technical",
                signal="buy",
                confidence=0.75,
                reasoning="强势多头排列，价格回踩 MA5。",
                key_levels={"support": 301.61, "resistance": 340.44, "stop_loss": 295.0},
                raw_data={"ma_alignment": "bullish", "trend_score": 73, "volume_status": "normal"},
            ))
            return self._stage_result("technical")

        technical.run.side_effect = _run_technical
        intel.run.return_value = self._stage_result("intel")

        with patch.object(orch, "_build_agent_chain", return_value=[technical, intel]):
            with patch("src.application.agent.orchestrator.time.time", side_effect=[0.0, 0.1, 0.2, 0.3, 1.2, 1.2, 1.2]):
                result = orch._execute_pipeline(ctx, parse_dashboard=True)

        self.assertTrue(result.success)
        self.assertIn("timed out", result.error)
        self.assertEqual(result.dashboard["decision_type"], "buy")
        self.assertIn("降级结果", result.dashboard["analysis_summary"])
        self.assertEqual(
            result.dashboard["dashboard"]["battle_plan"]["sniper_points"]["stop_loss"],
            295.0,
        )

    def test_run_stage_agent_no_pipeline_budget_uses_sub_agent_limit(self):
        """When pipeline budget is 0 (timeout_seconds=None), sub-agent limit applies standalone."""
        orch = self._make_orchestrator(
            config=self._make_config_with_sub_agent_timeouts(
                agent_technical_agent_timeout_s=180,
            )
        )
        agent = MagicMock(agent_name="technical")
        result = self._stage_result("technical")
        agent.run.return_value = result

        orch._run_stage_agent(agent, AgentContext(query="test"), timeout_seconds=None)

        call_kwargs = agent.run.call_args.kwargs
        self.assertEqual(call_kwargs["timeout_seconds"], 180)

    def test_run_stage_agent_pipeline_budget_larger_than_agent_limit_clamps_to_agent(self):
        """Pipeline remaining > sub-agent limit → use smaller agent limit."""
        orch = self._make_orchestrator(
            config=self._make_config_with_sub_agent_timeouts(
                agent_technical_agent_timeout_s=120,
            )
        )
        agent = MagicMock(agent_name="technical")
        result = self._stage_result("technical")
        agent.run.return_value = result

        orch._run_stage_agent(agent, AgentContext(query="test"), timeout_seconds=300)

        call_kwargs = agent.run.call_args.kwargs
        self.assertEqual(call_kwargs["timeout_seconds"], 120)

    def test_run_stage_agent_pipeline_budget_smaller_than_agent_limit_uses_pipeline(self):
        """Pipeline remaining < sub-agent limit → use smaller pipeline remaining."""
        orch = self._make_orchestrator(
            config=self._make_config_with_sub_agent_timeouts(
                agent_technical_agent_timeout_s=300,
            )
        )
        agent = MagicMock(agent_name="technical")
        result = self._stage_result("technical")
        agent.run.return_value = result

        orch._run_stage_agent(agent, AgentContext(query="test"), timeout_seconds=60)

        call_kwargs = agent.run.call_args.kwargs
        self.assertEqual(call_kwargs["timeout_seconds"], 60)

    def test_run_stage_agent_no_sub_agent_limit_passes_pipeline_budget_through(self):
        """No sub-agent limit configured (all 0) → pipeline budget passed through unchanged."""
        orch = self._make_orchestrator(
            config=self._make_config_with_sub_agent_timeouts(),
        )
        agent = MagicMock(agent_name="technical")
        result = self._stage_result("technical")
        agent.run.return_value = result

        orch._run_stage_agent(agent, AgentContext(query="test"), timeout_seconds=300)

        call_kwargs = agent.run.call_args.kwargs
        self.assertEqual(call_kwargs["timeout_seconds"], 300)

    def test_chat_persists_failure_message(self):
        from src.application.agent.orchestrator import OrchestratorResult

        orch = self._make_orchestrator()
        fake_result = OrchestratorResult(success=False, error="boom")

        with patch.object(orch, "_execute_pipeline", return_value=fake_result):
            with patch("src.application.agent.orchestrator.build_visible_chat_history", return_value=[]):
                with patch("src.application.agent.conversation.conversation_manager.add_message") as add_message:
                    result = orch.chat("hello", "session-2")

        self.assertFalse(result.success)
        add_message.assert_any_call("session-2", "assistant", "[分析失败] boom")

    def test_execute_pipeline_fails_when_dashboard_parse_fails(self):
        orch = self._make_orchestrator()
        ctx = AgentContext(query="test", stock_code="600519")
        decision = MagicMock(agent_name="decision")

        def fake_run(pipeline_ctx, progress_callback=None):
            pipeline_ctx.set_data("final_dashboard_raw", "not valid json")
            return self._stage_result("decision")

        decision.run.side_effect = fake_run

        with patch.object(orch, "_build_agent_chain", return_value=[decision]):
            result = orch._execute_pipeline(ctx, parse_dashboard=True)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Failed to parse dashboard JSON from agent response")
