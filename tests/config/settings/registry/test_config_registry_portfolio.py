"""Tests for config registry portfolio."""

from tests.config.settings._config_registry_support import (
    WEB_SETTINGS_PENDING_EXPOSURE,
    _TestP4PortfolioRiskFieldsRegisteredFixture,
    build_schema_response,
    get_field_definition,
    get_registered_field_keys,
    unittest,
)


class TestP4PortfolioRiskFieldsRegistered(_TestP4PortfolioRiskFieldsRegisteredFixture, unittest.TestCase):
    def test_fields_are_explicitly_registered(self) -> None:
        registered = set(get_registered_field_keys())
        for key in self._FIELD_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "system", key)
            self.assertEqual(field["display_order"], self._DISPLAY_ORDERS[key], key)
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")
            self.assertTrue(field.get("description"), f"{key} 缺少 description")
            self.assertNotIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 注册后必须从 pending 表移除")
            self.assertIn(key, registered, key)

    def test_no_new_frontend_category_is_introduced(self) -> None:
        """本批复用 system 分类，不新增前端 portfolio 分类。

        前端 SystemConfigCategory 是闭合 union，新增分类要同步改 union、
        icon map 和 3 个 locale 的分类标题。如果将来确实要拆出来，这个断言
        会提醒作者一并处理客户端兼容面。
        """
        schema = build_schema_response()
        self.assertEqual(len(schema["categories"]), 8)
        types_file = (self._ROOT / "apps/hrs-web/src/types/systemConfig.ts").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("'portfolio'", types_file)

    def test_help_keys_grouped_by_capability(self) -> None:
        for key in self._RISK_KEYS:
            self.assertEqual(
                get_field_definition(key)["help_key"],
                "settings.system.portfolio_risk",
                f"{key} 的 help_key 应与同族阈值字段一致",
            )
        # 汇率刷新是独立能力（接口行为而非告警灵敏度），不塞进同一 help_key。
        self.assertEqual(
            get_field_definition(self._FX_KEY)["help_key"],
            "settings.system.portfolio_fx",
        )

    def test_numeric_bounds_match_runtime_clamping(self) -> None:
        for key, minimum in self._NUMERIC_BOUNDS.items():
            validation = get_field_definition(key)["validation"]
            self.assertEqual(float(validation["min"]), float(minimum), key)
            self.assertNotIn("max", validation, f"{key} 运行时不收上限，registry 不得多写 max")

        clamped = self._build_config(
            {
                "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT": "-5",
                "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO": "-1",
                "PORTFOLIO_RISK_LOOKBACK_DAYS": "0",
            }
        )
        self.assertEqual(clamped.portfolio_risk_concentration_alert_pct, 0.0)
        self.assertEqual(clamped.portfolio_risk_stop_loss_near_ratio, 0.0)
        self.assertEqual(clamped.portfolio_risk_lookback_days, 1)

    def test_defaults_match_runtime_parsing(self) -> None:
        config = self._build_config({})
        self.assertEqual(config.portfolio_risk_concentration_alert_pct, 35.0)
        self.assertEqual(config.portfolio_risk_drawdown_alert_pct, 15.0)
        self.assertEqual(config.portfolio_risk_stop_loss_alert_pct, 10.0)
        self.assertEqual(config.portfolio_risk_stop_loss_near_ratio, 0.8)
        self.assertEqual(config.portfolio_risk_lookback_days, 180)
        self.assertTrue(config.portfolio_fx_update_enabled)
        # 本批字段的 registry 默认值单独对一次，不只依赖全局默认值守卫。
        for key, expected in (
            ("PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT", "35.0"),
            ("PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT", "15.0"),
            ("PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT", "10.0"),
            ("PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO", "0.8"),
            ("PORTFOLIO_RISK_LOOKBACK_DAYS", "180"),
            ("PORTFOLIO_FX_UPDATE_ENABLED", "true"),
        ):
            self.assertEqual(get_field_definition(key)["default_value"], expected, key)

        # 开关走 .lower() == 'true'：大小写不敏感，但 '1' / 'yes' 不算开启，
        # 与 FEISHU_SEND_AS_FILE 的口径不同。
        self.assertTrue(self._build_config({"PORTFOLIO_FX_UPDATE_ENABLED": "TRUE"}).portfolio_fx_update_enabled)
        self.assertFalse(self._build_config({"PORTFOLIO_FX_UPDATE_ENABLED": "1"}).portfolio_fx_update_enabled)
        self.assertFalse(self._build_config({"PORTFOLIO_FX_UPDATE_ENABLED": "yes"}).portfolio_fx_update_enabled)

        # 非法数值不会报错，而是回退默认值：设置页不能把错填变成启动失败。
        self.assertEqual(
            self._build_config({"PORTFOLIO_RISK_LOOKBACK_DAYS": "abc"}).portfolio_risk_lookback_days,
            180,
        )

    def test_thresholds_are_consumed_by_risk_report(self) -> None:
        """注册的不是死键：阈值从 Config 进入风险报告，并参与止损接近判定。"""
        source = (self._ROOT / "src/application/portfolio/portfolio_risk_service.py").read_text(encoding="utf-8")
        for attr in (
            "portfolio_risk_concentration_alert_pct",
            "portfolio_risk_drawdown_alert_pct",
            "portfolio_risk_stop_loss_alert_pct",
            "portfolio_risk_stop_loss_near_ratio",
            "portfolio_risk_lookback_days",
        ):
            self.assertIn(f'getattr(self.config, "{attr}"', source, f"{attr} 应仍被风险报告读取")

        snapshot = {
            "accounts": [
                {
                    "account_id": 1,
                    "positions": [
                        {"symbol": "600519", "avg_cost": 100.0, "last_price": 93.0},
                        {"symbol": "000001", "avg_cost": 100.0, "last_price": 91.0},
                    ],
                }
            ]
        }
        thresholds = {
            "stop_loss_alert_pct": 10.0,
            "stop_loss_near_ratio": 0.8,
        }
        from src.application.portfolio.portfolio_risk_service import PortfolioRiskService

        result = PortfolioRiskService._build_stop_loss(snapshot, thresholds)
        # near 阈值 = 10.0 × 0.8 = 8.0：亏 7% 不入选，亏 9% 入选但未跌破。
        self.assertEqual(result["near_count"], 1)
        self.assertEqual(result["triggered_count"], 0)
        self.assertEqual(result["items"][0]["symbol"], "000001")
        self.assertEqual(result["items"][0]["near_threshold_pct"], 8.0)

        tightened = PortfolioRiskService._build_stop_loss(
            snapshot,
            {"stop_loss_alert_pct": 10.0, "stop_loss_near_ratio": 0.5},
        )
        self.assertEqual(tightened["near_count"], 2)

    def test_fields_take_effect_without_restart(self) -> None:
        """读取时刻是按实例构造 / 按调用，保存链路会重置 Config 单例。"""
        for key in self._FIELD_KEYS:
            self.assertNotIn(
                "restart_required",
                get_field_definition(key).get("warning_codes", []),
                f"{key} 不需要重启，不该提醒用户重启",
            )

        # 下面的“不重启”只在风险服务负按请求构造时成立：若将来改成模块级
        # 单例或依赖注入缓存，这条断言会失败，提醒同步补 restart_required。
        endpoint_source = (
            self._ROOT / "api/v1/endpoints/portfolio.py"
        ).read_text(encoding="utf-8")
        self.assertIn("    service = PortfolioRiskService()", endpoint_source)
        risk_source = (
            self._ROOT / "src/application/portfolio/portfolio_risk_service.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("_risk_service_instance", risk_source)
        fx_source = (self._ROOT / "src/application/portfolio/portfolio_service.py").read_text(encoding="utf-8")
        self.assertIn("        config = get_config()", fx_source)

    def test_schema_response_includes_p4_fields(self) -> None:
        schema = build_schema_response()
        system = next(
            (cat for cat in schema["categories"] if cat["category"] == "system"),
            None,
        )
        self.assertIsNotNone(system, "system category missing")
        fields = system["fields"]
        field_keys = {field["key"] for field in fields}
        for key in self._FIELD_KEYS:
            self.assertIn(key, field_keys)
        # 本批字段排在 system 分类末尾，不打乱既有定时/服务/调试字段顺序。
        p4_orders = [field["display_order"] for field in fields if field["key"] in self._FIELD_KEYS]
        legacy_orders = [
            field["display_order"]
            for field in fields
            if field["key"] not in self._FIELD_KEYS
        ]
        self.assertGreaterEqual(min(p4_orders), max(legacy_orders))
