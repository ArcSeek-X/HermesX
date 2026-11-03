"""Tests for agent executor tools."""

from tests.application.agent._agent_executor_support import (
    AgentExecutor,
    LLMResponse,
    SAMPLE_DASHBOARD,
    StockScope,
    ToolCall,
    ToolDefinition,
    ToolParameter,
    ToolRegistry,
    _TestAgentExecutorFixture,
    _TestSerializeToolResultFixture,
    _make_mock_adapter,
    _make_registry_with_echo,
    _make_stock_registry,
    dataclass,
    json,
    run_agent_loop,
    serialize_tool_result,
    time,
    unittest,
)


class TestAgentExecutor(_TestAgentExecutorFixture, unittest.TestCase):
    def test_unsupported_tool_calling_response_is_not_treated_as_agent_success(self):
        executed_calls = []
        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="echo",
                description="Echoes back the input",
                parameters=[
                    ToolParameter(name="message", type="string", description="Message to echo"),
                ],
                handler=lambda message: executed_calls.append(("echo", message)) or {"echo": message},
            )
        )
        adapter = _make_mock_adapter()
        adapter.call_with_tools.return_value = LLMResponse(
            content="unsupported_tool_calling: local CLI generation backend does not support tools",
            provider="error",
            model="error",
            tool_calls=[],
            usage={},
        )

        result = run_agent_loop(
            messages=[{"role": "user", "content": "请查行情"}],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=2,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.content, "")
        self.assertIn("unsupported_tool_calling", result.error or "")
        self.assertEqual(result.tool_calls_log, [])
        self.assertEqual(executed_calls, [])

    def test_run_agent_loop_blocks_conflicting_stock_scoped_tool_and_keeps_tool_result(self):
        executed_calls = []
        registry = _make_stock_registry(executed_calls)
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Need quote.",
                tool_calls=[
                    ToolCall(id="quote_1", name="get_realtime_quote", arguments={"stock_code": "TTM"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content="I will stay on the current stock.",
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]

        messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "如果不考虑 TTM 呢"},
        ]
        result = run_agent_loop(
            messages=messages,
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            stock_scope=StockScope(expected_stock_code="600519", allowed_stock_codes={"600519"}),
        )

        self.assertTrue(result.success)
        self.assertEqual(executed_calls, [])
        self.assertEqual(len(result.tool_calls_log), 1)
        log_entry = result.tool_calls_log[0]
        self.assertFalse(log_entry["success"])
        self.assertTrue(log_entry["guarded"])
        self.assertEqual(log_entry["expected_stock_code"], "600519")
        self.assertEqual(log_entry["requested_stock_code"], "TTM")
        tool_messages = [msg for msg in result.messages if msg.get("role") == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertEqual(tool_messages[0]["tool_call_id"], "quote_1")
        self.assertIn("stock_scope_violation", tool_messages[0]["content"])

    def test_run_agent_loop_rejects_namespaced_tool_name_without_executing_handler(self):
        executed_calls = []
        registry = _make_stock_registry(executed_calls)
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Need news.",
                tool_calls=[
                    ToolCall(
                        id="news_1",
                        name="default_api:search_stock_news",
                        arguments={"stock_code": "AAPL", "stock_name": "贵州茅台"},
                    ),
                ],
                usage={"total_tokens": 10},
                provider="gemini",
            ),
            LLMResponse(
                content="Blocked wrong code.",
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="gemini",
            ),
        ]

        result = run_agent_loop(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "如果不考虑 AAPL 呢"},
            ],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            stock_scope=StockScope(expected_stock_code="600519", allowed_stock_codes={"600519"}),
        )

        self.assertTrue(result.success)
        self.assertEqual(executed_calls, [])
        self.assertFalse(result.tool_calls_log[0]["success"])
        self.assertNotIn("guarded", result.tool_calls_log[0])
        self.assertEqual(result.tool_calls_log[0]["tool"], "default_api:search_stock_news")
        tool_messages = [msg for msg in result.messages if msg.get("role") == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertIn("not found in registry", tool_messages[0]["content"])

    def test_parallel_tool_batch_guards_only_conflicting_stock_calls(self):
        executed_calls = []
        registry = _make_stock_registry(executed_calls)
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Need mixed tools.",
                tool_calls=[
                    ToolCall(id="quote_ok", name="get_realtime_quote", arguments={"stock_code": "600519"}),
                    ToolCall(id="quote_bad", name="get_realtime_quote", arguments={"stock_code": "AAPL"}),
                    ToolCall(id="echo_1", name="echo", arguments={"message": "not stock scoped"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content="Done.",
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
        self.assertIn(("quote", "600519"), executed_calls)
        self.assertIn(("echo", "not stock scoped"), executed_calls)
        self.assertNotIn(("quote", "AAPL"), executed_calls)
        guarded = [entry for entry in result.tool_calls_log if entry.get("guarded")]
        self.assertEqual(len(guarded), 1)
        self.assertEqual(guarded[0]["requested_stock_code"], "AAPL")

    def test_tool_call_then_text(self):
        """Agent calls a tool, gets result, then returns final answer."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()

        # Step 1: LLM requests tool call
        step1_response = LLMResponse(
            content="Let me check the data.",
            tool_calls=[
                ToolCall(id="call_1", name="echo", arguments={"message": "hello"}),
            ],
            usage={"total_tokens": 50},
            provider="gemini",
        )
        # Step 2: LLM returns final text
        step2_response = LLMResponse(
            content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
            tool_calls=[],
            usage={"total_tokens": 80},
            provider="gemini",
        )
        adapter.call_with_tools.side_effect = [step1_response, step2_response]

        executor = AgentExecutor(registry, adapter, max_steps=5)
        result = executor.run("Analyze 600519")

        self.assertTrue(result.success)
        self.assertEqual(result.total_steps, 2)
        self.assertEqual(result.total_tokens, 130)
        self.assertEqual(len(result.tool_calls_log), 1)
        self.assertEqual(result.tool_calls_log[0]["tool"], "echo")
        self.assertTrue(result.tool_calls_log[0]["success"])

    def test_multiple_tool_calls_in_one_step(self):
        """Agent requests multiple tool calls in a single response."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()

        step1 = LLMResponse(
            content="Gathering data.",
            tool_calls=[
                ToolCall(id="c1", name="echo", arguments={"message": "a"}),
                ToolCall(id="c2", name="echo", arguments={"message": "b"}),
            ],
            usage={"total_tokens": 40},
            provider="openai",
        )
        step2 = LLMResponse(
            content=json.dumps(SAMPLE_DASHBOARD),
            tool_calls=[],
            usage={"total_tokens": 60},
            provider="openai",
        )
        adapter.call_with_tools.side_effect = [step1, step2]

        executor = AgentExecutor(registry, adapter, max_steps=5)
        result = executor.run("Analyze 600519")

        self.assertTrue(result.success)
        self.assertEqual(len(result.tool_calls_log), 2)

    def test_tool_execution_error(self):
        """Tool raises exception — should be logged and error sent to LLM."""
        def _always_fail():
            raise RuntimeError("db down")

        registry = ToolRegistry()
        tool = ToolDefinition(
            name="failing_tool",
            description="Always fails",
            parameters=[],
            handler=_always_fail,
        )
        registry.register(tool)
        adapter = _make_mock_adapter()

        step1 = LLMResponse(
            content="",
            tool_calls=[
                ToolCall(id="f1", name="failing_tool", arguments={}),
            ],
            usage={"total_tokens": 30},
            provider="openai",
        )
        step2 = LLMResponse(
            content=json.dumps(SAMPLE_DASHBOARD),
            tool_calls=[],
            usage={"total_tokens": 50},
            provider="openai",
        )
        adapter.call_with_tools.side_effect = [step1, step2]

        executor = AgentExecutor(registry, adapter, max_steps=5)
        result = executor.run("Test error handling")

        # Should still succeed overall (agent handles tool errors gracefully)
        self.assertTrue(result.success)
        # The failing tool call should be logged as failure
        self.assertEqual(len(result.tool_calls_log), 1)
        self.assertFalse(result.tool_calls_log[0]["success"])

    def test_unknown_tool_called(self):
        """LLM requests a tool not in the registry — should handle gracefully."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()

        step1 = LLMResponse(
            content="",
            tool_calls=[
                ToolCall(id="u1", name="nonexistent_tool", arguments={}),
            ],
            usage={"total_tokens": 20},
            provider="openai",
        )
        step2 = LLMResponse(
            content=json.dumps(SAMPLE_DASHBOARD),
            tool_calls=[],
            usage={"total_tokens": 50},
            provider="openai",
        )
        adapter.call_with_tools.side_effect = [step1, step2]

        executor = AgentExecutor(registry, adapter, max_steps=5)
        result = executor.run("Test unknown tool")

        self.assertTrue(result.success)
        self.assertEqual(len(result.tool_calls_log), 1)
        self.assertFalse(result.tool_calls_log[0]["success"])
        self.assertFalse(result.tool_calls_log[0]["cached"])

    def test_non_retriable_tool_failure_is_cached_across_hk_variants(self):
        """Equivalent HK code variants should not re-execute a non-retriable failing tool."""
        calls = []

        def _quote(stock_code):
            calls.append(stock_code)
            return {
                "error": f"No realtime quote available for {stock_code}",
                "retriable": False,
                "note": "Skip retry",
            }

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="get_realtime_quote",
                description="Get realtime quote",
                parameters=[
                    ToolParameter(name="stock_code", type="string", description="Stock code"),
                ],
                handler=_quote,
            )
        )
        adapter = _make_mock_adapter()

        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(id="q1", name="get_realtime_quote", arguments={"stock_code": "hk01810"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(id="q2", name="get_realtime_quote", arguments={"stock_code": "1810.HK"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]

        executor = AgentExecutor(registry, adapter, max_steps=5)
        result = executor.run("Analyze HK01810")

        self.assertTrue(result.success)
        self.assertEqual(calls, ["hk01810"])
        self.assertEqual(len(result.tool_calls_log), 2)
        self.assertFalse(result.tool_calls_log[0]["cached"])
        self.assertTrue(result.tool_calls_log[1]["cached"])

    def test_parallel_tool_timeout_marks_only_pending_calls(self):
        """Parallel tool batches should emit timeout errors for unfinished tools."""
        registry = ToolRegistry()

        def _maybe_slow_echo(message):
            if message == "slow":
                time.sleep(0.05)
            return {"echo": message}

        registry.register(
            ToolDefinition(
                name="echo",
                description="Echoes back the input",
                parameters=[
                    ToolParameter(name="message", type="string", description="Message to echo"),
                ],
                handler=_maybe_slow_echo,
            )
        )
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Gathering data.",
                tool_calls=[
                    ToolCall(id="fast", name="echo", arguments={"message": "fast"}),
                    ToolCall(id="slow", name="echo", arguments={"message": "slow"}),
                ],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]

        result = run_agent_loop(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Analyze"},
            ],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            tool_call_timeout_seconds=0.01,
        )

        self.assertTrue(result.success)
        self.assertEqual(len(result.tool_calls_log), 2)
        timeout_logs = [log for log in result.tool_calls_log if log.get("timeout")]
        self.assertEqual(len(timeout_logs), 1)
        self.assertEqual(timeout_logs[0]["arguments"]["message"], "slow")

    def test_single_tool_timeout_marks_tool_failed(self):
        """Single tool calls should also respect the configured tool timeout."""
        registry = ToolRegistry()

        def _slow_echo(message):
            time.sleep(0.05)
            return {"echo": message}

        registry.register(
            ToolDefinition(
                name="echo",
                description="Echoes back the input",
                parameters=[
                    ToolParameter(name="message", type="string", description="Message to echo"),
                ],
                handler=_slow_echo,
            )
        )
        adapter = _make_mock_adapter()
        adapter.call_with_tools.side_effect = [
            LLMResponse(
                content="Gathering data.",
                tool_calls=[ToolCall(id="slow", name="echo", arguments={"message": "slow"})],
                usage={"total_tokens": 10},
                provider="openai",
            ),
            LLMResponse(
                content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            ),
        ]

        result = run_agent_loop(
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Analyze"},
            ],
            tool_registry=registry,
            llm_adapter=adapter,
            max_steps=3,
            tool_call_timeout_seconds=0.01,
        )

        self.assertTrue(result.success)
        self.assertEqual(len(result.tool_calls_log), 1)
        self.assertTrue(result.tool_calls_log[0].get("timeout"))
        self.assertEqual(result.tool_calls_log[0]["arguments"]["message"], "slow")


class TestSerializeToolResult(_TestSerializeToolResultFixture, unittest.TestCase):
    def test_serialize_none(self):
        result = serialize_tool_result(None)
        self.assertEqual(json.loads(result), {"result": None})

    def test_serialize_string(self):
        result = serialize_tool_result("hello")
        self.assertEqual(result, "hello")

    def test_serialize_dict(self):
        d = {"key": "value", "num": 42}
        result = serialize_tool_result(d)
        self.assertEqual(json.loads(result), d)

    def test_serialize_list(self):
        lst = [1, 2, 3]
        result = serialize_tool_result(lst)
        self.assertEqual(json.loads(result), lst)

    def test_serialize_dataclass(self):
        @dataclass
        class Sample:
            name: str = "test"
            value: int = 42

        result = serialize_tool_result(Sample())
        parsed = json.loads(result)
        self.assertEqual(parsed["name"], "test")
        self.assertEqual(parsed["value"], 42)
