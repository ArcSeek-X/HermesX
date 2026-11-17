"""Tests for agent executor execution."""

from tests.application.agent._agent_executor_support import (
    AgentExecutor,
    AgentResult,
    Config,
    ConversationRepository,
    DatabaseManager,
    LLMResponse,
    SAMPLE_DASHBOARD,
    SimpleNamespace,
    StockScope,
    ToolCall,
    UsageTelemetryAdapter,
    _TestAgentExecutorFixture,
    _make_mock_adapter,
    _make_registry_with_echo,
    _make_stock_registry,
    json,
    normalize_litellm_usage,
    patch,
    resolve_stock_scope,
    run_agent_loop,
    unittest,
)


class TestAgentExecutor(_TestAgentExecutorFixture, unittest.TestCase):
    def test_run_does_not_pass_stock_scope_to_dashboard_path(self):
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        executor = AgentExecutor(registry, adapter, max_steps=2)
        captured = {}

        def fake_run_loop(messages, tool_decls, parse_dashboard, progress_callback=None, stock_scope=None):
            captured["stock_scope"] = stock_scope
            return AgentResult(success=True, content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False))

        with patch.object(executor, "_run_loop", side_effect=fake_run_loop):
            result = executor.run("Analyze 600519", context={"stock_code": "600519"})

        self.assertTrue(result.success)
        self.assertIsNone(captured["stock_scope"])

    def test_resolve_stock_scope_compare_collects_multiple_normalized_codes(self):
        result = resolve_stock_scope(
            "比较 600519 和 AAPL",
            {"stock_code": "600519", "stock_name": "贵州茅台"},
        )

        self.assertEqual(result.stock_scope.mode, "compare")
        self.assertEqual(result.effective_context["stock_code"], "600519")
        self.assertEqual(result.effective_context["stock_name"], "贵州茅台")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519", "AAPL"})

    def test_default_initial_scope_keeps_litellm_behavior(self):
        result = resolve_stock_scope("分析 AAPL", None)

        self.assertIsNone(result.stock_scope)

    def test_strict_initial_scope_without_code_remains_unscoped(self):
        result = resolve_stock_scope("分析茅台", None, strict_initial_scope=True)

        self.assertIsNone(result.stock_scope)

    def test_resolve_stock_scope_keeps_ambiguous_bare_code_on_current_stock(self):
        result = resolve_stock_scope("AAPL", {"stock_code": "600519", "stock_name": "贵州茅台"})

        self.assertEqual(result.stock_scope.mode, "maintain")
        self.assertEqual(result.effective_context["stock_code"], "600519")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519"})

    def test_run_agent_loop_does_not_persist_agent_usage_without_provider_usage(self):
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        adapter.call_with_tools.return_value = LLMResponse(
            content="Done.",
            tool_calls=[],
            usage={},
            provider="openai",
            model="openai/gpt-test",
        )

        with patch("src.application.agent.runner._usage_telemetry_port", UsageTelemetryAdapter()) as usage_port, patch.object(usage_port, "persist") as persist_usage:
            result = run_agent_loop(
                messages=[{"role": "user", "content": "Analyze"}],
                tool_registry=registry,
                llm_adapter=adapter,
                max_steps=1,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.total_tokens, 0)
        persist_usage.assert_not_called()

    def test_run_agent_loop_does_not_persist_metadata_only_provider_usage(self):
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        adapter.call_with_tools.return_value = LLMResponse(
            content="Done.",
            tool_calls=[],
            usage=normalize_litellm_usage(
                {"estimated_prefix_tokens": 123},
                model="openai/gpt-4o",
            ),
            provider="openai",
            model="openai/gpt-test",
        )

        with patch("src.application.agent.runner._usage_telemetry_port", UsageTelemetryAdapter()) as usage_port, patch.object(usage_port, "persist") as persist_usage:
            result = run_agent_loop(
                messages=[{"role": "user", "content": "Analyze"}],
                tool_registry=registry,
                llm_adapter=adapter,
                max_steps=1,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.total_tokens, 0)
        persist_usage.assert_not_called()

    def test_run_agent_loop_persists_invalid_provider_usage_diagnostics(self):
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        usage = normalize_litellm_usage({"prompt_tokens": -1}, model="openai/gpt-4o")
        adapter.call_with_tools.return_value = LLMResponse(
            content="Done.",
            tool_calls=[],
            usage=usage,
            provider="openai",
            model="openai/gpt-test",
        )

        with patch("src.application.agent.runner._usage_telemetry_port", UsageTelemetryAdapter()) as usage_port, patch.object(usage_port, "persist") as persist_usage:
            result = run_agent_loop(
                messages=[{"role": "user", "content": "Analyze"}],
                tool_registry=registry,
                llm_adapter=adapter,
                max_steps=1,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.total_tokens, 0)
        self.assertEqual(usage["cache_observation"], "invalid_provider_usage")
        persist_usage.assert_called_once_with(usage, "openai/gpt-test", call_type="agent")

    def test_run_agent_loop_persists_agent_usage_with_provider_usage(self):
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        usage = {"total_tokens": 5}
        adapter.call_with_tools.return_value = LLMResponse(
            content="Done.",
            tool_calls=[],
            usage=usage,
            provider="openai",
            model="openai/gpt-test",
        )

        with patch("src.application.agent.runner._usage_telemetry_port", UsageTelemetryAdapter()) as usage_port, patch.object(usage_port, "persist") as persist_usage:
            result = run_agent_loop(
                messages=[{"role": "user", "content": "Analyze"}],
                tool_registry=registry,
                llm_adapter=adapter,
                max_steps=1,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.total_tokens, 5)
        persist_usage.assert_called_once_with(usage, "openai/gpt-test", call_type="agent")

    def test_run_agent_loop_skips_usage_persist_when_telemetry_port_unwired(self):
        """W4.2: 用量端口未装配时静默跳过，不得回退直连 storage，也不得抛错。"""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        adapter.call_with_tools.return_value = LLMResponse(
            content="Done.",
            tool_calls=[],
            usage={"total_tokens": 5},
            provider="openai",
            model="openai/gpt-test",
        )

        with patch("src.application.agent.runner._usage_telemetry_port", None), patch(
            "src.storage.persist_llm_usage"
        ) as storage_persist:
            result = run_agent_loop(
                messages=[{"role": "user", "content": "Analyze"}],
                tool_registry=registry,
                llm_adapter=adapter,
                max_steps=1,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.total_tokens, 5)
        storage_persist.assert_not_called()

    def test_run_agent_loop_blocks_numeric_conflicting_stock_code(self):
        executed_calls = []
        registry = _make_stock_registry(executed_calls)
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Need quote.",
                tool_calls=[
                    ToolCall(id="quote_1", name="get_realtime_quote", arguments={"stock_code": 123456}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content="Blocked wrong numeric code.",
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]

        result = run_agent_loop(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "继续看当前标的"},
            ],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            stock_scope=StockScope(expected_stock_code="600519", allowed_stock_codes={"600519"}),
        )

        self.assertTrue(result.success)
        self.assertEqual(executed_calls, [])
        self.assertTrue(result.tool_calls_log[0]["guarded"])
        self.assertEqual(result.tool_calls_log[0]["requested_stock_code"], "123456")
        tool_messages = [msg for msg in result.messages if msg.get("role") == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertIn("stock_scope_violation", tool_messages[0]["content"])

    def test_run_agent_loop_allows_explicit_allowed_stock_code_and_hk_equivalent(self):
        executed_calls = []
        registry = _make_stock_registry(executed_calls)
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Need quote.",
                tool_calls=[
                    ToolCall(id="quote_1", name="get_realtime_quote", arguments={"stock_code": "1810.HK"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content="AAPL and HK allowed.",
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]

        result = run_agent_loop(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "比较 HK01810 和 600519"},
            ],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            stock_scope=StockScope(
                expected_stock_code="600519",
                allowed_stock_codes={"600519", "HK01810"},
                mode="compare",
            ),
        )

        self.assertTrue(result.success)
        self.assertEqual(executed_calls, [("quote", "1810.HK")])
        self.assertFalse(result.tool_calls_log[0].get("guarded", False))

    def test_run_agent_loop_allows_compare_hint_stock_code(self):
        executed_calls = []
        registry = _make_stock_registry(executed_calls)
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Need quote.",
                tool_calls=[
                    ToolCall(id="quote_1", name="get_realtime_quote", arguments={"stock_code": "AAPL"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content="Compared allowed stock.",
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]
        message = "分析 600519 和 AAPL 的差异"
        scope = resolve_stock_scope(message, {"stock_code": "600519", "stock_name": "贵州茅台"}).stock_scope

        result = run_agent_loop(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": message},
            ],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            stock_scope=scope,
        )

        self.assertTrue(result.success)
        self.assertEqual(scope.mode, "compare")
        self.assertEqual(scope.allowed_stock_codes, {"600519", "AAPL"})
        self.assertEqual(executed_calls, [("quote", "AAPL")])
        self.assertFalse(result.tool_calls_log[0].get("guarded", False))

    def test_run_agent_loop_allows_plain_hk_code_from_compare_scope(self):
        executed_calls = []
        registry = _make_stock_registry(executed_calls)
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Need quote.",
                tool_calls=[
                    ToolCall(id="quote_1", name="get_realtime_quote", arguments={"stock_code": "01810"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content="Compared allowed HK stock.",
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]
        message = "比较 01810 和 AAPL"
        scope = resolve_stock_scope(message, {"stock_code": "600519", "stock_name": "贵州茅台"}).stock_scope

        result = run_agent_loop(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": message},
            ],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            stock_scope=scope,
        )

        self.assertTrue(result.success)
        self.assertEqual(scope.mode, "compare")
        self.assertEqual(scope.allowed_stock_codes, {"600519", "HK01810", "AAPL"})
        self.assertEqual(executed_calls, [("quote", "01810")])
        self.assertFalse(result.tool_calls_log[0].get("guarded", False))

    def test_run_agent_loop_allows_choice_compare_stock_codes(self):
        executed_calls = []
        registry = _make_stock_registry(executed_calls)
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Need quotes.",
                tool_calls=[
                    ToolCall(id="quote_1", name="get_realtime_quote", arguments={"stock_code": "AAPL"}),
                    ToolCall(id="quote_2", name="get_realtime_quote", arguments={"stock_code": "TSLA"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content="Compared allowed stocks.",
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]
        message = "AAPL 和 TSLA 哪个更值得买"
        scope = resolve_stock_scope(message, {"stock_code": "600519", "stock_name": "贵州茅台"}).stock_scope

        result = run_agent_loop(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": message},
            ],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            stock_scope=scope,
        )

        self.assertTrue(result.success)
        self.assertEqual(scope.mode, "compare")
        self.assertEqual(scope.allowed_stock_codes, {"600519", "AAPL", "TSLA"})
        self.assertEqual(executed_calls, [("quote", "AAPL"), ("quote", "TSLA")])
        self.assertFalse(result.tool_calls_log[0].get("guarded", False))
        self.assertFalse(result.tool_calls_log[1].get("guarded", False))

    def test_run_agent_loop_blocks_exchange_affix_tokens_from_compare_scope(self):
        cases = [
            ("比较 1810.HK 和 AAPL", "HK"),
            ("比较 600519.SH 和 AAPL", "SH"),
            ("比较 000001.SZ 和 AAPL", "SZ"),
            ("比较 600519.SS 和 AAPL", "SS"),
            ("比较 SH600519 和 AAPL", "SH"),
            ("比较 SZ000001 和 AAPL", "SZ"),
            ("比较 BJ920748 和 AAPL", "BJ"),
            ("比较 HK01810 和 AAPL", "HK"),
            ("比较 600519 SH 和 AAPL", "SH"),
            ("比较 000001 SZ 和 AAPL", "SZ"),
            ("比较 920748 BJ 和 AAPL", "BJ"),
            ("比较 01810 HK 和 AAPL", "HK"),
            ("比较 600519 SS 和 AAPL", "SS"),
        ]

        for message, requested_code in cases:
            with self.subTest(message=message, requested_code=requested_code):
                executed_calls = []
                registry = _make_stock_registry(executed_calls)
                adapter = _make_mock_adapter()
                adapter.call_with_tools.side_effect = [
                    LLMResponse(
                        content="Need quote.",
                        tool_calls=[
                            ToolCall(
                                id="quote_1",
                                name="get_realtime_quote",
                                arguments={"stock_code": requested_code},
                            ),
                        ],
                        usage={"total_tokens": 10},
                        provider="openai",
                    ),
                    LLMResponse(
                        content="Blocked invalid suffix token.",
                        tool_calls=[],
                        usage={"total_tokens": 10},
                        provider="openai",
                    ),
                ]
                scope = resolve_stock_scope(message, {"stock_code": "600519"}).stock_scope

                self.assertNotIn(requested_code, scope.allowed_stock_codes)
                result = run_agent_loop(
                    messages=[
                        {"role": "system", "content": "system"},
                        {"role": "user", "content": message},
                    ],
                    tool_registry=registry,
                    llm_adapter=adapter,
                    max_steps=3,
                    stock_scope=scope,
                )

                self.assertTrue(result.success)
                self.assertEqual(executed_calls, [])
                self.assertTrue(result.tool_calls_log[0]["guarded"])
                self.assertEqual(result.tool_calls_log[0]["requested_stock_code"], requested_code)
                tool_messages = [msg for msg in result.messages if msg.get("role") == "tool"]
                self.assertEqual(len(tool_messages), 1)
                self.assertIn("stock_scope_violation", tool_messages[0]["content"])

    def test_run_agent_loop_blocks_indicator_tokens_from_followup(self):
        cases = [
            ("分析 MA 均线", "MA"),
            ("分析 KDJ 指标", "KDJ"),
        ]

        for message, requested_code in cases:
            with self.subTest(message=message, requested_code=requested_code):
                executed_calls = []
                registry = _make_stock_registry(executed_calls)
                adapter = _make_mock_adapter()
                adapter.call_with_tools.side_effect = [
                    LLMResponse(
                        content="Need quote.",
                        tool_calls=[
                            ToolCall(
                                id="quote_1",
                                name="get_realtime_quote",
                                arguments={"stock_code": requested_code},
                            ),
                        ],
                        usage={"total_tokens": 10},
                        provider="openai",
                    ),
                    LLMResponse(
                        content="Blocked indicator token.",
                        tool_calls=[],
                        usage={"total_tokens": 10},
                        provider="openai",
                    ),
                ]
                scope = resolve_stock_scope(message, {"stock_code": "600519"}).stock_scope

                self.assertEqual(scope.allowed_stock_codes, {"600519"})
                self.assertNotIn(requested_code, scope.allowed_stock_codes)
                result = run_agent_loop(
                    messages=[
                        {"role": "system", "content": "system"},
                        {"role": "user", "content": message},
                    ],
                    tool_registry=registry,
                    llm_adapter=adapter,
                    max_steps=3,
                    stock_scope=scope,
                )

                self.assertTrue(result.success)
                self.assertEqual(executed_calls, [])
                self.assertTrue(result.tool_calls_log[0]["guarded"])
                self.assertEqual(result.tool_calls_log[0]["requested_stock_code"], requested_code)
                tool_messages = [msg for msg in result.messages if msg.get("role") == "tool"]
                self.assertEqual(len(tool_messages), 1)
                self.assertIn("stock_scope_violation", tool_messages[0]["content"])

    def test_run_agent_loop_replays_reasoning_and_provider_specific_fields_on_followup_call(self):
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Checking.",
                tool_calls=[
                    ToolCall(
                        id="call_reason",
                        name="echo",
                        arguments={"message": "hello"},
                        thought_signature="sig-1",
                        provider_specific_fields={"thought_signature": "sig-1", "extra": "keep"},
                    )
                ],
                reasoning_content="deepseek reasoning",
                usage={"total_tokens": 10},
                provider="deepseek",
                model="deepseek/deepseek-chat",
            ),
            LLMResponse(
                content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
                tool_calls=[],
                usage={"total_tokens": 20},
                provider="deepseek",
                model="deepseek/deepseek-chat",
            ),
        ]

        result = run_agent_loop(
            messages=[{"role": "user", "content": "Analyze"}],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=2,
        )

        self.assertTrue(result.success)
        followup_messages = adapter.call_with_tools.call_args_list[1].args[0]
        assistant_msg = followup_messages[-2]
        tool_msg = followup_messages[-1]
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertEqual(assistant_msg["reasoning_content"], "deepseek reasoning")
        self.assertEqual(assistant_msg["_trace_provider"], "deepseek")
        self.assertEqual(assistant_msg["_trace_model"], "deepseek/deepseek-chat")
        self.assertEqual(
            assistant_msg["tool_calls"][0]["provider_specific_fields"],
            {"thought_signature": "sig-1", "extra": "keep"},
        )
        self.assertEqual(assistant_msg["tool_calls"][0]["thought_signature"], "sig-1")
        self.assertEqual(tool_msg["role"], "tool")
        self.assertEqual(tool_msg["tool_call_id"], "call_reason")

    def test_chat_persists_single_provider_trace_and_reinjects_without_duplication(self):
        DatabaseManager.reset_instance()
        Config.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        adapter._config = SimpleNamespace(
            agent_context_compression_enabled=False,
            agent_context_compression_profile="balanced",
            agent_context_compression_trigger_tokens=999999,
            agent_context_protected_turns=1,
            llm_model_list=[],
            agent_litellm_model="deepseek/deepseek-chat",
            litellm_model="deepseek/deepseek-chat",
            litellm_fallback_models=[],
        )
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Checking.",
                tool_calls=[ToolCall(id="call_1", name="echo", arguments={"message": "first"})],
                reasoning_content="r1",
                usage={"total_tokens": 10},
                provider="deepseek",
                model="deepseek/deepseek-chat",
            ),
            LLMResponse(
                content="first final",
                tool_calls=[],
                usage={"total_tokens": 5},
                provider="deepseek",
                model="deepseek/deepseek-chat",
            ),
            LLMResponse(
                content="second final",
                tool_calls=[],
                usage={"total_tokens": 5},
                provider="deepseek",
                model="deepseek/deepseek-chat",
            ),
        ]

        executor = AgentExecutor(registry, adapter, max_steps=3)

        with patch(
            "src.application.agent.provider_trace._get_default_db_factory",
            return_value=lambda: db,
        ), patch(
            "src.application.agent.conversation._conversation_port",
            ConversationRepository(db),
        ), patch(
            "src.application.agent.chat_context._chat_context_port",
            ConversationRepository(db),
        ):
            first = executor.chat("first question", "executor-trace")
            second = executor.chat("second question", "executor-trace")

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(len(db.get_agent_provider_turns("executor-trace")), 1)
        second_request_messages = adapter.call_with_tools.call_args_list[2].args[0]
        ordered_roles = [msg["role"] for msg in second_request_messages[-5:]]
        self.assertEqual(ordered_roles, ["user", "assistant", "tool", "assistant", "user"])
        self.assertEqual(second_request_messages[-4]["reasoning_content"], "r1")
        self.assertEqual(second_request_messages[-3]["tool_call_id"], "call_1")
        self.assertEqual(second_request_messages[-2]["content"], "first final")
        self.assertEqual(second_request_messages[-1]["content"], "second question")

        DatabaseManager.reset_instance()
        Config.reset_instance()

    def test_max_steps_exceeded(self):
        """Agent keeps calling tools until max_steps is hit."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()

        # Always return tool calls, never final text
        tool_response = LLMResponse(
            content="Still working.",
            tool_calls=[
                ToolCall(id="c1", name="echo", arguments={"message": "loop"}),
            ],
            usage={"total_tokens": 20},
            provider="openai",
        )
        adapter.call_with_tools.return_value = tool_response

        executor = AgentExecutor(registry, adapter, max_steps=3)
        result = executor.run("Analyze loop")

        self.assertFalse(result.success)
        self.assertIn("max steps", result.error.lower())
        self.assertEqual(result.total_steps, 3)

    def test_model_trace_deduplicates_and_keeps_order(self):
        """Model trace should keep call order and de-duplicate repeated models."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()

        step1 = LLMResponse(
            content="first tool call",
            tool_calls=[ToolCall(id="m1", name="echo", arguments={"message": "a"})],
            usage={"total_tokens": 10},
            provider="gemini",
            model="gemini/gemini-2.0-flash",
        )
        step2 = LLMResponse(
            content="second tool call",
            tool_calls=[ToolCall(id="m2", name="echo", arguments={"message": "b"})],
            usage={"total_tokens": 10},
            provider="gemini",
            model="gemini/gemini-2.0-flash",
        )
        step3 = LLMResponse(
            content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
            tool_calls=[],
            usage={"total_tokens": 10},
            provider="openai",
            model="openai/gpt-4o-mini",
        )
        adapter.call_with_tools.side_effect = [step1, step2, step3]

        executor = AgentExecutor(registry, adapter, max_steps=5)
        result = executor.run("Analyze 600519")

        self.assertTrue(result.success)
        self.assertEqual(result.model, "gemini/gemini-2.0-flash, openai/gpt-4o-mini")
