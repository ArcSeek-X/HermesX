"""Tests for config registry defaults."""

from tests.config.settings._config_registry_support import (
    WEB_SETTINGS_HIDDEN_FROM_UI,
    WEB_SETTINGS_LEGACY_ALIASES,
    WEB_SETTINGS_PENDING_EXPOSURE,
    WEB_SETTINGS_UNREGISTERED_KEYS,
    _TestEnvExampleWebSettingsCoverageFixture,
    _TestRegistryDefaultsMatchRuntimeFixture,
    _TestUnregisteredConfigKeysDeclaredFixture,
    get_field_definition,
    get_registered_field_keys,
    unittest,
)


class TestEnvExampleWebSettingsCoverage(_TestEnvExampleWebSettingsCoverageFixture, unittest.TestCase):
    def test_active_env_example_keys_are_registered_or_hidden_from_web_ui(self) -> None:
        active_keys = {
            match.group(1)
            for line in self._ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
            for match in [self._ACTIVE_ENV_ASSIGNMENT_RE.match(line.strip())]
            if match
        }
        registered_keys = set(get_registered_field_keys())

        self.assertEqual(
            sorted(active_keys - registered_keys - WEB_SETTINGS_UNREGISTERED_KEYS),
            [],
        )


class TestUnregisteredConfigKeysDeclared(_TestUnregisteredConfigKeysDeclaredFixture, unittest.TestCase):
    def test_config_reads_are_registered_or_declared(self) -> None:
        undeclared = sorted(
            self._config_read_keys()
            - set(get_registered_field_keys())
            - WEB_SETTINGS_UNREGISTERED_KEYS
        )
        self.assertEqual(
            undeclared,
            [],
            "src/config/settings.py 读取了未声明的配置键。请二选一：在 _FIELD_DEFINITIONS 中注册"
            "（会出现在 Web 设置页），或登记到 WEB_SETTINGS_HIDDEN_FROM_UI / "
            "WEB_SETTINGS_PENDING_EXPOSURE / WEB_SETTINGS_LEGACY_ALIASES。",
        )

    def test_declarations_do_not_overlap_registry(self) -> None:
        registered = set(get_registered_field_keys())
        for name, keys in (
            ("WEB_SETTINGS_HIDDEN_FROM_UI", WEB_SETTINGS_HIDDEN_FROM_UI),
            ("WEB_SETTINGS_PENDING_EXPOSURE", set(WEB_SETTINGS_PENDING_EXPOSURE)),
            ("WEB_SETTINGS_LEGACY_ALIASES", set(WEB_SETTINGS_LEGACY_ALIASES)),
        ):
            self.assertEqual(
                sorted(keys & registered),
                [],
                f"{name} 与 _FIELD_DEFINITIONS 重叠：注册后必须从声明表中移除。",
            )

    def test_declaration_tables_are_mutually_exclusive(self) -> None:
        tables = {
            "hidden": WEB_SETTINGS_HIDDEN_FROM_UI,
            "pending": set(WEB_SETTINGS_PENDING_EXPOSURE),
            "legacy": set(WEB_SETTINGS_LEGACY_ALIASES),
        }
        names = sorted(tables)
        for index, left in enumerate(names):
            for right in names[index + 1:]:
                self.assertEqual(
                    sorted(tables[left] & tables[right]),
                    [],
                    f"{left} 与 {right} 不得重复登记同一个键。",
                )

    def test_declared_keys_exist_in_config_or_env_example(self) -> None:
        config_keys = self._config_read_keys()
        env_keys = self._env_example_keys()
        for name, keys in (
            ("WEB_SETTINGS_HIDDEN_FROM_UI", WEB_SETTINGS_HIDDEN_FROM_UI),
            ("WEB_SETTINGS_PENDING_EXPOSURE", set(WEB_SETTINGS_PENDING_EXPOSURE)),
            ("WEB_SETTINGS_LEGACY_ALIASES", set(WEB_SETTINGS_LEGACY_ALIASES)),
        ):
            stale = sorted(keys - config_keys - env_keys)
            self.assertEqual(
                stale,
                [],
                f"{name} 中存在已失效的键（src/config/settings.py 和 .env.example 都不再出现）：{stale}",
            )

    def test_legacy_aliases_point_to_registered_keys(self) -> None:
        registered = set(get_registered_field_keys())
        broken = sorted(
            alias
            for alias, canonical in WEB_SETTINGS_LEGACY_ALIASES.items()
            if canonical not in registered
        )
        self.assertEqual(
            broken,
            [],
            "legacy 别名必须指向已注册的 canonical 键，否则设置页会失去唯一入口。",
        )


class TestRegistryDefaultsMatchRuntime(_TestRegistryDefaultsMatchRuntimeFixture, unittest.TestCase):
    def test_registry_defaults_match_runtime(self) -> None:
        runtime = self._runtime_defaults()
        mismatches = []
        for key in get_registered_field_keys():
            if key in self._DERIVED_DEFAULT_KEYS:
                continue
            attribute = key.lower()
            if attribute not in runtime:
                continue
            expected = get_field_definition(key).get("default_value")
            if expected is None:
                continue

            actual = runtime[attribute]
            if isinstance(actual, bool):
                actual_text = "true" if actual else "false"
            elif isinstance(actual, (list, tuple)):
                actual_text = ",".join(str(item) for item in actual)
            elif actual is None:
                actual_text = ""
            else:
                actual_text = str(actual)

            if actual_text == str(expected):
                continue
            try:
                if float(actual_text) == float(expected):
                    continue
            except ValueError:
                pass
            mismatches.append((key, str(expected), actual_text))

        self.assertEqual(
            [],
            mismatches,
            "registry default_value 与 Config 运行时默认值不一致："
            f"{mismatches}",
        )
