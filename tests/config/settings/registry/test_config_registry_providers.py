"""Tests for config registry providers."""

from tests.config.settings._config_registry_support import (
    WEB_SETTINGS_UNREGISTERED_KEYS,
    _TestP1DataSourceFieldsRegisteredFixture,
    _TestP2NewsFieldsRegisteredFixture,
    get_field_definition,
    unittest,
)


class TestP1DataSourceFieldsRegistered(_TestP1DataSourceFieldsRegisteredFixture, unittest.TestCase):
    def test_fields_are_explicitly_registered(self) -> None:
        keys = self._ROUTING_KEYS + self._CREDENTIAL_KEYS + ("SOCIAL_SENTIMENT_API_URL",)
        for key in keys:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "data_source", key)
            self.assertNotEqual(
                field["display_order"],
                9000,
                f"{key} 必须是 _FIELD_DEFINITIONS 中的正式字段，不能依赖自动推断",
            )
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")

    def test_credential_fields_use_password_and_are_sensitive(self) -> None:
        for key in self._CREDENTIAL_KEYS:
            field = get_field_definition(key)
            self.assertTrue(field["is_sensitive"], key)
            self.assertEqual(field["ui_control"], "password", key)

    def test_routing_defaults_match_runtime(self) -> None:
        # 默认值必须与 src/config/settings.py 中对应的 os.getenv 回退值一致。
        for key, expected in self._RUNTIME_DEFAULTS.items():
            self.assertEqual(get_field_definition(key)["default_value"], expected, key)

    def test_routing_options_match_registered_sources(self) -> None:
        # 以 data_provider/{sector,limit_pool}/base.py 的 _build_sources() 为唯一事实源。
        from data_provider.limit_pool.base import _build_sources as build_limit_pool_sources
        from data_provider.sector.base import _build_sources as build_sector_sources

        for key, builder in (
            ("SECTOR_DATA_SOURCE", build_sector_sources),
            ("LIMITPOOL_DATA_SOURCE", build_limit_pool_sources),
        ):
            registered_sources = set(builder().keys())
            option_values = {
                option["value"] for option in get_field_definition(key)["options"]
            } - {"auto"}
            self.assertEqual(
                option_values,
                registered_sources,
                f"{key} 的 options 必须与该数据源管理器真实注册的 source 一致",
            )


class TestP2NewsFieldsRegistered(_TestP2NewsFieldsRegisteredFixture, unittest.TestCase):
    def test_fields_are_explicitly_registered(self) -> None:
        declared = WEB_SETTINGS_UNREGISTERED_KEYS
        for key in self._FIELD_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "data_source", key)
            self.assertNotEqual(
                field["display_order"],
                9000,
                f"{key} 必须是 _FIELD_DEFINITIONS 中的正式字段，不能依赖自动推断",
            )
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")
            self.assertNotIn(key, declared, f"{key} 注册后必须从声明表移除")

    def test_help_keys_grouped_by_capability(self) -> None:
        for help_key, keys in self._HELP_KEY_GROUPS.items():
            for key in keys:
                self.assertEqual(
                    get_field_definition(key)["help_key"],
                    help_key,
                    f"{key} 的 help_key 应与同族字段一致",
                )

    def test_boolean_fields_use_switch_control(self) -> None:
        for key in self._BOOLEAN_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["data_type"], "boolean", key)
            self.assertEqual(field["ui_control"], "switch", key)
            self.assertIn(field["default_value"], ("true", "false"), key)

    def test_numeric_bounds_match_runtime_clamping(self) -> None:
        # parse_env_int/parse_env_float 会对越界值做 clamp；设置页的 min/max
        # 必须与之一致，否则用户保存的值会在运行时被静默改写。
        for key, (low, high) in self._NUMERIC_BOUNDS.items():
            validation = get_field_definition(key)["validation"]
            self.assertEqual(float(validation["min"]), float(low), f"{key}.min")
            self.assertEqual(float(validation["max"]), float(high), f"{key}.max")

            attribute = key.lower()
            overflow = self._build_config({key: str(high * 3 + 100)})
            self.assertEqual(
                float(getattr(overflow, attribute)), float(high),
                f"{key} 超过上限时运行时应 clamp 到 registry max",
            )
            underflow = self._build_config({key: str(low - 100)})
            self.assertEqual(
                float(getattr(underflow, attribute)), float(low),
                f"{key} 低于下限时运行时应 clamp 到 registry min",
            )

    def test_url_fields_strip_trailing_slash(self) -> None:
        for key, expected in self._URL_DEFAULTS.items():
            self.assertEqual(get_field_definition(key)["default_value"], expected, key)
            # 运行时会对末尾斜杠做 rstrip，填 https://host// 后应归一为 https://host
            config = self._build_config({key: "https://example.com//"})
            self.assertEqual(getattr(config, key.lower()), "https://example.com", key)
