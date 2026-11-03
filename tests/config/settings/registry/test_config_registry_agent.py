"""Tests for config registry agent."""

from tests.config.settings._config_registry_support import (
    WEB_SETTINGS_PENDING_EXPOSURE,
    WEB_SETTINGS_UNREGISTERED_KEYS,
    _TestAgentContextCompressionFieldsFixture,
    _TestAgentEventAlertRulesJsonFieldFixture,
    _TestP3BotFieldsRegisteredFixture,
    build_schema_response,
    get_field_definition,
    get_registered_field_keys,
    unittest,
)


class TestAgentEventAlertRulesJsonField(_TestAgentEventAlertRulesJsonFieldFixture, unittest.TestCase):
    def test_description_marks_legacy_and_web_api_boundaries(self):
        field = get_field_definition("AGENT_EVENT_ALERT_RULES_JSON")
        description = field["description"]

        self.assertIn("Legacy JSON supports only price_cross, price_change_percent, and volume_spike", description)
        self.assertIn("Technical indicator", description)
        self.assertIn("watchlist", description)
        self.assertIn("portfolio", description)
        self.assertIn("market light", description)
        self.assertIn("Alert API/Web center", description)


class TestAgentContextCompressionFields(_TestAgentContextCompressionFieldsFixture, unittest.TestCase):
    def test_profile_uses_chinese_labels_and_enum(self):
        field = get_field_definition("AGENT_CONTEXT_COMPRESSION_PROFILE")

        self.assertEqual(field["category"], "agent")
        self.assertEqual(field["ui_control"], "select")
        self.assertEqual(
            field["validation"]["enum"],
            ["cost", "balanced", "long_context_raw_first"],
        )
        self.assertEqual(
            [option["label"] for option in field["options"]],
            ["成本优先", "均衡推荐", "长上下文原文优先"],
        )

    def test_trigger_and_protected_turns_can_follow_profile_preset(self):
        trigger = get_field_definition("AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS")
        protected = get_field_definition("AGENT_CONTEXT_PROTECTED_TURNS")

        self.assertEqual(trigger["default_value"], "")
        self.assertEqual(protected["default_value"], "")
        self.assertFalse(trigger["is_required"])
        self.assertFalse(protected["is_required"])
        self.assertIn("Leave empty", trigger["description"])
        self.assertIn("Leave empty", protected["description"])


class TestP3BotFieldsRegistered(_TestP3BotFieldsRegisteredFixture, unittest.TestCase):
    def test_fields_are_explicitly_registered(self) -> None:
        registered = set(get_registered_field_keys())
        for key in self._FIELD_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", key)
            self.assertEqual(field["display_order"], self._DISPLAY_ORDERS[key], key)
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")
            self.assertTrue(field.get("description"), f"{key} 缺少 description")
            self.assertNotIn(key, WEB_SETTINGS_UNREGISTERED_KEYS, f"{key} 注册后必须从声明表移除")
            self.assertIn(key, registered, key)

    def test_help_keys_grouped_by_capability(self) -> None:
        for help_key, keys in self._HELP_KEY_GROUPS.items():
            for key in keys:
                self.assertEqual(
                    get_field_definition(key)["help_key"],
                    help_key,
                    f"{key} 的 help_key 应与同族字段一致",
                )
        # EMAIL_SENDER_NAME 复用既有邮件分组，不新建同义 help_key
        self.assertEqual(
            get_field_definition("EMAIL_SENDER_NAME")["help_key"],
            "settings.notification.email",
        )

    def test_credentials_use_password_control_and_ids_do_not(self) -> None:
        for key in self._CREDENTIAL_KEYS:
            field = get_field_definition(key)
            self.assertTrue(field["is_sensitive"], f"{key} 应标为敏感字段")
            self.assertEqual(field["ui_control"], "password", f"{key} 必须用密码控件")
        for key in ("FEISHU_FOLDER_TOKEN", "BOT_ADMIN_USERS", "BOT_COMMAND_PREFIX"):
            field = get_field_definition(key)
            self.assertFalse(field["is_sensitive"], f"{key} 是标识/名单，不是密钥")

    def test_restart_boundary_matches_runtime_read_path(self) -> None:
        for key in self._RESTART_BOUNDARY_KEYS:
            self.assertIn(
                "restart_required",
                get_field_definition(key).get("warning_codes", []),
                f"{key} 在一次性构造时读取，必须提醒重启",
            )
        for key in self._HOT_RELOAD_KEYS:
            self.assertNotIn(
                "restart_required",
                get_field_definition(key).get("warning_codes", []),
                f"{key} 按请求/按实例读取，不该误导用户重启",
            )

        # 上面的提醒只在“保存链路不会重置分发器”时成立。若将来接上重置，
        # 这条断言会失败，提醒同步去掉 BOT_* 的 restart_required。
        save_path = (self._ROOT / "src/application/runtime/system_config_service.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("reset_dispatcher", save_path)

    def test_no_consumer_keys_stay_declared_but_unregistered(self) -> None:
        registered = set(get_registered_field_keys())
        for key in self._NO_CONSUMER_KEYS:
            self.assertNotIn(key, registered, f"{key} 无运行时读取方，不得注册到设置页")
            self.assertIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 必须留在 pending 声明表")

    def test_numeric_bound_matches_runtime_clamping(self) -> None:
        validation = get_field_definition("FEISHU_MAX_BYTES")["validation"]
        self.assertEqual(float(validation["min"]), 1.0)
        # 运行时只收下限，不收上限：registry 不能多出一个 max 而把可用值锁窄。
        self.assertNotIn("max", validation)
        clamped = self._build_config({"FEISHU_MAX_BYTES": "0"})
        self.assertEqual(clamped.feishu_max_bytes, 1)
        default = self._build_config({})
        self.assertEqual(default.feishu_max_bytes, 20000)

    def test_defaults_match_runtime_parsing(self) -> None:
        config = self._build_config({})
        self.assertTrue(config.bot_enabled)
        self.assertEqual(config.bot_command_prefix, "/")
        self.assertEqual(config.bot_admin_users, [])
        self.assertFalse(config.feishu_send_as_file)
        self.assertEqual(config.email_sender_name, "HermesX股票分析助手")
        self.assertIsNone(config.feishu_verification_token)

        # 逗号分隔名单：运行时去空白、丢空项，与 array 字段的保存形态一致。
        split = self._build_config({"BOT_ADMIN_USERS": "ou_a, ou_b ,, "})
        self.assertEqual(split.bot_admin_users, ["ou_a", "ou_b"])

        # 两个开关的 bool 解析口径并不相同，这里把差异固定住：
        # BOT_ENABLED 走 .lower() == 'true'（大小写不敏感，但 '1' / 'yes' 不算开启），
        # FEISHU_SEND_AS_FILE 走 in ('true', '1', 'yes')。
        self.assertFalse(self._build_config({"BOT_ENABLED": "false"}).bot_enabled)
        self.assertFalse(self._build_config({"BOT_ENABLED": "1"}).bot_enabled)
        self.assertTrue(self._build_config({"BOT_ENABLED": "TRUE"}).bot_enabled)
        self.assertTrue(self._build_config({"FEISHU_SEND_AS_FILE": "1"}).feishu_send_as_file)

    def test_schema_response_includes_p3_fields(self) -> None:
        schema = build_schema_response()
        notification = next(
            (cat for cat in schema["categories"] if cat["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification, "notification category missing")
        field_keys = {field["key"] for field in notification["fields"]}
        for key in self._FIELD_KEYS:
            self.assertIn(key, field_keys)
