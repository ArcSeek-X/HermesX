"""Tests for llm usage security."""

from tests.infrastructure.generation.telemetry._llm_usage_support import (
    LLMUsage,
    Path,
    _TestLLMUsageHMACFixture,
    _TestLegacyMessageStabilityAuditFixture,
    _fresh_db,
    _reset_usage_hmac_secret_cache_for_tests,
    attach_legacy_message_stability_audit,
    build_message_hmacs,
    hashlib,
    json,
    normalize_litellm_usage,
    os,
    patch,
    persist_llm_usage,
    py_hmac,
    tempfile,
    unittest,
)


class TestLLMUsageHMAC(_TestLLMUsageHMACFixture, unittest.TestCase):
    def test_hmac_sha256_is_used_without_raw_prompt_storage(self):
        messages = [
            {"role": "system", "content": "system policy"},
            {"role": "user", "content": "user prompt"},
        ]
        with patch.dict(
            os.environ,
            {
                "LLM_USAGE_HMAC_SECRET": "test-secret",
                "LLM_USAGE_HMAC_KEY_VERSION": "test-v1",
            },
            clear=False,
        ):
            _reset_usage_hmac_secret_cache_for_tests()
            fields = build_message_hmacs(messages, hash_scope="local_debug")

        expected_payload = json.dumps(
            messages,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        expected = py_hmac.new(
            b"test-secret",
            expected_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(fields["messages_hmac"], expected)
        self.assertEqual(len(fields["messages_hmac"]), 64)
        self.assertEqual(fields["hmac_key_version"], "test-v1")
        self.assertEqual(fields["hmac_domain"], "prompt_message")
        self.assertEqual(fields["hash_scope"], "local_debug")
        self.assertNotIn("user prompt", json.dumps(fields))

    def test_hmac_covers_tool_and_provider_wire_fields(self):
        first_messages = [
            {
                "role": "assistant",
                "content": "same",
                "_trace_provider": "anthropic",
                "tool_calls": [
                    {
                        "id": "call_a",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": "{}"},
                        "provider_specific_fields": {"thought_signature": "sig-a"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_a", "content": "same result"},
        ]
        second_messages = [
            {
                "role": "assistant",
                "content": "same",
                "_trace_provider": "anthropic",
                "tool_calls": [
                    {
                        "id": "call_b",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": '{"n":1}'},
                        "provider_specific_fields": {"thought_signature": "sig-b"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_b", "content": "same result"},
        ]
        with patch.dict(os.environ, {"LLM_USAGE_HMAC_SECRET": "tool-secret"}, clear=False):
            first = build_message_hmacs(first_messages)
            first_again = build_message_hmacs(first_messages)
            second = build_message_hmacs(second_messages)

        self.assertEqual(first["messages_hmac"], first_again["messages_hmac"])
        self.assertNotEqual(first["messages_hmac"], second["messages_hmac"])

    def test_hmac_ignores_internal_trace_metadata(self):
        base_messages = [{"role": "assistant", "content": "same"}]
        traced_messages = [
            {
                "role": "assistant",
                "content": "same",
                "_trace_provider": "anthropic",
                "_trace_model": "anthropic/claude-test",
            }
        ]
        with patch.dict(os.environ, {"LLM_USAGE_HMAC_SECRET": "trace-secret"}, clear=False):
            base = build_message_hmacs(base_messages)
            traced = build_message_hmacs(traced_messages)

        self.assertEqual(base["messages_hmac"], traced["messages_hmac"])

    def test_missing_env_uses_generated_local_secret_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "stock_analysis.db"
            secret_path = Path(tmpdir) / ".llm_usage_hmac_secret"
            with patch.dict(os.environ, {"DATABASE_PATH": str(db_path)}, clear=True):
                _reset_usage_hmac_secret_cache_for_tests()
                fields = build_message_hmacs([{"role": "user", "content": "hello"}])

            self.assertTrue(secret_path.exists())
            self.assertEqual(secret_path.stat().st_size, 32)
            self.assertEqual(len(fields["messages_hmac"]), 64)
            self.assertEqual(fields["hmac_key_version"], "local-v1")

    def test_empty_generated_secret_file_is_regenerated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "stock_analysis.db"
            secret_path = Path(tmpdir) / ".llm_usage_hmac_secret"
            secret_path.write_bytes(b"")
            with patch.dict(os.environ, {"DATABASE_PATH": str(db_path)}, clear=True):
                _reset_usage_hmac_secret_cache_for_tests()
                fields = build_message_hmacs([{"role": "user", "content": "hello"}])

            self.assertEqual(secret_path.stat().st_size, 32)
            self.assertEqual(len(fields["messages_hmac"]), 64)
            self.assertEqual(fields["hmac_key_version"], "local-v1")

    def test_key_version_is_part_of_hash_comparability_tuple(self):
        messages = [{"role": "user", "content": "same message"}]
        with patch.dict(
            os.environ,
            {
                "LLM_USAGE_HMAC_SECRET": "same-secret",
                "LLM_USAGE_HMAC_KEY_VERSION": "v1",
            },
            clear=False,
        ):
            first = build_message_hmacs(messages)
        with patch.dict(
            os.environ,
            {
                "LLM_USAGE_HMAC_SECRET": "same-secret",
                "LLM_USAGE_HMAC_KEY_VERSION": "v2",
            },
            clear=False,
        ):
            second = build_message_hmacs(messages)

        self.assertEqual(first["messages_hmac"], second["messages_hmac"])
        self.assertNotEqual(
            (first["hmac_key_version"], first["messages_hmac"]),
            (second["hmac_key_version"], second["messages_hmac"]),
        )


class TestLegacyMessageStabilityAudit(_TestLegacyMessageStabilityAuditFixture, unittest.TestCase):
    def test_attaches_hmac_and_internal_audit_fields_without_raw_marker_values(self):
        usage = attach_legacy_message_stability_audit(
            {},
            self._messages(),
            self._audit_context(),
        )

        self.assertEqual(usage["language"], "zh")
        self.assertEqual(usage["market_group"], "cn")
        self.assertEqual(usage["analysis_mode"], "stock_analysis")
        self.assertEqual(usage["legacy_prompt_mode"], "skill_aware")
        self.assertEqual(len(usage["skill_config_hmac"]), 64)
        self.assertEqual(usage["provider"], "gemini")
        self.assertEqual(usage["transport"], "litellm")
        self.assertEqual(usage["message_count"], 2)
        self.assertGreater(usage["estimated_total_prompt_tokens"], 0)
        self.assertIsNotNone(usage["approx_common_prefix_chars"])
        self.assertIsNotNone(usage["approx_common_prefix_tokens"])
        self.assertEqual(usage["eligibility_confidence"], "estimated")
        self.assertEqual(len(usage["messages_hmac"]), 64)
        self.assertEqual(len(usage["system_message_hmac"]), 64)
        self.assertEqual(len(usage["user_message_hmac"]), 64)

        marker_json = usage["known_dynamic_marker_positions"]
        self.assertIsInstance(marker_json, str)
        markers = json.loads(marker_json)
        self.assertEqual(
            {tuple(marker.keys()) for marker in markers},
            {("marker_name", "message_role", "char_offset")},
        )
        self.assertEqual(markers[0]["marker_name"], "stock_code")
        self.assertEqual(markers[0]["message_role"], "user")
        self.assertIsInstance(markers[0]["char_offset"], int)

        serialized = json.dumps(usage, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("600519", marker_json)
        self.assertNotIn("贵州茅台", marker_json)
        self.assertNotIn("2026-06-19", marker_json)
        self.assertNotIn("IMPORTANT_NEWS_TEXT", marker_json)
        self.assertNotIn("RSI breakout skill raw instructions", serialized)
        self.assertNotIn("Default skill policy raw text", serialized)
        self.assertNotIn("Authorization", serialized)
        self.assertNotIn("Bearer", serialized)

    def test_skill_config_hmac_changes_when_resolved_skill_config_changes(self):
        base_context = self._audit_context()
        changed_context = dict(base_context)
        changed_context["skill_config"] = dict(base_context["skill_config"])
        changed_context["skill_config"]["skill_instructions"] = "Different resolved skill instructions"

        first = attach_legacy_message_stability_audit(
            {},
            self._messages(),
            base_context,
        )
        second = attach_legacy_message_stability_audit(
            {},
            self._messages(),
            changed_context,
        )

        self.assertEqual(first["messages_hmac"], second["messages_hmac"])
        self.assertNotEqual(first["skill_config_hmac"], second["skill_config_hmac"])

    def test_common_prefix_estimate_uses_canonical_render_before_first_marker(self):
        messages = self._messages()
        usage = attach_legacy_message_stability_audit(
            {},
            messages,
            self._audit_context(),
        )
        user_content = messages[1]["content"]
        first_marker_offset = user_content.index("600519")

        self.assertGreater(usage["approx_common_prefix_chars"], first_marker_offset)
        self.assertEqual(
            usage["approx_common_prefix_tokens"],
            (usage["approx_common_prefix_chars"] + 2) // 3,
        )

    def test_empty_preferred_marker_list_does_not_fall_back_to_other_marker_keys(self):
        context = dict(self._audit_context())
        context["known_dynamic_markers"] = []
        context["markers"] = [
            {"marker_name": "stock_code", "message_role": "user", "text": "600519"},
        ]

        usage = attach_legacy_message_stability_audit(
            {},
            self._messages(),
            context,
        )

        self.assertEqual(json.loads(usage["known_dynamic_marker_positions"]), [])
        self.assertIsNone(usage["approx_common_prefix_chars"])
        self.assertIsNone(usage["approx_common_prefix_tokens"])

    def test_preserves_exact_and_invalid_provider_usage_confidence(self):
        messages = self._messages()
        exact = attach_legacy_message_stability_audit(
            normalize_litellm_usage({"prompt_tokens": 9}, model="openai/gpt-4o"),
            messages,
            self._audit_context(),
        )
        invalid = attach_legacy_message_stability_audit(
            normalize_litellm_usage({"prompt_tokens": -1}, model="openai/gpt-4o"),
            messages,
            self._audit_context(),
        )

        self.assertEqual(exact["eligibility_confidence"], "exact")
        self.assertEqual(invalid["eligibility_confidence"], "invalid")

    def test_persisted_marker_positions_remain_json_string(self):
        usage = attach_legacy_message_stability_audit(
            {},
            self._messages(),
            self._audit_context(),
        )
        db = _fresh_db()
        persist_llm_usage(usage, "gemini/gemini-test", call_type="analysis", stock_code="600519")

        with db.session_scope() as session:
            row = session.query(LLMUsage).one()
            persisted = {
                "language": row.language,
                "market_group": row.market_group,
                "analysis_mode": row.analysis_mode,
                "legacy_prompt_mode": row.legacy_prompt_mode,
                "skill_config_hmac": row.skill_config_hmac,
                "provider": row.provider,
                "transport": row.transport,
                "message_count": row.message_count,
                "known_dynamic_marker_positions": row.known_dynamic_marker_positions,
            }

        self.assertEqual(persisted["language"], "zh")
        self.assertEqual(persisted["market_group"], "cn")
        self.assertEqual(persisted["analysis_mode"], "stock_analysis")
        self.assertEqual(persisted["legacy_prompt_mode"], "skill_aware")
        self.assertEqual(len(persisted["skill_config_hmac"]), 64)
        self.assertEqual(persisted["provider"], "gemini")
        self.assertEqual(persisted["transport"], "litellm")
        self.assertEqual(persisted["message_count"], 2)
        self.assertIsInstance(persisted["known_dynamic_marker_positions"], str)
        parsed = json.loads(persisted["known_dynamic_marker_positions"])
        self.assertEqual(parsed[0]["marker_name"], "stock_code")
        self.assertNotIn("600519", persisted["known_dynamic_marker_positions"])

    def test_does_not_emit_block_level_p05b_fields(self):
        usage = attach_legacy_message_stability_audit(
            {},
            self._messages(),
            self._audit_context(),
        )

        for field in (
            "block_id",
            "stability_class",
            "static_prefix_hash",
            "dynamic_context_hash",
        ):
            self.assertNotIn(field, usage)
