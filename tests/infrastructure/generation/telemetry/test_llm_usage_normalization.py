"""Tests for llm usage normalization."""

from tests.infrastructure.generation.telemetry._llm_usage_support import (
    SimpleNamespace,
    Usage,
    extract_usage_payload,
    unittest,
)


class TestExtractUsagePayload(unittest.TestCase):
    def test_extracts_public_usage_before_private_hidden_usage(self):
        top_level_usage = {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=top_level_usage,
            usage_metadata=None,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), top_level_usage)

    def test_extracts_usage_metadata_before_private_hidden_usage(self):
        usage_metadata = {
            "prompt_token_count": 1,
            "candidates_token_count": 2,
            "total_token_count": 3,
        }
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=None,
            usage_metadata=usage_metadata,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), usage_metadata)

    def test_extracts_usage_metadata_when_public_usage_has_no_signal(self):
        top_level_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        usage_metadata = {
            "prompt_token_count": 1,
            "candidates_token_count": 2,
            "total_token_count": 3,
        }
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=top_level_usage,
            usage_metadata=usage_metadata,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), usage_metadata)

    def test_extracts_litellm_private_hidden_usage_from_object_chunk_best_effort(self):
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(usage=None, usage_metadata=None, _hidden_params={"usage": hidden_usage})

        self.assertIs(extract_usage_payload(response), hidden_usage)

    def test_extracts_private_hidden_usage_when_public_usage_is_zero_only(self):
        top_level_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=top_level_usage,
            usage_metadata=None,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), hidden_usage)

    def test_extracts_private_hidden_usage_object_when_public_object_is_zero_only(self):
        public_usage = Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        hidden_usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)

        response = SimpleNamespace(
            usage=public_usage,
            usage_metadata=None,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), hidden_usage)

    def test_keeps_public_usage_when_nested_cache_signal_exists(self):
        top_level_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "prompt_tokens_details": {"cached_tokens": 500},
        }
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=top_level_usage,
            usage_metadata=None,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), top_level_usage)

    def test_keeps_invalid_public_usage_instead_of_hidden_usage(self):
        top_level_usage = {"prompt_tokens": True}
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=top_level_usage,
            usage_metadata=None,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), top_level_usage)

    def test_keeps_blank_public_usage_count_instead_of_hidden_usage(self):
        top_level_usage = {"prompt_tokens": "", "completion_tokens": 2, "total_tokens": 2}
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=top_level_usage,
            usage_metadata=None,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), top_level_usage)

    def test_keeps_invalid_public_usage_instead_of_usage_metadata(self):
        top_level_usage = {"prompt_tokens": True}
        usage_metadata = {
            "prompt_token_count": 1,
            "candidates_token_count": 2,
            "total_token_count": 3,
        }
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=top_level_usage,
            usage_metadata=usage_metadata,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), top_level_usage)

    def test_keeps_invalid_usage_metadata_instead_of_hidden_usage(self):
        top_level_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        usage_metadata = {"prompt_token_count": True}
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = SimpleNamespace(
            usage=top_level_usage,
            usage_metadata=usage_metadata,
            _hidden_params={"usage": hidden_usage},
        )

        self.assertIs(extract_usage_payload(response), usage_metadata)

    def test_extracts_litellm_private_hidden_usage_from_dict_chunk_best_effort(self):
        hidden_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        response = {"usage": None, "usage_metadata": None, "_hidden_params": {"usage": hidden_usage}}

        self.assertIs(extract_usage_payload(response), hidden_usage)

    def test_returns_none_when_no_usage_payload_exists(self):
        response = SimpleNamespace(usage=None, usage_metadata=None, _hidden_params={})

        self.assertIsNone(extract_usage_payload(response))
