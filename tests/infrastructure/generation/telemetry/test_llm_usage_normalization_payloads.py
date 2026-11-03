"""Tests for llm usage normalization payloads."""

from tests.infrastructure.generation.telemetry._llm_usage_support import (
    has_provider_usage_payload,
    json,
    normalize_litellm_usage,
    should_persist_usage_telemetry,
    unittest,
)


class TestLLMUsageNormalizer(unittest.TestCase):
    def test_invalid_token_counts_are_marked_invalid(self):
        cases = [
            {"prompt_tokens": True, "completion_tokens": 2, "total_tokens": 3},
            {"prompt_tokens": -1, "completion_tokens": 2, "total_tokens": 1},
            {"prompt_tokens": 1.5, "completion_tokens": 2, "total_tokens": 3.5},
            {"prompt_tokens": "", "completion_tokens": 2, "total_tokens": 2},
            {"prompt_tokens": "not-a-count", "completion_tokens": 2, "total_tokens": 3},
            {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": "3.5"},
        ]

        for payload in cases:
            with self.subTest(payload=payload):
                usage = normalize_litellm_usage(payload, model="openai/gpt-4o")

                self.assertEqual(usage["prompt_tokens"], 0)
                self.assertEqual(usage["completion_tokens"], 0)
                self.assertEqual(usage["total_tokens"], 0)
                self.assertIsNone(usage["normalized_prompt_tokens"])
                self.assertIsNone(usage["normalized_completion_tokens"])
                self.assertIsNone(usage["normalized_total_tokens"])
                self.assertEqual(usage["cache_observation"], "invalid_provider_usage")
                self.assertEqual(usage["eligibility_confidence"], "invalid")

    def test_impossible_total_tokens_are_marked_invalid(self):
        usage = normalize_litellm_usage(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 5},
            model="openai/gpt-4o",
        )

        self.assertEqual(usage["prompt_tokens"], 0)
        self.assertEqual(usage["completion_tokens"], 0)
        self.assertEqual(usage["total_tokens"], 0)
        self.assertEqual(usage["provider_reported_prompt_tokens"], 10)
        self.assertEqual(usage["cache_observation"], "invalid_provider_usage")
        self.assertEqual(usage["eligibility_confidence"], "invalid")

    def test_extra_total_tokens_are_not_marked_invalid(self):
        usage = normalize_litellm_usage(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 35},
            model="openai/gpt-4o",
        )

        self.assertEqual(usage["prompt_tokens"], 10)
        self.assertEqual(usage["completion_tokens"], 20)
        self.assertEqual(usage["total_tokens"], 35)
        self.assertNotEqual(usage["cache_observation"], "invalid_provider_usage")

    def test_should_persist_usage_telemetry_keeps_invalid_diagnostics_only(self):
        invalid_usage = normalize_litellm_usage({"prompt_tokens": -1}, model="openai/gpt-4o")
        no_usage = normalize_litellm_usage(None, model="openai/gpt-4o")
        metadata_only = normalize_litellm_usage(
            {"estimated_prefix_tokens": 123},
            model="openai/gpt-4o",
        )

        self.assertFalse(has_provider_usage_payload(invalid_usage))
        self.assertTrue(should_persist_usage_telemetry(invalid_usage))
        self.assertFalse(should_persist_usage_telemetry(no_usage))
        self.assertFalse(should_persist_usage_telemetry(metadata_only))

    def test_raw_usage_drops_unmodeled_metadata_before_size_limit(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1,
                "prompt_tokens_details": {"cached_tokens": 1},
                "metadata": {"plain_url": "https://example.test/path?token_count=2"},
                "nested": {"safe_count": 2},
                "headers": {"authorization": "Bearer secret"},
                "large": "x" * 5000,
            },
            model="gateway/custom-model",
            provider="gateway",
        )

        raw = usage["provider_usage_json"]
        self.assertIsNotNone(raw)
        parsed = json.loads(raw)
        self.assertEqual(parsed, {"prompt_tokens": 1, "prompt_tokens_details": {"cached_tokens": 1}})
        self.assertNotIn("_truncated", parsed)
        self.assertNotIn("example.test", raw)
        self.assertNotIn("safe_count", raw)
        self.assertNotIn("authorization", raw)
        self.assertNotIn("x" * 100, raw)

    def test_raw_usage_drops_tokenizer_free_text_fields(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1,
                "completion_tokens": 2,
                "total_tokens": 3,
                "api_key": "sk-secret",
                "headers": {"authorization": "Bearer secret"},
                "raw_prompt": "do not persist this prompt",
                "nested": {"raw_user_input": "do not persist this user input"},
                "tokenizer_name": "cl100k_base prompt fragment",
                "tokenizer_version": "Authorization: Bearer sk-header",
            },
            model="gateway/custom-model",
        )

        raw = usage["provider_usage_json"]
        self.assertIsNotNone(raw)
        self.assertLessEqual(len(raw.encode("utf-8")), 4096)
        self.assertNotIn("sk-secret", raw)
        self.assertNotIn("authorization", raw)
        self.assertNotIn("do not persist this prompt", raw)
        self.assertNotIn("do not persist this user input", raw)
        parsed = json.loads(raw)
        self.assertEqual(parsed, {"completion_tokens": 2, "prompt_tokens": 1, "total_tokens": 3})
        self.assertNotIn("tokenizer_name", parsed)
        self.assertNotIn("tokenizer_version", parsed)

    def test_raw_usage_drops_unmodeled_prompt_message_content_fields(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "total_tokens": 5,
                "prompt": "SECRET_PROMPT",
                "messages": [{"role": "user", "content": "SECRET_MESSAGE"}],
                "content": "SECRET_CONTENT",
                "input": "SECRET_INPUT",
                "output": "SECRET_OUTPUT",
            },
            model="gateway/custom-model",
            provider="gateway",
        )

        raw = usage["provider_usage_json"]
        self.assertIsNotNone(raw)
        self.assertNotIn("SECRET_PROMPT", raw)
        self.assertNotIn("SECRET_MESSAGE", raw)
        self.assertNotIn("SECRET_CONTENT", raw)
        self.assertNotIn("SECRET_INPUT", raw)
        self.assertNotIn("SECRET_OUTPUT", raw)
        parsed = json.loads(raw)
        self.assertEqual(parsed, {"completion_tokens": 2, "prompt_tokens": 3, "total_tokens": 5})

    def test_raw_usage_sanitizes_forbidden_key_variants(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1,
                "apiKey": "sk-secret",
                "x-api-key": "sk-secondary",
                "requestBody": "raw request payload",
                "responseText": "raw model response",
                "webhook_url": "https://example.test/hook",
                "nested": {
                    "rawUserInput": "private user input",
                    "safe_count": 2,
                },
            },
            model="gateway/custom-model",
        )

        raw = usage["provider_usage_json"]
        self.assertIsNotNone(raw)
        self.assertNotIn("sk-secret", raw)
        self.assertNotIn("sk-secondary", raw)
        self.assertNotIn("raw request payload", raw)
        self.assertNotIn("raw model response", raw)
        self.assertNotIn("example.test/hook", raw)
        self.assertNotIn("private user input", raw)
        parsed = json.loads(raw)
        self.assertEqual(parsed["prompt_tokens"], 1)
        self.assertNotIn("nested", parsed)

    def test_raw_usage_drops_invalid_count_string_values(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1,
                "completion_tokens": "2",
                "total_tokens": "3",
                "cached_tokens": "not-a-count",
                "prompt_tokens_details": {
                    "cached_tokens": "https://hooks.slack.com/services/T000/B000/secret",
                    "audio_tokens": "4",
                },
            },
            model="gateway/custom-model",
            provider="gateway",
        )

        raw = usage["provider_usage_json"]
        self.assertIsNotNone(raw)
        parsed = json.loads(raw)
        self.assertEqual(
            parsed,
            {
                "completion_tokens": 2,
                "prompt_tokens": 1,
                "prompt_tokens_details": {"audio_tokens": 4},
                "total_tokens": 3,
            },
        )
        self.assertNotIn("cached_tokens", parsed)
        self.assertNotIn("hooks.slack.com", raw)

    def test_raw_usage_drops_invalid_nested_count_urls(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 1,
                "prompt_tokens_details": {
                    "cached_tokens": "https://sctapi.ftqq.com/SCTSECRET.send?title=x",
                    "audio_tokens": "https://hooks.internal.example/path/secret",
                    "text_tokens": 5,
                },
                "completion_tokens_details": {
                    "reasoning_tokens": "6",
                },
            },
            model="gateway/custom-model",
            provider="gateway",
        )

        raw = usage["provider_usage_json"]
        self.assertIsNotNone(raw)
        self.assertNotIn("sctapi.ftqq.com", raw)
        self.assertNotIn("hooks.internal.example", raw)
        parsed = json.loads(raw)
        self.assertEqual(
            parsed,
            {
                "completion_tokens_details": {"reasoning_tokens": 6},
                "prompt_tokens": 1,
                "prompt_tokens_details": {"text_tokens": 5},
            },
        )
