"""Tests for system config secrets."""

from tests.application.runtime._system_config_service_support import (
    Any,
    Dict,
    List,
    SimpleNamespace,
    _SystemConfigServiceTestCaseFixture,
    contextmanager,
    json,
    logging,
    os,
    patch,
    requests,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_get_config_keeps_regular_sensitive_values_unmasked(self) -> None:
        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertIn("GEMINI_API_KEY", items)
        self.assertEqual(items["GEMINI_API_KEY"]["value"], "secret-key-value")
        self.assertFalse(items["GEMINI_API_KEY"]["is_masked"])
        self.assertTrue(items["GEMINI_API_KEY"]["raw_value_exists"])

    def test_get_config_masks_alphasift_install_spec(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "ALPHASIFT_INSTALL_SPEC=git+https://user:token@example.com/internal/alphasift.git",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["ALPHASIFT_INSTALL_SPEC"]["value"], payload["mask_token"])
        self.assertTrue(items["ALPHASIFT_INSTALL_SPEC"]["is_masked"])
        self.assertTrue(items["ALPHASIFT_INSTALL_SPEC"]["schema"]["is_sensitive"])

    def test_get_config_masks_hermes_secret_fields(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_CHANNELS=hermes",
            "LLM_HERMES_API_KEY=sk-hermes-secret-value",
            "LLM_HERMES_API_KEYS=sk-old-secret-value",
            "LLM_HERMES_EXTRA_HEADERS={\"Authorization\":\"Bearer secret\"}",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["LLM_HERMES_API_KEY"]["value"], payload["mask_token"])
        self.assertTrue(items["LLM_HERMES_API_KEY"]["is_masked"])
        self.assertEqual(items["LLM_HERMES_API_KEYS"]["value"], payload["mask_token"])
        self.assertTrue(items["LLM_HERMES_API_KEYS"]["is_masked"])
        self.assertEqual(items["LLM_HERMES_EXTRA_HEADERS"]["value"], payload["mask_token"])
        self.assertTrue(items["LLM_HERMES_EXTRA_HEADERS"]["is_masked"])

    def test_hermes_saved_secret_changed_port_does_not_send_request(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_CHANNELS=hermes",
            "LLM_HERMES_PROTOCOL=openai",
            "LLM_HERMES_BASE_URL=http://127.0.0.1:8642/v1",
            "LLM_HERMES_API_KEY=sk-hermes-secret-value",
        )

        with patch("src.application.runtime.system_config_service.requests.Session") as session_cls:
            result = self.service.discover_llm_channel_models(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:9999/v1",
                api_key="******",
                models=["hermes-agent"],
                use_saved_secret=True,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "saved_secret_scope_mismatch")
        session_cls.assert_not_called()

    def test_hermes_saved_secret_runtime_env_cannot_rebind_endpoint(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_CHANNELS=hermes",
            "LLM_HERMES_PROTOCOL=openai",
            "LLM_HERMES_BASE_URL=http://127.0.0.1:8642/v1",
            "LLM_HERMES_API_KEY=saved-secret-token",
        )

        with patch.dict(os.environ, {"LLM_HERMES_BASE_URL": "http://127.0.0.1:9999/v1"}, clear=False), \
             patch("src.application.runtime.system_config_service.requests.Session") as session_cls:
            result = self.service.discover_llm_channel_models(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:9999/v1",
                api_key="******",
                models=["hermes-agent"],
                use_saved_secret=True,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "saved_secret_scope_mismatch")
        self.assertNotIn("saved-secret-token", str(result))
        session_cls.assert_not_called()

    def test_hermes_model_discovery_uses_no_proxy_session(self) -> None:
        observed: Dict[str, Any] = {}

        class FakeSession:
            def __init__(self) -> None:
                self.trust_env = True

            def get(self, url: str, **kwargs: Any) -> Any:
                observed["url"] = url
                observed["trust_env"] = self.trust_env
                observed["headers"] = kwargs.get("headers") or {}
                return SimpleNamespace(
                    status_code=200,
                    ok=True,
                    json=lambda: {"data": [{"id": "hermes-agent"}]},
                )

            def close(self) -> None:
                observed["closed"] = True

        with patch("src.application.runtime.system_config_service.requests.Session", side_effect=FakeSession), \
             patch("src.application.runtime.system_config_service.requests.get") as requests_get:
            result = self.service.discover_llm_channel_models(
                name="hermes",
                protocol="openai",
                base_url="http://localhost:8642/v1",
                api_key="sk-hermes-secret-value",
                models=["hermes-agent"],
            )

        self.assertTrue(result["success"])
        self.assertEqual(observed["url"], "http://127.0.0.1:8642/v1/models")
        self.assertFalse(observed["trust_env"])
        self.assertEqual(observed["headers"]["Authorization"], "Bearer sk-hermes-secret-value")
        self.assertTrue(observed["closed"])
        requests_get.assert_not_called()

    def test_hermes_model_discovery_invalid_url_fails_before_request(self) -> None:
        with patch("src.application.runtime.system_config_service.requests.Session") as session_cls:
            result = self.service.discover_llm_channel_models(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1?next=proxy",
                api_key="saved-secret-token",
                models=["hermes-agent"],
            )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "invalid_config")
        self.assertEqual(result["details"]["reason"], "invalid_hermes_url")
        self.assertNotIn("saved-secret-token", rendered)
        session_cls.assert_not_called()

    def test_hermes_model_discovery_http_error_redacts_non_sk_secret(self) -> None:
        class FakeSession:
            def __init__(self) -> None:
                self.trust_env = True

            def get(self, *_args: Any, **_kwargs: Any) -> Any:
                return SimpleNamespace(
                    status_code=500,
                    ok=False,
                    json=lambda: {"error": {"message": "upstream saw saved-secret-token"}},
                    text="upstream saw saved-secret-token",
                )

            def close(self) -> None:
                pass

        with patch("src.application.runtime.system_config_service.requests.Session", side_effect=FakeSession):
            result = self.service.discover_llm_channel_models(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key="saved-secret-token",
                models=["hermes-agent"],
            )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        self.assertFalse(result["success"])
        self.assertNotIn("saved-secret-token", rendered)
        self.assertNotIn("Bearer saved-secret-token", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_llm_result_redacts_raw_comma_secret_and_segments(self) -> None:
        raw_secret = "saved-secret-token,second-part"
        redactions = self.service._build_redaction_values(raw_secret)
        variants = [
            "Bearer saved-secret-token,second-part",
            "Bearer saved-secret-token, second-part",
            "Bearer saved-secret-token ,second-part",
            "Authorization: Bearer saved-secret-token,   second-part",
            "upstream saw saved-secret-token, second-part",
        ]

        result = self.service._build_llm_channel_result(
            success=False,
            message="; ".join(variants),
            error=" | ".join(variants),
            stage="model_discovery",
            error_code="network_error",
            retryable=False,
            details={
                "raw": raw_secret,
                "variants": variants,
                "first": "saved-secret-token",
                "second": "second-part",
            },
            capability_results={
                "json": {
                    "status": "failed",
                    "message": variants[1],
                    "details": {"echo": variants[3]},
                }
            },
            resolved_protocol="openai",
            models=[],
            latency_ms=None,
            redaction_values=redactions,
        )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        self.assertNotIn(raw_secret, rendered)
        for variant in variants:
            self.assertNotIn(variant, rendered)
        self.assertNotIn("saved-secret-token", rendered)
        self.assertNotIn("second-part", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_llm_result_recursively_redacts_models_details_and_capabilities(self) -> None:
        raw_secret = "saved-secret-token,second-part"
        redactions = self.service._build_redaction_values(raw_secret)

        details = self.service._sanitize_llm_details(
            {
                "items": [
                    {"message": "saved-secret-token"},
                    [{"nested": "Bearer saved-secret-token, second-part"}],
                ],
                "saved-secret-token": "second-part",
            },
            redaction_values=redactions,
        )
        result = self.service._build_llm_channel_result(
            success=False,
            message="upstream saw saved-secret-token, second-part",
            error="Authorization: Bearer saved-secret-token,   second-part",
            stage="model_discovery",
            error_code="network_error",
            retryable=False,
            details=details,
            resolved_protocol="openai",
            resolved_model="saved-secret-token",
            models=["saved-secret-token", ["second-part"]],
            capability_results={
                "json": {
                    "status": "failed",
                    "details": {"items": [{"message": "saved-secret-token"}]},
                }
            },
            redaction_values=redactions,
        )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        self.assertNotIn(raw_secret, rendered)
        self.assertNotIn("saved-secret-token, second-part", rendered)
        self.assertNotIn("saved-secret-token", rendered)
        self.assertNotIn("second-part", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_hermes_model_discovery_request_exception_redacts_response_and_logs(self) -> None:
        class FakeSession:
            def __init__(self) -> None:
                self.trust_env = True

            def get(self, *_args: Any, **_kwargs: Any) -> Any:
                raise requests.RequestException("proxy saw saved-secret-token")

            def close(self) -> None:
                pass

        with patch("src.application.runtime.system_config_service.requests.Session", side_effect=FakeSession), \
             self.assertLogs("src.application.runtime.system_config_service", level="WARNING") as logs:
            result = self.service.discover_llm_channel_models(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key="saved-secret-token",
                models=["hermes-agent"],
            )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        log_text = "\n".join(logs.output)
        self.assertFalse(result["success"])
        self.assertNotIn("saved-secret-token", rendered)
        self.assertNotIn("saved-secret-token", log_text)
        self.assertIn("[REDACTED]", rendered)
        self.assertIn("[REDACTED]", log_text)

    def test_hermes_request_exception_redacts_comma_secret_variants_from_logs(self) -> None:
        raw_secret = "saved-secret-token,second-part"
        variants = [
            "Bearer saved-secret-token,second-part",
            "Bearer saved-secret-token, second-part",
            "Bearer saved-secret-token ,second-part",
            "Authorization: Bearer saved-secret-token,   second-part",
            "upstream saw saved-secret-token, second-part",
        ]
        redactions = self.service._build_redaction_values(raw_secret)
        sanitized = self.service._sanitize_llm_error_text(
            " | ".join(variants),
            redaction_values=redactions,
        )
        with self.assertLogs("src.application.runtime.system_config_service", level="WARNING") as logs:
            logging.getLogger("src.application.runtime.system_config_service").warning(
                "LLM channel model discovery failed for hermes: %s",
                sanitized,
            )

        log_text = "\n".join(logs.output)
        self.assertNotIn(raw_secret, log_text)
        self.assertNotIn("saved-secret-token, second-part", log_text)
        self.assertNotIn("saved-secret-token", log_text)
        self.assertNotIn("second-part", log_text)
        for variant in variants:
            self.assertNotIn(variant, log_text)
        self.assertIn("[REDACTED]", log_text)

    def test_hermes_channel_test_invalid_url_fails_before_completion(self) -> None:
        with patch("src.infrastructure.providers.system_config_runtime.open_hermes_no_proxy_client") as no_proxy_client, \
             patch("litellm.completion") as completion:
            result = self.service.test_llm_channel(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1#fragment",
                api_key="saved-secret-token",
                models=["hermes-agent"],
                capability_checks=["json"],
            )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "invalid_config")
        self.assertEqual(result["details"]["reason"], "invalid_hermes_url")
        self.assertEqual(result["capability_results"]["json"]["status"], "skipped")
        self.assertNotIn("saved-secret-token", rendered)
        no_proxy_client.assert_not_called()
        completion.assert_not_called()

    def test_hermes_runtime_only_masked_key_is_not_sent_for_channel_test(self) -> None:
        with patch("src.infrastructure.providers.system_config_runtime.open_hermes_no_proxy_client") as no_proxy_client, \
             patch("litellm.completion") as completion:
            result = self.service.test_llm_channel(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key="******",
                models=["hermes-agent"],
                use_saved_secret=False,
                capability_checks=["json"],
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "runtime_secret_not_reusable")
        self.assertEqual(result["details"]["reason"], "runtime_secret_not_reusable")
        self.assertEqual(result["capability_results"]["json"]["status"], "skipped")
        no_proxy_client.assert_not_called()
        completion.assert_not_called()

    def test_hermes_masked_key_is_not_sent_for_model_discovery(self) -> None:
        with patch("src.application.runtime.system_config_service.requests.Session") as session_cls:
            result = self.service.discover_llm_channel_models(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key="******",
                models=["hermes-agent"],
                use_saved_secret=False,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "runtime_secret_not_reusable")
        self.assertEqual(result["details"]["reason"], "runtime_secret_not_reusable")
        session_cls.assert_not_called()

    def test_hermes_saved_literal_masked_key_is_not_reused(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_CHANNELS=hermes",
            "LLM_HERMES_BASE_URL=http://127.0.0.1:8642/v1",
            "LLM_HERMES_API_KEY=******",
        )

        with patch("src.infrastructure.providers.system_config_runtime.open_hermes_no_proxy_client") as no_proxy_client, \
             patch("litellm.completion") as completion:
            result = self.service.test_llm_channel(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key="******",
                models=["hermes-agent"],
                use_saved_secret=True,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "runtime_secret_not_reusable")
        no_proxy_client.assert_not_called()
        completion.assert_not_called()

    def test_hermes_channel_test_rejects_comma_api_key_before_outbound(self) -> None:
        raw_key = "key-a,key-b"
        with patch("src.infrastructure.providers.system_config_runtime.open_hermes_no_proxy_client") as no_proxy_client, \
             patch("litellm.completion") as completion:
            result = self.service.test_llm_channel(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key=raw_key,
                models=["hermes-agent"],
                capability_checks=["json"],
            )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "invalid_config")
        self.assertEqual(result["details"]["reason"], "multiple_api_keys")
        self.assertNotIn(raw_key, rendered)
        self.assertNotIn("key-a", rendered)
        self.assertNotIn("key-b", rendered)
        no_proxy_client.assert_not_called()
        completion.assert_not_called()

    def test_hermes_model_discovery_rejects_comma_api_key_before_outbound(self) -> None:
        raw_key = "key-a,key-b"
        with patch("src.application.runtime.system_config_service.requests.Session") as session_cls:
            result = self.service.discover_llm_channel_models(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key=raw_key,
                models=["hermes-agent"],
            )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "invalid_config")
        self.assertEqual(result["details"]["reason"], "multiple_api_keys")
        self.assertNotIn(raw_key, rendered)
        self.assertNotIn("key-a", rendered)
        self.assertNotIn("key-b", rendered)
        session_cls.assert_not_called()

    def test_hermes_unsupported_capabilities_are_skipped_without_probe(self) -> None:
        no_proxy_calls: List[Dict[str, Any]] = []
        completion_models: List[str] = []

        @contextmanager
        def fake_no_proxy_openai_client(**kwargs: Any):
            no_proxy_calls.append(kwargs)
            yield object()

        def fake_completion(**kwargs: Any) -> Any:
            completion_models.append(str(kwargs.get("model") or ""))
            self.assertFalse(kwargs.get("stream"))
            self.assertIn("client", kwargs)
            self.assertNotIn("api_key", kwargs)
            self.assertNotIn("api_base", kwargs)
            return self._mock_completion_response("OK")

        with patch("src.infrastructure.providers.system_config_runtime.open_hermes_no_proxy_client", fake_no_proxy_openai_client), \
             patch("litellm.completion", side_effect=fake_completion):
            result = self.service.test_llm_channel(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key="sk-hermes-secret-value",
                models=["hermes-agent"],
                capability_checks=["tools", "stream", "vision"],
            )

        self.assertTrue(result["success"])
        self.assertEqual(len(no_proxy_calls), 1)
        self.assertEqual(completion_models, ["openai/hermes-agent"])
        capability_results = result["capability_results"]
        self.assertEqual(set(capability_results), {"tools", "stream", "vision"})
        for capability in ("tools", "stream", "vision"):
            self.assertEqual(capability_results[capability]["status"], "skipped")
            self.assertEqual(capability_results[capability]["error_code"], "not_probed")

    def test_hermes_failure_redacts_non_sk_secret_from_response_and_logs(self) -> None:
        @contextmanager
        def fake_no_proxy_openai_client(**_kwargs: Any):
            yield object()

        def fake_completion(**_kwargs: Any) -> Any:
            raise RuntimeError("upstream echoed saved-secret-token")

        with patch("src.infrastructure.providers.system_config_runtime.open_hermes_no_proxy_client", fake_no_proxy_openai_client), \
             patch("litellm.completion", side_effect=fake_completion), \
             self.assertLogs("src.application.runtime.system_config_service", level="WARNING") as logs:
            result = self.service.test_llm_channel(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key="saved-secret-token",
                models=["hermes-agent"],
            )

        self.assertFalse(result["success"])
        self.assertNotIn("saved-secret-token", str(result))
        self.assertNotIn("saved-secret-token", "\n".join(logs.output))

    def test_hermes_json_capability_exception_redacts_non_sk_secret(self) -> None:
        @contextmanager
        def fake_no_proxy_openai_client(**_kwargs: Any):
            yield object()

        completion_calls = 0

        def fake_completion(**_kwargs: Any) -> Any:
            nonlocal completion_calls
            completion_calls += 1
            if completion_calls == 1:
                return self._mock_completion_response("OK")
            raise RuntimeError("json capability saw saved-secret-token")

        with patch("src.infrastructure.providers.system_config_runtime.open_hermes_no_proxy_client", fake_no_proxy_openai_client), \
             patch("litellm.completion", side_effect=fake_completion):
            result = self.service.test_llm_channel(
                name="hermes",
                protocol="openai",
                base_url="http://127.0.0.1:8642/v1",
                api_key="saved-secret-token",
                models=["hermes-agent"],
                capability_checks=["json"],
            )

        rendered = json.dumps(result, ensure_ascii=False, default=str)
        self.assertTrue(result["success"])
        self.assertEqual(result["capability_results"]["json"]["status"], "failed")
        self.assertNotIn("saved-secret-token", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_get_config_masks_llm_usage_hmac_secret(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_USAGE_HMAC_SECRET=telemetry-secret",
            "LLM_USAGE_HMAC_KEY_VERSION=test-v1",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["LLM_USAGE_HMAC_SECRET"]["value"], payload["mask_token"])
        self.assertTrue(items["LLM_USAGE_HMAC_SECRET"]["is_masked"])
        self.assertTrue(items["LLM_USAGE_HMAC_SECRET"]["schema"]["is_sensitive"])
        self.assertEqual(items["LLM_USAGE_HMAC_KEY_VERSION"]["value"], "test-v1")
        self.assertFalse(items["LLM_USAGE_HMAC_KEY_VERSION"]["is_masked"])

    def test_generation_backend_status_preserves_masked_saved_secret(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
            "GEMINI_API_KEY=saved-secret-value",
        )

        payload = self.service.preview_generation_backend_status(
            items=[{"key": "GEMINI_API_KEY", "value": "******"}],
            mask_token="******",
        )

        self.assertEqual(payload["primary_backend_id"], "litellm")
        self.assertTrue(payload["primary"]["available"])

    def test_import_desktop_env_treats_mask_token_as_literal_value(self) -> None:
        current_version = self.manager.get_config_version()

        self.service.import_desktop_env(
            config_version=current_version,
            content="GEMINI_API_KEY=******\n",
            reload_now=False,
        )

        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["GEMINI_API_KEY"], "******")

    def test_update_preserves_masked_secret(self) -> None:
        old_version = self.manager.get_config_version()
        response = self.service.update(
            config_version=old_version,
            items=[
                {"key": "GEMINI_API_KEY", "value": "******"},
                {"key": "STOCK_LIST", "value": "600519,300750"},
            ],
            mask_token="******",
            reload_now=False,
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["applied_count"], 1)
        self.assertEqual(response["skipped_masked_count"], 1)
        self.assertIn("STOCK_LIST", response["updated_keys"])

        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["STOCK_LIST"], "600519,300750")
        self.assertEqual(current_map["GEMINI_API_KEY"], "secret-key-value")

    def test_validate_rejects_explicit_hermes_only_agent_model(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "hermes"},
                {"key": "LLM_HERMES_API_KEY", "value": "sk-hermes-test-value"},
                {"key": "LLM_HERMES_MODELS", "value": "hermes-agent"},
                {"key": "AGENT_LITELLM_MODEL", "value": "openai/hermes-agent"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "AGENT_LITELLM_MODEL"
                and issue["code"] == "explicit_agent_model_no_safe_deployment"
                for issue in validation["issues"]
            )
        )

    def test_validate_rejects_bare_hermes_vision_model(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "hermes"},
                {"key": "LLM_HERMES_API_KEY", "value": "sk-hermes-test-value"},
                {"key": "LLM_HERMES_MODELS", "value": "hermes-agent"},
                {"key": "VISION_MODEL", "value": "hermes-agent"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "VISION_MODEL"
                and issue["code"] == "hermes_vision_unsupported"
                for issue in validation["issues"]
            )
        )

    @patch("src.infrastructure.notification.senders.wechat_sender.requests.post")
    def test_test_notification_channel_skips_masked_secret_overwrite(self, mock_post) -> None:
        self._rewrite_env("WECHAT_WEBHOOK_URL=https://saved.example.com/hook?key=savedsecret")
        mock_post.return_value = self._mock_http_response(200, {"errcode": 0})

        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="wechat",
                items=[{"key": "WECHAT_WEBHOOK_URL", "value": "******"}],
                mask_token="******",
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )

        self.assertTrue(payload["success"])
        self.assertEqual(mock_post.call_args[0][0], "https://saved.example.com/hook?key=savedsecret")

    @patch("src.infrastructure.notification.senders.ntfy_sender.requests.post")
    def test_test_notification_channel_supports_ntfy_and_masks_topic_target(self, mock_post) -> None:
        mock_post.return_value = self._mock_http_response(200)

        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="ntfy",
                items=[
                    {"key": "NTFY_URL", "value": "https://ntfy.sh/private-topic"},
                    {"key": "NTFY_TOKEN", "value": "secret-token"},
                ],
                title="Test title",
                content="hello",
                timeout_seconds=4,
            )

        self.assertTrue(payload["success"])
        self.assertEqual(mock_post.call_args.args[0], "https://ntfy.sh")
        self.assertEqual(mock_post.call_args.kwargs["json"]["topic"], "private-topic")
        self.assertEqual(mock_post.call_args.kwargs["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(mock_post.call_args.kwargs["timeout"], 4)
        self.assertIn("https://ntfy.sh/***", payload["attempts"][0]["target"])
        self.assertNotIn("private-topic", str(payload))
        self.assertNotIn("NTFY_URL", self.env_path.read_text(encoding="utf-8"))

    @patch("src.infrastructure.notification.senders.telegram_sender.requests.post")
    def test_test_notification_channel_masks_short_sensitive_target(self, mock_post) -> None:
        mock_post.return_value = self._mock_http_response(200, {"ok": True})

        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="telegram",
                items=[
                    {"key": "TELEGRAM_BOT_TOKEN", "value": "tok123"},
                    {"key": "TELEGRAM_CHAT_ID", "value": "chat-id"},
                ],
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["attempts"][0]["target"], "***")
        self.assertNotIn("tok123", str(payload))

    def test_update_warns_when_clearing_unsupported_hermes_keys(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_CHANNELS=hermes",
            "LLM_HERMES_PROTOCOL=openai",
            "LLM_HERMES_BASE_URL=http://127.0.0.1:8642/v1",
            "LLM_HERMES_API_KEY=sk-hermes-test-value",
            "LLM_HERMES_API_KEYS=sk-old-a,sk-old-b",
            'LLM_HERMES_EXTRA_HEADERS={"X":"Y"}',
            "LLM_HERMES_MODELS=hermes-agent",
        )

        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[
                {"key": "LLM_HERMES_API_KEYS", "value": ""},
                {"key": "LLM_HERMES_EXTRA_HEADERS", "value": ""},
            ],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        joined = " | ".join(response["warnings"])
        self.assertIn("Hermes Phase 3 不支持", joined)
        self.assertIn("LLM_HERMES_API_KEYS", joined)
        self.assertIn("LLM_HERMES_EXTRA_HEADERS", joined)
        self.assertIn("LLM_HERMES_API_KEY", joined)
        self.assertIn(".env 备份", joined)
        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["LLM_HERMES_API_KEYS"], "")
        self.assertEqual(current_map["LLM_HERMES_EXTRA_HEADERS"], "")
