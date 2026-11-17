"""Tests for system config validation."""

from tests.application.runtime._system_config_service_support import (
    Config,
    _SystemConfigServiceTestCaseFixture,
    os,
    patch,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_runtime_env_fallback_does_not_override_saved_provider_and_base_url_settings(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519",
            "LOG_LEVEL=INFO",
            "LITELLM_MODEL=openai/gpt-4o-mini",
            "OPENAI_MODEL=gpt-4.1",
        )

        with patch.dict(
            os.environ,
            {
                "OPENAI_BASE_URL": "https://runtime-openai.v1",
                "OPENAI_API_KEY": "runtime-openai-key",
            },
            clear=False,
        ):
            pre_save = self.service.get_config(include_schema=True)
            pre_save_items = {item["key"]: item for item in pre_save["items"]}

            self.assertEqual(pre_save_items["OPENAI_BASE_URL"]["value"], "https://runtime-openai.v1")
            self.assertFalse(pre_save_items["OPENAI_BASE_URL"]["raw_value_exists"])
            self.assertEqual(pre_save_items["OPENAI_API_KEY"]["value"], "runtime-openai-key")
            self.assertFalse(pre_save_items["OPENAI_API_KEY"]["raw_value_exists"])
            self.assertEqual(pre_save_items["LITELLM_MODEL"]["value"], "openai/gpt-4o-mini")
            self.assertTrue(pre_save_items["LITELLM_MODEL"]["raw_value_exists"])
            self.assertEqual(pre_save_items["OPENAI_MODEL"]["value"], "gpt-4.1")
            self.assertTrue(pre_save_items["OPENAI_MODEL"]["raw_value_exists"])

            response = self.service.update(
                config_version=self.manager.get_config_version(),
                items=[{"key": "STOCK_LIST", "value": "300750"}],
                reload_now=False,
            )
            self.assertTrue(response["success"])

            current_map = self.manager.read_config_map()
            self.assertEqual(current_map["STOCK_LIST"], "300750")
            self.assertEqual(current_map["LITELLM_MODEL"], "openai/gpt-4o-mini")
            self.assertEqual(current_map["OPENAI_MODEL"], "gpt-4.1")
            self.assertNotIn("OPENAI_BASE_URL", current_map)
            self.assertNotIn("OPENAI_API_KEY", current_map)

    def test_validate_reports_invalid_time(self) -> None:
        validation = self.service.validate(items=[{"key": "SCHEDULE_TIME", "value": "25:70"}])
        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_format" for issue in validation["issues"]))

    def test_validate_rejects_portfolio_risk_values_below_registry_min(self) -> None:
        """越界数值在设置页是「拒绝保存」，不是运行时 clamp。

        两条路径必须分开：`parse_env_float/int(minimum=...)` 只作用于 `.env` /
        进程环境变量读取；设置页保存走 registry ``validation.min``，越界返回
        ``out_of_range`` 并阻止写入。批次 P4 的文案据此描述，这里把区分钉住，
        避免后续批次把 clamp 当成唯一越界行为。
        """
        cases = (
            ("PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT", "-1", ">=0.0"),
            ("PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT", "-0.5", ">=0.0"),
            ("PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT", "-10", ">=0.0"),
            ("PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO", "-0.1", ">=0.0"),
            ("PORTFOLIO_RISK_LOOKBACK_DAYS", "0", ">=1"),
        )
        for key, bad_value, expected in cases:
            with self.subTest(key=key):
                validation = self.service.validate(items=[{"key": key, "value": bad_value}])
                self.assertFalse(validation["valid"])
                issue = next(i for i in validation["issues"] if i["key"] == key)
                self.assertEqual(issue["code"], "out_of_range")
                self.assertEqual(issue["severity"], "error")
                self.assertEqual(issue["expected"], expected)

    def test_validate_accepts_portfolio_risk_values_without_upper_bound(self) -> None:
        """registry 只声明下限、不新增上限：下限上的边界值与极大值都应通过。"""
        validation = self.service.validate(
            items=[
                {"key": "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT", "value": "0"},
                {"key": "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO", "value": "10000"},
                {"key": "PORTFOLIO_RISK_LOOKBACK_DAYS", "value": "1"},
            ]
        )
        self.assertTrue(validation["valid"], validation["issues"])

    def test_validate_rejects_non_literal_boolean_for_portfolio_fx_switch(self) -> None:
        """`1` 在 `.env` 里会被读成关闭，因此设置页必须直接拒绝而不是静默关闭。"""
        validation = self.service.validate(items=[{"key": "PORTFOLIO_FX_UPDATE_ENABLED", "value": "1"}])
        self.assertFalse(validation["valid"])
        issue = next(i for i in validation["issues"] if i["key"] == "PORTFOLIO_FX_UPDATE_ENABLED")
        self.assertEqual(issue["code"], "invalid_type")
        accepted = self.service.validate(items=[{"key": "PORTFOLIO_FX_UPDATE_ENABLED", "value": "false"}])
        self.assertTrue(accepted["valid"], accepted["issues"])

    def test_validate_rejects_p5_numeric_values_below_registry_min(self) -> None:
        """批次 P5 数值字段与 P4 同口径：越界是拒绝保存，不是静默 clamp。"""
        for key, bad_value in (("WECHAT_MAX_BYTES", "0"), ("MARKDOWN_TO_IMAGE_MAX_CHARS", "-1")):
            with self.subTest(key=key):
                validation = self.service.validate(items=[{"key": key, "value": bad_value}])
                self.assertFalse(validation["valid"])
                issue = next(i for i in validation["issues"] if i["key"] == key)
                self.assertEqual(issue["code"], "out_of_range")
                self.assertEqual(issue["severity"], "error")
                self.assertEqual(issue["expected"], ">=1")
                accepted = self.service.validate(items=[{"key": key, "value": "1"}])
                self.assertTrue(accepted["valid"], accepted["issues"])
        # 只声明下限：极大值仍可保存。
        huge = self.service.validate(items=[{"key": "WECHAT_MAX_BYTES", "value": "999999999"}])
        self.assertTrue(huge["valid"], huge["issues"])

    def test_validate_rejects_p5_select_values_outside_options(self) -> None:
        """下拉字段的 enum 由 options 派生，保存时必须拦住列表外的值。

        运行时对这两个字段并不同构：`MD2IMG_ENGINE` 会回落 wkhtmltoimage，
        而 `WECHAT_MSG_TYPE` 会把任意值原样存下、由发送侧按 markdown 处理，
        所以设置页不能像 `.env` 那样“填了再说”。
        """
        for key, bad_value, options in (
            ("MD2IMG_ENGINE", "puppeteer", ("wkhtmltoimage", "markdown-to-file")),
            ("WECHAT_MSG_TYPE", "news", ("markdown", "text")),
        ):
            with self.subTest(key=key):
                validation = self.service.validate(items=[{"key": key, "value": bad_value}])
                self.assertFalse(validation["valid"])
                issue = next(i for i in validation["issues"] if i["key"] == key)
                self.assertEqual(issue["code"], "invalid_enum")
                self.assertEqual(issue["expected"], ",".join(options))
                accepted = self.service.validate(items=[{"key": key, "value": options[1]}])
                self.assertTrue(accepted["valid"], accepted["issues"])

    def test_validate_accepts_empty_schedule_times_fallback(self) -> None:
        validation = self.service.validate(items=[{"key": "SCHEDULE_TIMES", "value": ""}])
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_reports_invalid_searxng_url(self) -> None:
        validation = self.service.validate(items=[{"key": "SEARXNG_BASE_URLS", "value": "searx.local,https://ok.example"}])
        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_url" for issue in validation["issues"]))

    def test_validate_reports_invalid_public_searxng_toggle(self) -> None:
        validation = self.service.validate(
            items=[{"key": "SEARXNG_PUBLIC_INSTANCES_ENABLED", "value": "maybe"}]
        )
        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_type" for issue in validation["issues"]))

    def test_validate_warns_daily_digest_is_reserved(self) -> None:
        validation = self.service.validate(
            items=[{"key": "NOTIFICATION_DAILY_DIGEST_ENABLED", "value": "true"}]
        )

        self.assertTrue(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "NOTIFICATION_DAILY_DIGEST_ENABLED"
                and issue["code"] == "reserved_notification_daily_digest"
                and issue["severity"] == "warning"
                for issue in validation["issues"]
            )
        )

    def test_validate_warns_when_only_folder_token_cleared_with_app_credentials(self) -> None:
        """Clearing FEISHU_FOLDER_TOKEN while app credentials remain should trigger mismatch."""
        old_version = self.manager.get_config_version()
        self.service.update(
            config_version=old_version,
            items=[
                {"key": "FEISHU_APP_ID", "value": "cli_xxx"},
                {"key": "FEISHU_APP_SECRET", "value": "secret_xxx"},
            ],
        )
        validation = self.service.validate(
            items=[
                {"key": "FEISHU_FOLDER_TOKEN", "value": ""},
            ]
        )
        self.assertTrue(validation["valid"])
        self.assertTrue(
            any(
                issue["code"] == "feishu_mode_mismatch"
                and issue["severity"] == "warning"
                for issue in validation["issues"]
            )
        )

    def test_validate_allows_explicit_mixed_agent_model(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "hermes,remote"},
                {"key": "LLM_HERMES_API_KEY", "value": "sk-hermes-test-value"},
                {"key": "LLM_HERMES_MODELS", "value": "shared-route"},
                {"key": "LLM_REMOTE_PROTOCOL", "value": "openai"},
                {"key": "LLM_REMOTE_BASE_URL", "value": "https://api.example.com/v1"},
                {"key": "LLM_REMOTE_API_KEY", "value": "sk-remote-test-value"},
                {"key": "LLM_REMOTE_MODELS", "value": "shared-route"},
                {"key": "AGENT_LITELLM_MODEL", "value": "openai/shared-route"},
            ]
        )

        self.assertFalse(
            any(
                issue["key"] == "AGENT_LITELLM_MODEL"
                and issue["code"] == "explicit_agent_model_no_safe_deployment"
                for issue in validation["issues"]
            ),
            validation["issues"],
        )

    @patch.object(
        Config,
        "parse_litellm_yaml",
        return_value=[
            {
                "model_name": "gpt4o",
                "litellm_params": {"model": "openai/gpt-4o-mini", "api_key": "sk-test-value"},
            }
        ],
    )
    def test_validate_accepts_unprefixed_agent_model_when_yaml_declares_alias(self, _mock_parse_yaml) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LITELLM_CONFIG", "value": "/tmp/litellm.yaml"},
                {"key": "AGENT_LITELLM_MODEL", "value": "gpt4o"},
            ]
        )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_reports_invalid_select_option(self) -> None:
        validation = self.service.validate(items=[{"key": "AGENT_ARCH", "value": "invalid-mode"}])

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_enum" for issue in validation["issues"]))

    def test_validate_accepts_report_language_english(self) -> None:
        validation = self.service.validate(items=[{"key": "REPORT_LANGUAGE", "value": "en"}])

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_accepts_report_language_korean(self) -> None:
        validation = self.service.validate(items=[{"key": "REPORT_LANGUAGE", "value": "ko"}])

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_accepts_comma_separated_market_review_region(self) -> None:
        validation = self.service.validate(
            items=[{"key": "MARKET_REVIEW_REGION", "value": "cn,jp,us"}]
        )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_accepts_blank_context_compression_preset_fields(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS", "value": ""},
                {"key": "AGENT_CONTEXT_PROTECTED_TURNS", "value": ""},
            ]
        )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_reports_invalid_context_compression_profile(self) -> None:
        validation = self.service.validate(
            items=[{"key": "AGENT_CONTEXT_COMPRESSION_PROFILE", "value": "invalid"}]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_enum" for issue in validation["issues"]))

    def test_validate_reports_invalid_json(self) -> None:
        validation = self.service.validate(items=[{"key": "AGENT_EVENT_ALERT_RULES_JSON", "value": "[invalid"}])

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_json" for issue in validation["issues"]))

    def test_validate_accepts_blank_optional_json(self) -> None:
        validation = self.service.validate(items=[{"key": "AGENT_EVENT_ALERT_RULES_JSON", "value": ""}])

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_accepts_multiline_json(self) -> None:
        validation = self.service.validate(items=[{
            "key": "AGENT_EVENT_ALERT_RULES_JSON",
            "value": (
                "[\n"
                '  {"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800}\n'
                "]"
            ),
        }])

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_accepts_legacy_agent_orchestrator_mode_alias(self) -> None:
        validation = self.service.validate(items=[{"key": "AGENT_ORCHESTRATOR_MODE", "value": "strategy"}])

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_accepts_minimax_model_as_direct_env_provider(self) -> None:
        """minimax is NOT a managed key provider; it uses LiteLLM direct-env routing."""
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "minimax/MiniMax-M1"},
                {"key": "LLM_PRIMARY_ENABLED", "value": "false"},
                {"key": "LITELLM_MODEL", "value": "minimax/MiniMax-M1"},
            ]
        )

        self.assertFalse(any(issue.get("key") == "LITELLM_MODEL" and issue["code"] == "missing_runtime_source" for issue in validation.get("issues", [])))

    def test_validate_accepts_cohere_model_as_direct_env_provider(self) -> None:
        """cohere is NOT a managed key provider; it also uses LiteLLM direct-env routing."""
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_ENABLED", "value": "false"},
                {"key": "LITELLM_MODEL", "value": "cohere/command-r-plus"},
            ]
        )

        self.assertFalse(any(issue.get("key") == "LITELLM_MODEL" and issue["code"] == "missing_runtime_source" for issue in validation.get("issues", [])))

    def test_validate_accepts_google_model_as_direct_env_provider(self) -> None:
        """google prefix is not managed by project key buckets and is kept as direct provider routing."""
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_ENABLED", "value": "false"},
                {"key": "LITELLM_MODEL", "value": "google/gemini-2.5-flash"},
            ]
        )

        self.assertFalse(any(issue.get("key") == "LITELLM_MODEL" and issue["code"] == "missing_runtime_source" for issue in validation.get("issues", [])))

    def test_validate_accepts_xai_model_as_direct_env_provider(self) -> None:
        """xai is not a managed provider key and is also preserved as direct runtime source."""
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_ENABLED", "value": "false"},
                {"key": "LITELLM_MODEL", "value": "xai/grok-beta"},
            ]
        )

        self.assertFalse(any(issue.get("key") == "LITELLM_MODEL" and issue["code"] == "missing_runtime_source" for issue in validation.get("issues", [])))

    def test_validate_reports_invalid_event_rule_semantics(self) -> None:
        validation = self.service.validate(items=[{
            "key": "AGENT_EVENT_ALERT_RULES_JSON",
            "value": '[{"stock_code":"600519","alert_type":"price_cross","status":"bad","direction":"above","price":1800}]',
        }])

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_event_rule" for issue in validation["issues"]))

    def test_validate_accepts_price_change_percent_event_rule(self) -> None:
        validation = self.service.validate(items=[{
            "key": "AGENT_EVENT_ALERT_RULES_JSON",
            "value": (
                '[{"stock_code":"300750","alert_type":"price_change_percent",'
                '"direction":"down","change_pct":3.0}]'
            ),
        }])

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_rejects_unsupported_event_rule_type(self) -> None:
        validation = self.service.validate(items=[{
            "key": "AGENT_EVENT_ALERT_RULES_JSON",
            "value": '[{"stock_code":"600519","alert_type":"sentiment_shift"}]',
        }])

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_event_rule" for issue in validation["issues"]))

    def test_validate_rejects_comma_only_api_key(self) -> None:
        """Whitespace/comma-only api_key must fail validation (P2: parsed-segment check)."""
        for bad_key in (",", " , ", "  ,  ,  "):
            with self.subTest(api_key=bad_key):
                validation = self.service.validate(
                    items=[
                        {"key": "LLM_CHANNELS", "value": "primary"},
                        {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                        {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                        {"key": "LLM_PRIMARY_API_KEY", "value": bad_key},
                    ]
                )
                self.assertFalse(validation["valid"])
                self.assertTrue(
                    any(issue["code"] == "missing_api_key" for issue in validation["issues"]),
                    f"Expected missing_api_key for api_key={bad_key!r}, got: {validation['issues']}",
                )

    def test_validate_rejects_ssrf_metadata_base_url(self) -> None:
        """base_url pointing to cloud metadata service must be blocked (P1: SSRF guard)."""
        for bad_url in (
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://100.100.100.200/latest/meta-data/",
        ):
            with self.subTest(base_url=bad_url):
                validation = self.service.validate(
                    items=[
                        {"key": "LLM_CHANNELS", "value": "primary"},
                        {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                        {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                        {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test"},
                        {"key": "LLM_PRIMARY_BASE_URL", "value": bad_url},
                    ]
                )
                self.assertFalse(validation["valid"])
                self.assertTrue(
                    any(issue["code"] == "ssrf_blocked" for issue in validation["issues"]),
                    f"Expected ssrf_blocked for base_url={bad_url!r}, got: {validation['issues']}",
                )

    def test_validate_allows_localhost_base_url(self) -> None:
        """localhost/LAN base_url must not be blocked (legitimate Ollama endpoints)."""
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "local"},
                {"key": "LLM_LOCAL_PROTOCOL", "value": "ollama"},
                {"key": "LLM_LOCAL_MODELS", "value": "llama3"},
                {"key": "LLM_LOCAL_API_KEY", "value": ""},
                {"key": "LLM_LOCAL_BASE_URL", "value": "http://localhost:11434"},
            ]
        )
        self.assertFalse(any(issue["code"] == "ssrf_blocked" for issue in validation["issues"]))
