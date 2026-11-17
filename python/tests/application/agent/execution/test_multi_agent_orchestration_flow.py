"""Tests for multi agent orchestration flow."""

from tests.application.agent._multi_agent_support import (
    AgentContext,
    AgentOpinion,
    Config,
    ConversationRepository,
    DatabaseManager,
    MagicMock,
    SimpleNamespace,
    _TestOrchestratorExecutionFixture,
    json,
    patch,
    unittest,
)


class TestOrchestratorExecution(_TestOrchestratorExecutionFixture, unittest.TestCase):
    def test_prepare_agent_uses_default_constant_as_raise_threshold(self):
        orch = self._make_orchestrator()
        agent = MagicMock(agent_name="technical", max_steps=6)

        prepared = orch._prepare_agent(agent)
        self.assertIs(prepared, agent)
        self.assertEqual(agent.max_steps, 6)

        orch.max_steps = 12
        agent.max_steps = 6
        orch._prepare_agent(agent)
        self.assertEqual(agent.max_steps, 12)

        orch.max_steps = 5
        agent.max_steps = 6
        orch._prepare_agent(agent)
        self.assertEqual(agent.max_steps, 5)

    def test_pipeline_summary_and_risk_override_share_disabled_override_contract(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_risk_override=False))
        ctx = AgentContext(query="test", stock_code="600519")
        captured_messages = []

        def fake_run_agent_loop(messages, **kwargs):
            captured_messages.append(messages)
            return SimpleNamespace(
                success=True,
                content=self._dashboard_json(decision_type="buy"),
                total_tokens=11,
                tool_calls_log=[],
                models_used=["test/model"],
            )

        technical = self._OpinionStage("technical", signal="buy", confidence=0.8)
        risk = self._OpinionStage(
            "risk",
            signal="sell",
            confidence=0.9,
            raw_data={"veto_buy": True},
        )
        decision = self._decision_agent()

        with patch.object(orch, "_build_agent_chain", return_value=[technical, risk, decision]):
            with patch("src.application.agent.runner.parse_dashboard_json", side_effect=lambda raw: json.loads(raw)):
                with patch("src.application.agent.agents.base_agent.run_agent_loop", side_effect=fake_run_agent_loop):
                    result = orch._execute_pipeline(ctx, parse_dashboard=True)

        self.assertTrue(result.success)
        self.assertEqual(result.dashboard["decision_type"], "buy")
        self.assertIsNone(ctx.get_data("risk_override_applied"))

        combined = "\n".join(
            str(message.get("content", ""))
            for messages in captured_messages
            for message in messages
        )
        self.assertEqual(combined.count("## Agent Disagreement Summary"), 1)
        self.assertIn('"risk_override_present": false', combined)
        self.assertIn('"override_enabled": false', combined)
        self.assertIn('"override_trigger_present": true', combined)
        self.assertNotIn('"conflict_type": "risk_override"', combined)
        self.assertNotIn("[Pre-fetched: agent_disagreement_summary]", combined)

    def test_pipeline_risk_level_high_is_evidence_not_runtime_override(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_risk_override=True))
        ctx = AgentContext(query="test", stock_code="600519")
        captured_messages = []

        def fake_run_agent_loop(messages, **kwargs):
            captured_messages.append(messages)
            return SimpleNamespace(
                success=True,
                content=self._dashboard_json(decision_type="buy"),
                total_tokens=11,
                tool_calls_log=[],
                models_used=["test/model"],
            )

        technical = self._OpinionStage("technical", signal="buy", confidence=0.8)
        risk = self._OpinionStage(
            "risk",
            signal="sell",
            confidence=0.9,
            raw_data={"risk_level": "high"},
        )
        decision = self._decision_agent()

        with patch.object(orch, "_build_agent_chain", return_value=[technical, risk, decision]):
            with patch("src.application.agent.runner.parse_dashboard_json", side_effect=lambda raw: json.loads(raw)):
                with patch("src.application.agent.agents.base_agent.run_agent_loop", side_effect=fake_run_agent_loop):
                    result = orch._execute_pipeline(ctx, parse_dashboard=True)

        self.assertTrue(result.success)
        self.assertEqual(result.dashboard["decision_type"], "buy")
        self.assertIsNone(ctx.get_data("risk_override_applied"))

        combined = "\n".join(
            str(message.get("content", ""))
            for messages in captured_messages
            for message in messages
        )
        self.assertEqual(combined.count("## Agent Disagreement Summary"), 1)
        self.assertIn('"evidence_present": true', combined)
        self.assertIn('"override_trigger_present": false', combined)
        self.assertIn('"risk_override_present": false', combined)
        self.assertNotIn('"conflict_type": "risk_override"', combined)

    def test_pipeline_enabled_risk_veto_is_reflected_in_summary_and_final_dashboard(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_risk_override=True))
        ctx = AgentContext(query="test", stock_code="600519")
        captured_messages = []

        def fake_run_agent_loop(messages, **kwargs):
            captured_messages.append(messages)
            return SimpleNamespace(
                success=True,
                content=self._dashboard_json(decision_type="buy"),
                total_tokens=11,
                tool_calls_log=[],
                models_used=["test/model"],
            )

        technical = self._OpinionStage("technical", signal="buy", confidence=0.8)
        risk = self._OpinionStage(
            "risk",
            signal="sell",
            confidence=0.9,
            raw_data={"veto_buy": True, "reasoning": "material risk"},
        )
        decision = self._decision_agent()

        with patch.object(orch, "_build_agent_chain", return_value=[technical, risk, decision]):
            with patch("src.application.agent.runner.parse_dashboard_json", side_effect=lambda raw: json.loads(raw)):
                with patch("src.application.agent.agents.base_agent.run_agent_loop", side_effect=fake_run_agent_loop):
                    result = orch._execute_pipeline(ctx, parse_dashboard=True)

        self.assertTrue(result.success)
        self.assertEqual(result.dashboard["decision_type"], "hold")
        self.assertEqual(ctx.get_data("risk_override_applied"), {
            "from": "buy",
            "to": "hold",
            "adjustment": "veto",
            "reason": "risk_veto",
        })

        combined = "\n".join(
            str(message.get("content", ""))
            for messages in captured_messages
            for message in messages
        )
        self.assertEqual(combined.count("## Agent Disagreement Summary"), 1)
        self.assertIn('"conflict_type": "risk_override"', combined)
        self.assertIn('"risk_override_present": true', combined)
        self.assertIn('"override_enabled": true', combined)
        self.assertIn('"override_trigger_present": true', combined)

    def test_pipeline_degraded_directional_input_is_not_reported_as_consensus(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_risk_override=True))
        ctx = AgentContext(query="test", stock_code="600519")
        captured_messages = []

        def fake_run_agent_loop(messages, **kwargs):
            captured_messages.append(messages)
            return SimpleNamespace(
                success=True,
                content=self._dashboard_json(decision_type="buy"),
                total_tokens=11,
                tool_calls_log=[],
                models_used=["test/model"],
            )

        technical = self._OpinionStage("technical", signal="buy", confidence=0.8)
        intel = self._FailedStage("intel", error="news source failed")
        decision = self._decision_agent()

        with patch.object(orch, "_build_agent_chain", return_value=[technical, intel, decision]):
            with patch("src.application.agent.runner.parse_dashboard_json", side_effect=lambda raw: json.loads(raw)):
                with patch("src.application.agent.agents.base_agent.run_agent_loop", side_effect=fake_run_agent_loop):
                    result = orch._execute_pipeline(ctx, parse_dashboard=True)

        self.assertTrue(result.success)
        self.assertEqual(ctx.meta["degraded_stages"], [
            {"stage_name": "intel", "status": "failed", "non_critical": True}
        ])

        combined = "\n".join(
            str(message.get("content", ""))
            for messages in captured_messages
            for message in messages
        )
        self.assertEqual(combined.count("## Agent Disagreement Summary"), 1)
        self.assertIn('"conflict_type": "partial_bullish_with_degraded_inputs"', combined)
        self.assertIn('"decision_path_hint": "state_degraded_inputs_before_any_bullish_lean"', combined)
        self.assertIn('"stage_name": "intel"', combined)
        self.assertIn('"non_critical": true', combined)
        self.assertNotIn('"conflict_type": "aligned_bullish"', combined)

    def test_strategy_engine_preserves_scheduler_diagnostics(self):
        orch = self._make_orchestrator()
        ctx = AgentContext(
            query="test",
            stock_code="600519",
            meta={
                "invalid_opinions": [
                    {
                        "agent_name": "skill_fund_flow",
                        "reason": "skill_timeout",
                    }
                ]
            },
        )
        ctx.add_opinion(AgentOpinion(
            agent_name="skill_hot_theme",
            signal="moon",
            confidence=0.9,
            reasoning="bad fixture",
        ))
        ctx.add_opinion(AgentOpinion(
            agent_name="skill_bull_trend",
            signal="buy",
            confidence=0.8,
            reasoning="valid fixture",
            raw_data={"skill_id": "bull_trend"},
        ))

        orch._run_strategy_engine(ctx)

        invalid_bucket = ctx.meta["invalid_opinions"]
        self.assertEqual([item["agent_name"] for item in invalid_bucket], [
            "skill_fund_flow",
            "skill_hot_theme",
        ])
        self.assertEqual(invalid_bucket[0]["reason"], "skill_timeout")
        self.assertEqual(invalid_bucket[1]["reason"], "unrecognized_signal")
        synthesis = ctx.get_data("skill_consensus")["strategy_synthesis"]
        self.assertEqual(synthesis["summary_params"]["opinion_count"], 1)
        self.assertEqual(synthesis["summary_params"]["invalid_opinion_count"], 2)
        self.assertEqual(synthesis["summary_params"]["total_opinion_count"], 3)

        from src.application.agent.agents.decision_agent import DecisionAgent
        prompt = DecisionAgent(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
        ).build_user_message(ctx)
        self.assertIn("执行超时 1 个", prompt)
        self.assertIn("signal 无法识别 1 个", prompt)

    def test_execute_pipeline_times_out_after_stage(self):
        orch = self._make_orchestrator(config=SimpleNamespace(agent_orchestrator_timeout_s=1))
        agent = MagicMock(agent_name="technical")
        agent.run.return_value = self._stage_result("technical")

        with patch.object(orch, "_build_agent_chain", return_value=[agent]):
            with patch("src.application.agent.orchestrator.time.time", side_effect=[0.0, 0.1, 1.2, 1.2, 1.2, 1.2]):
                result = orch._execute_pipeline(AgentContext(query="test"))

        self.assertFalse(result.success)
        self.assertIn("timed out", result.error)

    def test_run_stage_agent_skill_agent_fallback_applies_skill_clamp(self):
        """Skill agents (in _skill_agent_names) use the 'skill' clamp key as fallback."""
        orch = self._make_orchestrator(
            config=self._make_config_with_sub_agent_timeouts(
                agent_skill_agent_timeout_s=90,
            )
        )
        orch._skill_agent_names = {"bull_trend_specialist", "volume_breakout_specialist"}
        agent = MagicMock(agent_name="bull_trend_specialist")
        result = self._stage_result("bull_trend_specialist")
        agent.run.return_value = result

        orch._run_stage_agent(agent, AgentContext(query="test"), timeout_seconds=300)

        call_kwargs = agent.run.call_args.kwargs
        self.assertEqual(call_kwargs["timeout_seconds"], 90)

    def test_run_stage_agent_skill_agent_exact_name_match_wins_over_skill_fallback(self):
        """Exact agent_name match takes priority over _skill_agent_names fallback."""
        orch = self._make_orchestrator(
            config=self._make_config_with_sub_agent_timeouts(
                agent_skill_agent_timeout_s=90,
                agent_decision_agent_timeout_s=150,
            )
        )
        orch._skill_agent_names = {"decision"}
        agent = MagicMock(agent_name="decision")
        result = self._stage_result("decision")
        agent.run.return_value = result

        orch._run_stage_agent(agent, AgentContext(query="test"), timeout_seconds=300)

        call_kwargs = agent.run.call_args.kwargs
        # Exact name "decision" → 150, not skill fallback 90
        self.assertEqual(call_kwargs["timeout_seconds"], 150)

    def test_chat_uses_compressed_history_builder(self):
        from src.application.agent.orchestrator import OrchestratorResult

        orch = self._make_orchestrator()

        with patch.object(orch, "_execute_pipeline", return_value=OrchestratorResult(success=True, content="ok")):
            with patch("src.application.agent.orchestrator.build_visible_chat_history", return_value=[]) as build_history:
                with patch("src.application.agent.conversation.conversation_manager.get_or_create"):
                    with patch("src.application.agent.conversation.conversation_manager.add_message"):
                        orch.chat("hello", "session-1")

        build_history.assert_called_once()
        self.assertEqual(build_history.call_args.args[0], "session-1")
        self.assertIs(build_history.call_args.args[1], orch.llm_adapter)

    def test_chat_does_not_read_or_write_provider_trace(self):
        from src.application.agent.orchestrator import OrchestratorResult

        DatabaseManager.reset_instance()
        Config.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")
        session_id = "multi-agent-trace-boundary"
        user_id = db.save_conversation_message(session_id, "user", "previous question")
        assistant_id = db.save_conversation_message(session_id, "assistant", "previous answer")
        db.save_agent_provider_turn(
            session_id=session_id,
            run_id="run-existing",
            provider="deepseek",
            model="deepseek/deepseek-chat",
            anchor_user_message_id=user_id,
            anchor_assistant_message_id=assistant_id,
            messages=[
                {
                    "role": "assistant",
                    "reasoning_content": "reasoning",
                    "tool_calls": [{"id": "call_1", "name": "echo", "arguments": {}}],
                },
                {"role": "tool", "tool_call_id": "call_1", "content": "tool-result"},
            ],
            contains_reasoning=True,
            contains_tool_calls=True,
            contains_thinking_blocks=False,
            must_roundtrip=True,
            estimated_tokens=10,
        )

        orch = self._make_orchestrator()
        try:
            with patch.object(orch, "_execute_pipeline", return_value=OrchestratorResult(success=True, content="ok")):
                with patch("src.application.agent.orchestrator.build_visible_chat_history", return_value=[]) as build_history:
                    with patch.object(db, "get_agent_provider_turns", wraps=db.get_agent_provider_turns) as get_turns, patch(
                        "src.application.agent.conversation._conversation_port",
                        ConversationRepository(db)
                    ):
                        result = orch.chat("hello", session_id)

            self.assertTrue(result.success)
            build_history.assert_called_once()
            get_turns.assert_not_called()
            rows = db.get_agent_provider_turns(session_id)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["run_id"], "run-existing")
        finally:
            DatabaseManager.reset_instance()
            Config.reset_instance()

    def test_chat_persists_user_and_assistant_messages(self):
        from src.application.agent.orchestrator import OrchestratorResult

        orch = self._make_orchestrator()
        fake_result = OrchestratorResult(success=True, content="assistant reply")

        with patch.object(orch, "_execute_pipeline", return_value=fake_result):
            with patch("src.application.agent.orchestrator.build_visible_chat_history", return_value=[]):
                with patch("src.application.agent.conversation.conversation_manager.add_message") as add_message:
                    result = orch.chat("hello", "session-1")

        self.assertTrue(result.success)
        self.assertEqual(add_message.call_count, 2)
        add_message.assert_any_call("session-1", "user", "hello")
        add_message.assert_any_call("session-1", "assistant", "assistant reply")

    def test_chat_transaction_persists_user_before_multi_agent_execution(self):
        """SSE acceptance can occur after persistence but before the pipeline starts."""
        from src.application.agent.orchestrator import OrchestratorResult

        orch = self._make_orchestrator()
        fake_result = OrchestratorResult(success=True, content="assistant reply")

        with patch.object(orch, "_execute_pipeline", return_value=fake_result) as execute_pipeline:
            with patch("src.application.agent.orchestrator.build_visible_chat_history", return_value=[]):
                with patch("src.application.agent.conversation.conversation_manager.get_or_create"):
                    with patch("src.application.agent.conversation.conversation_manager.add_message") as add_message:
                        turn = orch.prepare_turn(message="hello", session_id="session-accepted")

                        add_message.assert_called_once_with("session-accepted", "user", "hello")
                        execute_pipeline.assert_not_called()

                        result = orch.execute_turn(turn)

        self.assertTrue(result.success)
        execute_pipeline.assert_called_once_with(
            turn.context,
            parse_dashboard=False,
            progress_callback=None,
        )
        self.assertEqual(add_message.call_args_list[-1].args, (
            "session-accepted",
            "assistant",
            "assistant reply",
        ))

    def test_execute_pipeline_chat_prefers_free_form_response(self):
        orch = self._make_orchestrator()
        ctx = AgentContext(query="请总结一下", stock_code="600519")
        ctx.meta["response_mode"] = "chat"
        decision = MagicMock(agent_name="decision")

        def fake_run(pipeline_ctx, progress_callback=None):
            pipeline_ctx.set_data("final_dashboard", {"decision_type": "buy", "analysis_summary": "json dashboard"})
            pipeline_ctx.set_data("final_response_text", "这是自然语言回复")
            return self._stage_result("decision", raw_text="这是自然语言回复")

        decision.run.side_effect = fake_run

        with patch.object(orch, "_build_agent_chain", return_value=[decision]):
            result = orch._execute_pipeline(ctx, parse_dashboard=False)

        self.assertTrue(result.success)
        self.assertEqual(result.content, "这是自然语言回复")

    def test_strategy_agents_are_selected_after_technical_stage(self):
        orch = self._make_orchestrator()
        orch.mode = "specialist"
        ctx = AgentContext(query="分析600519", stock_code="600519")
        ctx.meta["response_mode"] = "chat"

        technical = MagicMock(agent_name="technical")

        def _run_technical(run_ctx, progress_callback=None):
            run_ctx.add_opinion(AgentOpinion(
                agent_name="technical",
                signal="buy",
                confidence=0.8,
                reasoning="trend ok",
                raw_data={"ma_alignment": "bullish", "trend_score": 78, "volume_status": "normal"},
            ))
            return self._stage_result("technical")

        technical.run.side_effect = _run_technical

        intel = MagicMock(agent_name="intel")
        intel.run.return_value = self._stage_result("intel")

        risk = MagicMock(agent_name="risk")
        risk.run.return_value = self._stage_result("risk")

        strategy = MagicMock(agent_name="strategy_bull_trend")

        def _run_strategy(run_ctx, progress_callback=None):
            run_ctx.add_opinion(AgentOpinion(
                agent_name="strategy_bull_trend",
                signal="buy",
                confidence=0.7,
                reasoning="strategy ok",
            ))
            return self._stage_result("strategy_bull_trend")

        strategy.run.side_effect = _run_strategy

        decision = MagicMock(agent_name="decision")
        decision.run.return_value = self._stage_result("decision", raw_text="final answer")

        def _build_specialist_agents(run_ctx):
            self.assertTrue(any(op.agent_name == "technical" for op in run_ctx.opinions))
            return [strategy]

        with patch.object(orch, "_build_agent_chain", return_value=[technical, intel, risk, decision]):
            with patch.object(orch, "_build_specialist_agents", side_effect=_build_specialist_agents) as build_specialist_agents:
                result = orch._execute_pipeline(ctx, parse_dashboard=False)

        self.assertTrue(result.success)
        self.assertEqual(result.content, "final answer")
        build_specialist_agents.assert_called_once()
        strategy.run.assert_called_once()
