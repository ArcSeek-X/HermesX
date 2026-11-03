"""Tests for config registry notifications."""

from tests.config.settings._config_registry_support import (
    WEB_SETTINGS_HIDDEN_FROM_UI,
    WEB_SETTINGS_PENDING_EXPOSURE,
    _TestAstrBotFieldsRegisteredFixture,
    _TestDingTalkWebhookFieldsRegisteredFixture,
    _TestFeishuWebhookFieldsRegisteredFixture,
    _TestNotificationNoiseFieldsRegisteredFixture,
    _TestNotificationRouteFieldsRegisteredFixture,
    _TestP5ReportImageAndWechatFormFieldsRegisteredFixture,
    _TestSlackFieldsRegisteredFixture,
    build_schema_response,
    get_field_definition,
    get_registered_field_keys,
    unittest,
)


class TestSlackFieldsRegistered(_TestSlackFieldsRegisteredFixture, unittest.TestCase):
    def test_field_definitions_exist(self):
        for key in self._SLACK_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertNotEqual(
                field["display_order"], 9000,
                f"{key} should be explicitly registered, not inferred",
            )

    def test_bot_token_is_sensitive(self):
        field = get_field_definition("SLACK_BOT_TOKEN")
        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")

    def test_webhook_url_is_sensitive(self):
        field = get_field_definition("SLACK_WEBHOOK_URL")
        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")

    def test_channel_id_not_sensitive(self):
        field = get_field_definition("SLACK_CHANNEL_ID")
        self.assertFalse(field["is_sensitive"])

    def test_schema_response_includes_slack(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._SLACK_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")

    def test_display_order_between_discord_and_pushover(self):
        discord = get_field_definition("DISCORD_MAIN_CHANNEL_ID")
        pushover = get_field_definition("PUSHOVER_USER_KEY")
        for key in self._SLACK_KEYS:
            order = get_field_definition(key)["display_order"]
            self.assertGreater(order, discord["display_order"],
                               f"{key} should appear after Discord")
            self.assertLess(order, pushover["display_order"],
                            f"{key} should appear before Pushover")


class TestFeishuWebhookFieldsRegistered(_TestFeishuWebhookFieldsRegisteredFixture, unittest.TestCase):
    def test_field_definitions_exist(self):
        for key in self._FEISHU_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertNotEqual(
                field["display_order"], 9000,
                f"{key} should be explicitly registered, not inferred",
            )

    def test_secret_is_sensitive(self):
        field = get_field_definition("FEISHU_WEBHOOK_SECRET")
        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")

    def test_keyword_is_not_sensitive(self):
        field = get_field_definition("FEISHU_WEBHOOK_KEYWORD")
        self.assertFalse(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "text")

    def test_webhook_url_uses_url_validation(self):
        field = get_field_definition("FEISHU_WEBHOOK_URL")
        self.assertEqual(field["validation"]["item_type"], "url")
        self.assertIn("https", field["validation"]["allowed_schemes"])

    def test_schema_response_includes_feishu_webhook_fields(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._FEISHU_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")


class TestAstrBotFieldsRegistered(_TestAstrBotFieldsRegisteredFixture, unittest.TestCase):
    def test_field_definitions_exist(self):
        for key in self._ASTRBOT_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertNotEqual(
                field["display_order"], 9000,
                f"{key} should be explicitly registered, not inferred",
            )

    def test_url_and_token_are_sensitive_password_controls(self):
        for key in self._ASTRBOT_KEYS:
            field = get_field_definition(key)
            self.assertTrue(field["is_sensitive"], f"{key} should be sensitive")
            self.assertEqual(field["ui_control"], "password")

    def test_url_uses_url_validation(self):
        field = get_field_definition("ASTRBOT_URL")
        self.assertEqual(field["validation"]["item_type"], "url")
        self.assertIn("https", field["validation"]["allowed_schemes"])

    def test_schema_response_includes_astrbot_fields(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._ASTRBOT_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")


class TestDiscordInteractionPublicKeyField(unittest.TestCase):
    def test_field_definition_exists(self):
        field = get_field_definition("DISCORD_INTERACTIONS_PUBLIC_KEY")
        self.assertEqual(field["category"], "notification")
        self.assertFalse(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "text")

    def test_schema_response_includes_public_key_field(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        self.assertIn("DISCORD_INTERACTIONS_PUBLIC_KEY", field_keys)


class TestNotificationRouteFieldsRegistered(_TestNotificationRouteFieldsRegisteredFixture, unittest.TestCase):
    def test_field_definitions_exist(self):
        for key in self._ROUTE_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertEqual(field["data_type"], "array", f"{key} data_type")
            self.assertFalse(field["is_sensitive"], f"{key} should not be sensitive")
            self.assertIn("email", field["validation"]["allowed_values"])

    def test_schema_response_includes_route_fields(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._ROUTE_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")


class TestNotificationNoiseFieldsRegistered(_TestNotificationNoiseFieldsRegisteredFixture, unittest.TestCase):
    def test_field_definitions_exist(self):
        for key in self._NOISE_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertFalse(field["is_sensitive"], f"{key} should not be sensitive")
            self.assertFalse(field["is_required"], f"{key} should not be required")

        self.assertEqual(get_field_definition("NOTIFICATION_DEDUP_TTL_SECONDS")["data_type"], "integer")
        self.assertEqual(get_field_definition("NOTIFICATION_COOLDOWN_SECONDS")["data_type"], "integer")
        self.assertEqual(get_field_definition("NOTIFICATION_DAILY_DIGEST_ENABLED")["data_type"], "boolean")
        min_severity = get_field_definition("NOTIFICATION_MIN_SEVERITY")
        self.assertEqual(min_severity["options"][0]["value"], "")
        self.assertIn("", min_severity["validation"]["enum"])
        self.assertIn("warning", min_severity["validation"]["enum"])

    def test_schema_response_includes_noise_fields(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._NOISE_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")


class TestDingTalkWebhookFieldsRegistered(_TestDingTalkWebhookFieldsRegisteredFixture, unittest.TestCase):
    def test_dingtalk_webhook_fields_are_visible_sensitive_and_documented(self):
        expected = {
            "DINGTALK_WEBHOOK_URL": "settings.notification.DINGTALK_WEBHOOK_URL",
            "DINGTALK_SECRET": "settings.notification.DINGTALK_SECRET",
        }
        for key, help_key in expected.items():
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification")
            self.assertEqual(field["ui_control"], "password")
            self.assertTrue(field["is_sensitive"])
            self.assertEqual(field["help_key"], help_key)
            self.assertTrue(field["examples"])
            self.assertTrue(field["docs"])
            self.assertNotIn(key, WEB_SETTINGS_HIDDEN_FROM_UI)

    def test_dingtalk_webhook_url_has_url_validation(self):
        field = get_field_definition("DINGTALK_WEBHOOK_URL")
        self.assertEqual(field["validation"]["item_type"], "url")
        self.assertEqual(field["validation"]["allowed_schemes"], ["http", "https"])

    def test_schema_response_includes_dingtalk_webhook_fields(self):
        schema = build_schema_response()
        notification = next(
            category
            for category in schema["categories"]
            if category["category"] == "notification"
        )
        fields = {field["key"]: field for field in notification["fields"]}
        self.assertIn("DINGTALK_WEBHOOK_URL", fields)
        self.assertIn("DINGTALK_SECRET", fields)
        self.assertEqual(
            fields["DINGTALK_WEBHOOK_URL"]["help_key"],
            "settings.notification.DINGTALK_WEBHOOK_URL",
        )


class TestP5ReportImageAndWechatFormFieldsRegistered(_TestP5ReportImageAndWechatFormFieldsRegisteredFixture, unittest.TestCase):
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
            self.assertNotIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 注册后必须从 pending 表移除")
            self.assertIn(key, registered, key)

    def test_help_keys_grouped_by_capability(self) -> None:
        """两个能力各自一个 help_key，不塞进已有的飞书 / 聊天机器人组。"""
        for key in self._WECHAT_KEYS:
            self.assertEqual(
                get_field_definition(key)["help_key"],
                "settings.notification.wechat_delivery",
                key,
            )
        for key in self._MD2IMG_KEYS:
            self.assertEqual(
                get_field_definition(key)["help_key"],
                "settings.notification.markdown_to_image",
                key,
            )

    def test_select_options_match_runtime_accepted_values(self) -> None:
        """下拉选项是运行时的取值集，且保存校验会拿到自动补齐的 enum。"""
        for key, values in self._SELECT_OPTIONS.items():
            field = get_field_definition(key)
            self.assertEqual(field["ui_control"], "select", key)
            self.assertEqual(field["data_type"], "string", key)
            self.assertEqual([option["value"] for option in field["options"]], values, key)
            self.assertEqual(field["validation"]["enum"], values, f"{key} 的 enum 应由 options 自动派生")

    def test_numeric_bounds_match_runtime_clamping(self) -> None:
        for key, minimum in self._NUMERIC_BOUNDS.items():
            validation = get_field_definition(key)["validation"]
            self.assertEqual(float(validation["min"]), float(minimum), key)
            self.assertNotIn("max", validation, f"{key} 运行时不收上限，registry 不得多写 max")

        clamped = self._build_config(
            {"WECHAT_MAX_BYTES": "0", "MARKDOWN_TO_IMAGE_MAX_CHARS": "-1"}
        )
        self.assertEqual(clamped.wechat_max_bytes, 1)
        self.assertEqual(clamped.markdown_to_image_max_chars, 1)

    def test_defaults_match_runtime_parsing(self) -> None:
        config = self._build_config({})
        self.assertEqual(config.wechat_msg_type, "markdown")
        self.assertEqual(config.wechat_max_bytes, 4000)
        self.assertEqual(config.markdown_to_image_channels, [])
        self.assertEqual(config.markdown_to_image_max_chars, 15000)
        self.assertEqual(config.md2img_engine, "wkhtmltoimage")
        for key, expected in (
            ("WECHAT_MSG_TYPE", "markdown"),
            ("WECHAT_MAX_BYTES", "4000"),
            ("MARKDOWN_TO_IMAGE_CHANNELS", ""),
            ("MARKDOWN_TO_IMAGE_MAX_CHARS", "15000"),
            ("MD2IMG_ENGINE", "wkhtmltoimage"),
        ):
            self.assertEqual(get_field_definition(key)["default_value"], expected, key)

    def test_runtime_parsing_semantics_locked(self) -> None:
        """把注册文案声称的四个解析行为固定成用例，防止文案与实现分叉。

        1. WECHAT_MAX_BYTES 不填时默认值跟消息类型走（text 2048）；
        2. text 模式下发送侧还会把上限压到 2000 字节；
        3. 消息类型只做大写归一，引擎非法值回落 wkhtmltoimage；
        4. 渠道列表会去空、去空白并转小写。
        """
        self.assertEqual(self._build_config({"WECHAT_MSG_TYPE": "text"}).wechat_max_bytes, 2048)
        self.assertEqual(
            self._build_config({"WECHAT_MSG_TYPE": "TEXT", "WECHAT_MAX_BYTES": "3000"}).wechat_max_bytes,
            3000,
        )
        self.assertEqual(self._build_config({"WECHAT_MSG_TYPE": "TEXT"}).wechat_msg_type, "text")
        # 非法值不报错也不直接取 2048 以外的默认：发送侧把非 markdown 归为 markdown 行为。
        self.assertEqual(self._build_config({"WECHAT_MSG_TYPE": "news"}).wechat_msg_type, "news")
        self.assertEqual(self._build_config({"MD2IMG_ENGINE": "puppeteer"}).md2img_engine, "wkhtmltoimage")
        self.assertEqual(
            self._build_config({"MARKDOWN_TO_IMAGE_CHANNELS": " Telegram , WECHAT ,,"}).markdown_to_image_channels,
            ["telegram", "wechat"],
        )

        from src.infrastructure.notification.senders.wechat_sender import WechatSender

        sender = WechatSender(
            self._build_config(
                {
                    "WECHAT_WEBHOOK_URL": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
                    "WECHAT_MSG_TYPE": "text",
                    "WECHAT_MAX_BYTES": "9000",
                }
            )
        )
        captured: list = []

        def _capture(content, **kwargs):
            captured.append(content)
            return True

        sender._send_wechat_message = _capture
        long_content = "\n\n".join(f"### 股票 {index}\n\n{'内容' * 40}\n\n---" for index in range(40))
        self.assertTrue(sender.send_to_wechat(long_content))
        # 发送时刻的硬约束：text 下取 min(配置值, 2000)，因此配置写 9000
        # 也不会让分片突破 2000 字节（企业微信 text 单条限 2048）。
        self.assertGreater(len(captured), 1)
        for chunk in captured:
            self.assertLessEqual(len(chunk.encode("utf-8")), 2000)

        markdown_sender = WechatSender(
            self._build_config(
                {
                    "WECHAT_WEBHOOK_URL": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
                    "WECHAT_MAX_BYTES": "9000",
                }
            )
        )
        markdown_chunks: list = []
        markdown_sender._send_wechat_message = lambda content, **kwargs: (markdown_chunks.append(content), True)[1]
        markdown_sender._send_wechat_chunked = lambda content, max_bytes: (markdown_chunks.append(max_bytes), True)[1]
        self.assertTrue(markdown_sender.send_to_wechat(long_content))
        # 同样配置下 markdown 不叠加 2000 约束，直接用配置值分批。
        self.assertEqual(markdown_chunks, [9000])

    def test_fields_are_consumed_at_runtime(self) -> None:
        """注册的不是死键：五个属性在运行时代码里确有读取方。"""
        notification_source = (self._ROOT / "src/application/notification/notification.py").read_text(encoding="utf-8")
        self.assertIn("getattr(config, 'markdown_to_image_channels', [])", notification_source)
        self.assertIn("config, 'markdown_to_image_max_chars', 15000", notification_source)

        md2img_source = (self._ROOT / "src/infrastructure/reporting/img_render.py").read_text(encoding="utf-8")
        self.assertIn('getattr(get_config(), "md2img_engine"', md2img_source)

        wechat_source = (
            self._ROOT / "src/infrastructure/notification/senders/wechat_sender.py"
        ).read_text(encoding="utf-8")
        self.assertIn("getattr(config, 'wechat_max_bytes', 4000)", wechat_source)
        self.assertIn("getattr(config, 'wechat_msg_type', 'markdown')", wechat_source)

    def test_fields_take_effect_without_restart(self) -> None:
        """读取时刻是实例构造 / 按调用，且通知服务不缓存单例。"""
        for key in self._FIELD_KEYS:
            self.assertNotIn(
                "restart_required",
                get_field_definition(key).get("warning_codes", []),
                f"{key} 不需要重启，不该提醒用户重启",
            )

        # 下面的“不重启”只在通知服务每次新建时成立：若将来改成模块级单例
        # 或依赖注入缓存，这条断言会失败，提醒同步补 restart_required。
        notification_source = (self._ROOT / "src/application/notification/notification.py").read_text(encoding="utf-8")
        self.assertIn("    return NotificationService()", notification_source)
        self.assertNotIn("_notification_service_instance", notification_source)

    def test_remaining_vision_keys_stay_pending(self) -> None:
        """本批故意不入库的两个 Vision 键必须留在 pending，且仍未注册。

        VISION_MODEL 的写入归属在「AI 模型接入」通道编辑器，注册会变成一键两面；
        VISION_PROVIDER_PRIORITY 除 `Config.validate()` 的告警文案外无行为读取方。
        两者都要先定调才能入库，不得在后续批次里直接当普通卡片注册。
        """
        registered = set(get_registered_field_keys())
        for key in self._REMAINING_PENDING:
            self.assertIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 应仍在 pending 表")
            self.assertEqual(WEB_SETTINGS_PENDING_EXPOSURE[key], "P5", key)
            self.assertNotIn(key, registered, f"{key} 归属/行为未定，不得先注册")
        # 归属冲突不会因为“注册了”而自然消失：通用卡片列表仍只按隐藏集过滤。
        settings_source = (self._ROOT / "apps/hrs-web/src/pages/SettingsPage.tsx").read_text(encoding="utf-8")
        self.assertIn("VISION_MODEL", settings_source)

    def test_schema_response_includes_p5_fields(self) -> None:
        schema = build_schema_response()
        notification = next(
            (cat for cat in schema["categories"] if cat["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification, "notification category missing")
        fields = notification["fields"]
        field_keys = {field["key"] for field in fields}
        for key in self._FIELD_KEYS:
            self.assertIn(key, field_keys)
        # 本批字段排在 notification 分类末尾，不打乱已有渠道/机器人字段顺序。
        p5_orders = [field["display_order"] for field in fields if field["key"] in self._FIELD_KEYS]
        legacy_orders = [
            field["display_order"]
            for field in fields
            if field["key"] not in self._FIELD_KEYS
        ]
        self.assertGreaterEqual(min(p5_orders), max(legacy_orders))
        # 下拉选项随 schema 下发，前端才能渲染中文标签。
        for key, values in self._SELECT_OPTIONS.items():
            field = next(item for item in fields if item["key"] == key)
            self.assertEqual([option["value"] for option in field["options"]], values, key)
