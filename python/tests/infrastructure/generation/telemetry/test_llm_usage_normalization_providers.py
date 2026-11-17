"""Tests for llm usage normalization providers."""

from tests.infrastructure.generation.telemetry._llm_usage_support import (
    Usage,
    extract_usage_payload,
    has_provider_usage_payload,
    json,
    normalize_litellm_usage,
    unittest,
)


class TestLLMUsageNormalizer(unittest.TestCase):
    def test_openai_cached_tokens(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 2000,
                "completion_tokens": 100,
                "total_tokens": 2100,
                "prompt_tokens_details": {"cached_tokens": 500},
            },
            model="openai/gpt-4o",
        )

        self.assertEqual(usage["prompt_tokens"], 2000)
        self.assertEqual(usage["normalized_cache_read_tokens"], 500)
        self.assertEqual(usage["provider_reported_cached_tokens"], 500)
        self.assertEqual(usage["provider_min_cache_tokens"], 1024)
        self.assertEqual(usage["cache_eligibility"], "eligible")
        self.assertEqual(usage["cache_observation"], "partial_hit")
        self.assertEqual(usage["normalized_cache_hit_ratio"], 0.25)

    def test_openai_impossible_cache_counts_are_marked_invalid(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 2000,
                "completion_tokens": 10,
                "total_tokens": 2010,
                "prompt_tokens_details": {"cached_tokens": 5000},
            },
            model="openai/gpt-4o",
        )

        self.assertEqual(usage["provider_reported_prompt_tokens"], 2000)
        self.assertEqual(usage["provider_reported_cached_tokens"], 5000)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_observation"], "invalid_provider_usage")
        self.assertEqual(usage["eligibility_confidence"], "invalid")
        self.assertIsNone(usage["normalized_cache_read_tokens"])
        self.assertIsNone(usage["normalized_uncached_input_tokens"])
        self.assertIsNone(usage["normalized_cache_hit_ratio"])

    def test_openai_below_threshold_does_not_fake_zero_hit(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
                "prompt_tokens_details": {"cached_tokens": 0},
            },
            model="openai/gpt-4o",
        )

        self.assertEqual(usage["cache_eligibility"], "below_threshold")
        self.assertIsNone(usage["normalized_cache_eligible_input_tokens"])
        self.assertEqual(usage["cache_observation"], "unknown")

    def test_openai_compatible_model_without_cache_field_keeps_cache_unknown(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1500,
                "completion_tokens": 1,
                "total_tokens": 1501,
            },
            model="openai/Qwen/Qwen3-235B-A22B-Thinking-2507",
            provider="openai",
        )

        self.assertEqual(usage["prompt_tokens"], 1500)
        self.assertEqual(usage["cache_capability"], "unknown")
        self.assertEqual(usage["cache_eligibility"], "unknown")
        self.assertEqual(usage["cache_observation"], "unknown")
        self.assertIsNone(usage["provider_min_cache_tokens"])
        self.assertIsNone(usage["normalized_cache_eligible_input_tokens"])
        self.assertIsNone(usage["normalized_cache_read_tokens"])

    def test_openai_compatible_cached_tokens_do_not_use_native_openai_threshold(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1500,
                "completion_tokens": 1,
                "total_tokens": 1501,
                "prompt_tokens_details": {"cached_tokens": 1500},
            },
            model="openai/Qwen/Qwen3-235B-A22B-Thinking-2507",
            provider="openai",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 1500)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_eligibility"], "eligible")
        self.assertEqual(usage["cache_observation"], "full_hit")
        self.assertIsNone(usage["provider_min_cache_tokens"])
        self.assertEqual(usage["normalized_cache_eligible_input_tokens"], 1500)

    def test_glm_cached_tokens_use_openai_shape(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1200,
                "completion_tokens": 80,
                "total_tokens": 1280,
                "prompt_tokens_details": {"cached_tokens": 1200},
            },
            model="zhipu/glm-4.5",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 1200)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_observation"], "full_hit")

    def test_zhipu_provider_alias_uses_glm_cache_shape(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1200,
                "completion_tokens": 80,
                "total_tokens": 1280,
                "prompt_tokens_details": {"cached_tokens": 1200},
            },
            model="zhipu/glm-4.5",
            provider="zhipu",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 1200)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_observation"], "full_hit")
        self.assertIsNone(usage["provider_min_cache_tokens"])

    def test_qwen_wrapped_openai_model_uses_openai_compatible_cache_shape(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1500,
                "completion_tokens": 200,
                "total_tokens": 1700,
                "prompt_tokens_details": {"cached_tokens": 1200},
            },
            model="openai/qwen-max",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 1200)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_observation"], "partial_hit")

    def test_kimi_wrapped_openai_model_uses_top_level_cached_tokens(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1500,
                "completion_tokens": 200,
                "total_tokens": 1700,
                "cached_tokens": 300,
            },
            model="openai/kimi-k2",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 300)
        self.assertEqual(usage["cache_capability"], "supported")

    def test_openrouter_cache_read_write_tokens(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1500,
                "completion_tokens": 200,
                "total_tokens": 1700,
                "cache_read_tokens": 300,
                "cache_write_tokens": 100,
            },
            model="openai/~anthropic/claude-sonnet",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 300)
        self.assertEqual(usage["normalized_cache_write_tokens"], 100)
        self.assertEqual(usage["cache_capability"], "supported")

    def test_anthropic_official_cache_breakdown_sums_total_input(self):
        usage = normalize_litellm_usage(
            {
                "input_tokens": 100,
                "output_tokens": 30,
                "cache_read_input_tokens": 10,
                "cache_creation_input_tokens": 20,
            },
            model="anthropic/claude-3-5-sonnet",
        )

        # Anthropic defines total input as input + cache read + cache creation tokens.
        self.assertEqual(usage["prompt_tokens"], 130)
        self.assertEqual(usage["completion_tokens"], 30)
        self.assertEqual(usage["total_tokens"], 160)
        self.assertEqual(usage["normalized_cache_read_tokens"], 10)
        self.assertEqual(usage["normalized_cache_write_tokens"], 20)
        self.assertEqual(usage["normalized_uncached_input_tokens"], 100)
        self.assertEqual(usage["cache_observation"], "read_and_write")

    def test_anthropic_litellm_normalized_usage_keeps_prompt_tokens_without_input_tokens(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
            model="anthropic/claude-3-5-sonnet",
        )

        self.assertEqual(usage["prompt_tokens"], 100)
        self.assertEqual(usage["completion_tokens"], 20)
        self.assertEqual(usage["total_tokens"], 120)
        self.assertEqual(usage["normalized_prompt_tokens"], 100)
        self.assertEqual(usage["normalized_cache_read_tokens"], 0)
        self.assertEqual(usage["normalized_cache_write_tokens"], 0)
        self.assertEqual(usage["normalized_uncached_input_tokens"], 100)
        self.assertEqual(usage["cache_observation"], "zero_hit")

    def test_anthropic_litellm_normalized_usage_derives_uncached_tokens_without_input_tokens(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 115,
                "completion_tokens": 20,
                "total_tokens": 135,
                "cache_read_input_tokens": 10,
                "cache_creation_input_tokens": 5,
            },
            model="anthropic/claude-3-5-sonnet",
        )

        self.assertEqual(usage["prompt_tokens"], 115)
        self.assertEqual(usage["completion_tokens"], 20)
        self.assertEqual(usage["total_tokens"], 135)
        self.assertEqual(usage["normalized_prompt_tokens"], 115)
        self.assertEqual(usage["normalized_cache_read_tokens"], 10)
        self.assertEqual(usage["normalized_cache_write_tokens"], 5)
        self.assertEqual(usage["normalized_uncached_input_tokens"], 100)
        self.assertEqual(usage["cache_observation"], "read_and_write")

    def test_gemini_usage_metadata(self):
        payload = {
            "usage_metadata": {
                "prompt_token_count": 1000,
                "candidates_token_count": 50,
                "total_token_count": 1050,
                "cached_content_token_count": 32,
            }
        }

        usage = normalize_litellm_usage(
            extract_usage_payload(payload),
            model="gemini/gemini-2.5-flash",
        )

        self.assertEqual(usage["prompt_tokens"], 1000)
        self.assertEqual(usage["completion_tokens"], 50)
        self.assertEqual(usage["total_tokens"], 1050)
        self.assertEqual(usage["normalized_cache_read_tokens"], 32)
        self.assertEqual(usage["cache_observation"], "partial_hit")

    def test_gemini_litellm_usage_cache_read_input_tokens(self):
        usage = normalize_litellm_usage(
            Usage(
                prompt_tokens=1000,
                completion_tokens=50,
                total_tokens=1050,
                cache_read_input_tokens=32,
            ),
            model="gemini/gemini-2.5-flash",
        )

        self.assertEqual(usage["prompt_tokens"], 1000)
        self.assertEqual(usage["completion_tokens"], 50)
        self.assertEqual(usage["total_tokens"], 1050)
        self.assertEqual(usage["normalized_cache_read_tokens"], 32)
        self.assertEqual(usage["provider_reported_cached_tokens"], 32)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_observation"], "partial_hit")
        raw = json.loads(usage["provider_usage_json"])
        self.assertTrue(
            raw.get("cache_read_input_tokens") == 32
            or raw.get("prompt_tokens_details", {}).get("cached_tokens") == 32
        )

    def test_vertex_ai_gemini_usage_uses_gemini_cache_shape(self):
        usage = normalize_litellm_usage(
            Usage(
                prompt_tokens=1000,
                completion_tokens=50,
                total_tokens=1050,
                cache_read_input_tokens=32,
            ),
            model="vertex_ai/gemini-2.5-flash",
            provider="vertex_ai",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 32)
        self.assertEqual(usage["provider_reported_cached_tokens"], 32)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_observation"], "partial_hit")

    def test_gemini_litellm_usage_zero_cache_hit(self):
        usage = normalize_litellm_usage(
            Usage(
                prompt_tokens=1000,
                completion_tokens=50,
                total_tokens=1050,
                cache_read_input_tokens=0,
            ),
            model="gemini/gemini-2.5-flash",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 0)
        self.assertEqual(usage["provider_reported_cached_tokens"], 0)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_observation"], "zero_hit")

    def test_gemini_prompt_tokens_details_cached_tokens_fallback(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1000,
                "completion_tokens": 50,
                "total_tokens": 1050,
                "prompt_tokens_details": {"cached_tokens": 32},
            },
            model="gemini/gemini-2.5-flash",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 32)
        self.assertEqual(usage["provider_reported_cached_tokens"], 32)
        self.assertEqual(usage["cache_capability"], "supported")
        self.assertEqual(usage["cache_observation"], "partial_hit")

    def test_deepseek_hit_miss_tokens(self):
        usage = normalize_litellm_usage(
            {
                "completion_tokens": 10,
                "prompt_cache_hit_tokens": 40,
                "prompt_cache_miss_tokens": 60,
            },
            model="deepseek/deepseek-chat",
        )

        self.assertEqual(usage["prompt_tokens"], 100)
        self.assertEqual(usage["total_tokens"], 110)
        self.assertEqual(usage["normalized_cache_read_tokens"], 40)
        self.assertEqual(usage["normalized_cache_miss_tokens"], 60)
        self.assertEqual(usage["normalized_uncached_input_tokens"], 60)

    def test_openai_deepseek_hit_miss_tokens_use_payload_shape(self):
        usage = normalize_litellm_usage(
            {
                "completion_tokens": 10,
                "prompt_cache_hit_tokens": 40,
                "prompt_cache_miss_tokens": 60,
            },
            model="openai/deepseek-chat",
        )

        self.assertEqual(usage["prompt_tokens"], 100)
        self.assertEqual(usage["total_tokens"], 110)
        self.assertEqual(usage["normalized_cache_read_tokens"], 40)
        self.assertEqual(usage["normalized_cache_miss_tokens"], 60)
        self.assertEqual(usage["normalized_uncached_input_tokens"], 60)
        self.assertEqual(usage["cache_capability"], "supported")

    def test_deepseek_hit_miss_does_not_override_provider_prompt_tokens(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 50,
                "completion_tokens": 10,
                "total_tokens": 60,
                "prompt_cache_hit_tokens": 40,
                "prompt_cache_miss_tokens": 60,
            },
            model="openai/deepseek-chat",
        )

        self.assertEqual(usage["cache_observation"], "invalid_provider_usage")
        self.assertEqual(usage["eligibility_confidence"], "invalid")
        self.assertEqual(usage["prompt_tokens"], 0)
        self.assertEqual(usage["completion_tokens"], 0)
        self.assertEqual(usage["total_tokens"], 0)
        self.assertEqual(usage["provider_reported_prompt_tokens"], 50)
        self.assertEqual(usage["provider_reported_cached_tokens"], 40)

    def test_stepfun_top_level_cached_tokens(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 900,
                "completion_tokens": 100,
                "total_tokens": 1000,
                "cached_tokens": 300,
            },
            model="stepfun/step-2",
        )

        self.assertEqual(usage["normalized_cache_read_tokens"], 300)
        self.assertEqual(usage["cache_capability"], "supported")

    def test_unknown_provider_keeps_cache_unknown(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1000,
                "completion_tokens": 100,
                "total_tokens": 1100,
            },
            model="gateway/custom-model",
            provider="gateway",
        )

        self.assertEqual(usage["prompt_tokens"], 1000)
        self.assertIsNone(usage["normalized_cache_read_tokens"])
        self.assertIsNone(usage["normalized_cache_miss_tokens"])
        self.assertEqual(usage["cache_capability"], "unknown")
        self.assertEqual(usage["cache_observation"], "unknown")

    def test_has_provider_usage_payload_detects_real_usage_signals(self):
        self.assertTrue(has_provider_usage_payload({"total_tokens": 5}))
        self.assertTrue(has_provider_usage_payload({"normalized_total_tokens": 5}))
        self.assertTrue(has_provider_usage_payload({"provider_usage_json": '{"prompt_tokens":1}'}))
        self.assertTrue(has_provider_usage_payload({"normalized_cache_read_tokens": 5}))
        self.assertTrue(has_provider_usage_payload({"normalized_cache_write_tokens": 5}))
        self.assertTrue(has_provider_usage_payload({"normalized_cache_miss_tokens": 5}))
        self.assertTrue(has_provider_usage_payload({"provider_reported_cached_tokens": 5}))
        self.assertTrue(
            has_provider_usage_payload(
                {"provider_usage_json": '{"prompt_tokens_details":{"cached_tokens":1}}'}
            )
        )
        self.assertTrue(has_provider_usage_payload({"provider_usage_json": '{"cache_read_input_tokens":1}'}))
        self.assertTrue(has_provider_usage_payload({"provider_usage_json": '{"prompt_cache_hit_tokens":1}'}))
        self.assertTrue(
            has_provider_usage_payload(
                {"provider_usage_json": '{"prompt_tokens":1000,"cache_read_input_tokens":0}'}
            )
        )
        self.assertFalse(has_provider_usage_payload({"prompt_tokens": True}))
        self.assertFalse(has_provider_usage_payload({"prompt_tokens": -1}))
        self.assertFalse(has_provider_usage_payload({"provider_usage_json": '{"prompt_tokens":-1}'}))

    def test_has_provider_usage_payload_ignores_empty_hmac_and_cache_metadata(self):
        self.assertFalse(has_provider_usage_payload(None))
        self.assertFalse(has_provider_usage_payload({}))
        self.assertFalse(
            has_provider_usage_payload(
                {
                    "messages_hmac": "a" * 64,
                    "system_message_hmac": None,
                    "user_message_hmac": "b" * 64,
                    "hmac_key_version": "local-v1",
                    "hmac_domain": "prompt_message",
                    "hash_scope": "deployment",
                }
            )
        )
        for provider_usage_json in (
            '{"estimated_prefix_tokens":123}',
            '{"tokenizer_name":"cl100k_base","tokenizer_version":"v1"}',
            '{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}',
            '{"cache_read_input_tokens":0}',
            '{"prompt_tokens_details":{"cached_tokens":0}}',
            '{"_truncated":true,"_original_size_bytes":8192}',
            '{not valid json',
            '["prompt_tokens",1]',
            '"prompt_tokens"',
            "1",
        ):
            self.assertFalse(has_provider_usage_payload({"provider_usage_json": provider_usage_json}))
        self.assertFalse(
            has_provider_usage_payload(
                {
                    "cache_observation": "no_usage",
                    "cache_capability": "unknown",
                    "normalized_cache_read_tokens": None,
                }
            )
        )

    def test_has_provider_usage_payload_ignores_normalized_metadata_only_usage(self):
        usage = normalize_litellm_usage(
            {"estimated_prefix_tokens": 123},
            model="openai/gpt-4o",
        )

        self.assertEqual(json.loads(usage["provider_usage_json"]), {"estimated_prefix_tokens": 123})
        self.assertFalse(has_provider_usage_payload(usage))

    def test_has_provider_usage_payload_ignores_normalized_no_usage_shape(self):
        usage = normalize_litellm_usage(None, model="openai/gpt-4o")

        self.assertEqual(usage["cache_observation"], "no_usage")
        self.assertEqual(usage["total_tokens"], 0)
        self.assertFalse(has_provider_usage_payload(usage))

    def test_provider_usage_json_preserves_allowlisted_usage_cache_shapes(self):
        cases = [
            (
                "openai",
                {
                    "prompt_tokens": 2000,
                    "completion_tokens": 100,
                    "total_tokens": 2100,
                    "prompt_tokens_details": {"cached_tokens": 500},
                },
                "openai/gpt-4o",
                {"prompt_tokens": 2000, "prompt_tokens_details": {"cached_tokens": 500}},
            ),
            (
                "anthropic",
                {
                    "input_tokens": 100,
                    "output_tokens": 30,
                    "cache_read_input_tokens": 10,
                    "cache_creation_input_tokens": 20,
                },
                "anthropic/claude-3-5-sonnet",
                {
                    "input_tokens": 100,
                    "output_tokens": 30,
                    "cache_read_input_tokens": 10,
                    "cache_creation_input_tokens": 20,
                },
            ),
            (
                "gemini",
                {
                    "prompt_token_count": 1000,
                    "candidates_token_count": 50,
                    "total_token_count": 1050,
                    "cached_content_token_count": 32,
                },
                "gemini/gemini-2.5-flash",
                {
                    "prompt_token_count": 1000,
                    "candidates_token_count": 50,
                    "total_token_count": 1050,
                    "cached_content_token_count": 32,
                },
            ),
            (
                "deepseek",
                {
                    "completion_tokens": 10,
                    "prompt_cache_hit_tokens": 40,
                    "prompt_cache_miss_tokens": 60,
                },
                "deepseek/deepseek-chat",
                {
                    "completion_tokens": 10,
                    "prompt_cache_hit_tokens": 40,
                    "prompt_cache_miss_tokens": 60,
                },
            ),
            (
                "stepfun",
                {
                    "prompt_tokens": 900,
                    "completion_tokens": 100,
                    "total_tokens": 1000,
                    "cached_tokens": 300,
                },
                "stepfun/step-2",
                {
                    "prompt_tokens": 900,
                    "completion_tokens": 100,
                    "total_tokens": 1000,
                    "cached_tokens": 300,
                },
            ),
        ]

        for name, payload, model, expected_subset in cases:
            with self.subTest(name=name):
                usage = normalize_litellm_usage(payload, model=model)
                raw = usage["provider_usage_json"]
                self.assertIsNotNone(raw)
                parsed = json.loads(raw)
                for key, expected in expected_subset.items():
                    self.assertEqual(parsed[key], expected)
