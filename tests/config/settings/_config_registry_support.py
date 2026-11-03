# -*- coding: utf-8 -*-
# 本文件主要测试：测试配置注册表相关功能
"""Tests for config_registry field definitions and schema building.

Ensures every notification channel that has a sender implementation also
has its config keys registered in _FIELD_DEFINITIONS so the Web settings
page and /api/v1/system/config/schema can expose them.
"""
import re
import unittest
from tests.support.paths import get_repo_root

from src.config.registry import (
    SCHEMA_VERSION,
    WEB_SETTINGS_HIDDEN_FROM_UI,
    WEB_SETTINGS_LEGACY_ALIASES,
    WEB_SETTINGS_PENDING_EXPOSURE,
    WEB_SETTINGS_UNREGISTERED_KEYS,
    build_schema_response,
    get_field_definition,
    get_registered_field_keys,
)


# 设置页卡片标题 / 描述走前端中文表（systemConfigI18n.ts 的 fieldTitleMap /
# fieldDescriptionMap），未命中时回退到后端英文 title/description。下面这批
# 字段在本轮配置批次之前就没有中文条目，属于已登记的存量飘移（中文界面
# 会看到英文卡片）。把它固定成只能收缩的 backlog：新批次注册字段时必须同时
# 补中文标题与描述，不得再往这里加名字。
_ZH_UI_LOCALIZATION_BACKLOG = frozenset({
    "AGENT_SKILL_CONCURRENCY", "ALPHASIFT_ENABLED", "ALPHASIFT_INSTALL_SPEC", "ALPHAVANTAGE_API_KEY",
    "ANTHROPIC_API_KEY", "ANTHROPIC_API_KEYS", "ANTHROPIC_MAX_TOKENS", "ANTHROPIC_MODEL",
    "ANTHROPIC_TEMPERATURE", "CODESEARCH_DATA_SOURCE", "CODESEARCH_FALLBACK_ENABLED",
    "CODESEARCH_SOURCE_PRIORITY", "DEEPSEEK_API_KEYS", "FEISHU_CHAT_ID", "FEISHU_DOMAIN",
    "FEISHU_RECEIVE_ID_TYPE", "FINNHUB_API_KEY", "GEMINI_API_KEYS", "GEMINI_MODEL_FALLBACK",
    "KLINE_DATA_SOURCE", "KLINE_FALLBACK_ENABLED", "KLINE_SOURCE_PRIORITY", "LIMITPOOL_DATA_SOURCE",
    "LIMITPOOL_FALLBACK_ENABLED", "LIMITPOOL_SOURCE_PRIORITY", "LONGBRIDGE_ACCESS_TOKEN",
    "LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_OAUTH_CLIENT_ID", "NEWSNOW_BASE_URL",
    "NEWS_INTEL_AUTO_FETCH_ENABLED", "NEWS_INTEL_FETCH_TIMEOUT_SEC", "NEWS_INTEL_MAX_ITEMS_PER_SOURCE",
    "NEWS_INTEL_RETENTION_DAYS", "OPENAI_API_KEYS", "OPENAI_TEMPERATURE", "OPENAI_VISION_MODEL",
    "SECTOR_DATA_SOURCE", "SECTOR_FALLBACK_ENABLED", "SECTOR_SOURCE_PRIORITY", "SOCIAL_SENTIMENT_API_KEY",
    "SOCIAL_SENTIMENT_API_URL", "STOCKDB_BASE_URL", "STOCKDB_CACHE_TTL_SEC", "STOCKDB_COOLDOWN_SEC",
    "STOCKDB_ENABLED", "STOCKDB_MAX_ROWS", "STOCKDB_TIMEOUT_MS", "STOCKINFO_DATA_SOURCE",
    "STOCKINFO_FALLBACK_ENABLED", "STOCKINFO_SOURCE_PRIORITY", "STOCKSDK_BRIDGE_ENTRY", "STOCKSDK_ENABLED",
    "STOCKSDK_KLINE_FALLBACK", "STOCKSDK_NODE_BIN", "STOCKSDK_RATE_LIMIT_RPS", "STOCKSDK_TIMEOUT_MS",
    "WALLSTREETCN_CALENDAR_BASE_URL", "WALLSTREETCN_CALENDAR_ENABLED",
    "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE", "WALLSTREETCN_CALENDAR_TIMEOUT", "WSCN_LIVE_NEWS_BASE_URL",
    "WSCN_LIVE_NEWS_DEFAULT_LIMIT", "WSCN_LIVE_NEWS_ENABLED", "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
    "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC", "WSCN_LIVE_NEWS_IMPORTANT_SCORE", "WSCN_LIVE_NEWS_TIMEOUT_SEC",
})


class _TestSlackFieldsRegisteredFixture:
    """Slack config keys must be present in the registry."""
    _SLACK_KEYS = ("SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID", "SLACK_WEBHOOK_URL")


class _TestFeishuWebhookFieldsRegisteredFixture:
    """Feishu webhook security fields must be registered for the settings UI."""
    _FEISHU_KEYS = (
        "FEISHU_WEBHOOK_URL",
        "FEISHU_WEBHOOK_SECRET",
        "FEISHU_WEBHOOK_KEYWORD",
    )


class _TestAstrBotFieldsRegisteredFixture:
    """AstrBot config keys must be explicitly registered for settings UI."""
    _ASTRBOT_KEYS = ("ASTRBOT_URL", "ASTRBOT_TOKEN")


class _TestSettingsHelpMetadataFixture:
    """Field help metadata should be available for covered settings help slices."""
    _AI_MODEL_HIDDEN_KEYS = {
        "LLM_CHANNELS",
        "LLM_TEMPERATURE",
        "LITELLM_MODEL",
        "AGENT_LITELLM_MODEL",
        "LITELLM_FALLBACK_MODELS",
        "AIHUBMIX_KEY",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEYS",
        "GEMINI_API_KEY",
        "GEMINI_API_KEYS",
        "GEMINI_MODEL",
        "GEMINI_MODEL_FALLBACK",
        "GEMINI_TEMPERATURE",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_API_KEYS",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_TEMPERATURE",
        "ANTHROPIC_MAX_TOKENS",
        "OPENAI_API_KEY",
        "OPENAI_API_KEYS",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OPENAI_VISION_MODEL",
        "OPENAI_TEMPERATURE",
        "VISION_MODEL",
    }
    _SYSTEM_HIDDEN_KEYS = {
        "ADMIN_AUTH_ENABLED",
    }
    _HELP_KEYS = (
        "STOCK_LIST",
        "GENERATION_BACKEND",
        "GENERATION_FALLBACK_BACKEND",
        "LITELLM_MODEL",
        "LLM_CHANNELS",
        "FEISHU_WEBHOOK_URL",
        "WEBUI_HOST",
        "AGENT_GENERATION_BACKEND",
        "AGENT_LITELLM_MODEL",
        "LITELLM_FALLBACK_MODELS",
        "TUSHARE_TOKEN",
        "REALTIME_SOURCE_PRIORITY",
        "TAVILY_API_KEYS",
        "NEWS_STRATEGY_PROFILE",
        "WECHAT_WEBHOOK_URL",
        "EMAIL_RECEIVERS",
        "SCHEDULE_TIME",
        "ADMIN_AUTH_ENABLED",
        # PR3 Phase 1: Agent + Event Alert
        "AGENT_MODE",
        "AGENT_MAX_STEPS",
        "AGENT_SKILLS",
        "AGENT_SKILL_DIR",
        "AGENT_NL_ROUTING",
        "AGENT_ARCH",
        "AGENT_ORCHESTRATOR_MODE",
        "AGENT_ORCHESTRATOR_TIMEOUT_S",
        "AGENT_SKILL_CONCURRENCY",
        "AGENT_RISK_OVERRIDE",
        "AGENT_DEEP_RESEARCH_BUDGET",
        "AGENT_DEEP_RESEARCH_TIMEOUT",
        "AGENT_MEMORY_ENABLED",
        "AGENT_SKILL_AUTOWEIGHT",
        "AGENT_SKILL_ROUTING",
        "AGENT_CONTEXT_COMPRESSION_ENABLED",
        "AGENT_CONTEXT_COMPRESSION_PROFILE",
        "AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS",
        "AGENT_CONTEXT_PROTECTED_TURNS",
        "AGENT_EVENT_MONITOR_ENABLED",
        "AGENT_EVENT_MONITOR_INTERVAL_MINUTES",
        "AGENT_EVENT_ALERT_RULES_JSON",
        # PR3 Phase 2: Backtest
        "BACKTEST_ENABLED",
        "BACKTEST_EVAL_WINDOW_DAYS",
        "BACKTEST_MIN_AGE_DAYS",
        "BACKTEST_ENGINE_VERSION",
        "BACKTEST_NEUTRAL_BAND_PCT",
        # PR3 Phase 3: Report + Notification Route
        "REPORT_SUMMARY_ONLY",
        "REPORT_SHOW_LLM_MODEL",
        "REPORT_TEMPLATES_DIR",
        "REPORT_RENDERER_ENABLED",
        "REPORT_INTEGRITY_ENABLED",
        "REPORT_INTEGRITY_RETRY",
        "REPORT_HISTORY_COMPARE_N",
        "SINGLE_STOCK_NOTIFY",
        "MERGE_EMAIL_NOTIFICATION",
        "NOTIFICATION_REPORT_CHANNELS",
        "NOTIFICATION_ALERT_CHANNELS",
        "NOTIFICATION_SYSTEM_ERROR_CHANNELS",
        "NOTIFICATION_DEDUP_TTL_SECONDS",
        "NOTIFICATION_COOLDOWN_SECONDS",
        "NOTIFICATION_QUIET_HOURS",
        "NOTIFICATION_TIMEZONE",
        "NOTIFICATION_MIN_SEVERITY",
        "NOTIFICATION_DAILY_DIGEST_ENABLED",
        # PR3 Phase 4: System Runtime
        "LOG_LEVEL",
        "DEBUG",
        "MAX_WORKERS",
        "ANALYSIS_DELAY",
        "SAVE_CONTEXT_SNAPSHOT",
        "MARKET_REVIEW_ENABLED",
        "DAILY_MARKET_CONTEXT_ENABLED",
        "MARKET_REVIEW_REGION",
        "MARKET_REVIEW_COLOR_SCHEME",
        # Issue #1512: stream, log, and WebUI startup fields
        "DINGTALK_STREAM_ENABLED",
        "FEISHU_STREAM_ENABLED",
        "LOG_DIR",
        "WEBUI_ENABLED",
        "WEBUI_AUTO_BUILD",
    )


class _TestIssue1512SettingsFieldsFixture:
    """Issue #1512 visible fields must be explicitly registered."""


class _TestEnvExampleWebSettingsCoverageFixture:
    """Active .env.example keys must be registered or explicitly declared."""
    _ENV_EXAMPLE = get_repo_root() / ".env.example"
    _ACTIVE_ENV_ASSIGNMENT_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=")


class _TestUnregisteredConfigKeysDeclaredFixture:
    """``src/config/settings.py`` reads must be registered or declared as non-UI keys.

    Web settings only render registered fields. Without this guard a new
    ``os.getenv`` call silently becomes an invisible configuration knob:
    visible in ``.env`` but impossible to edit from the settings page.
    """
    _ROOT = get_repo_root()
    _CONFIG_PY = _ROOT / "src/config/settings.py"
    _ENV_EXAMPLE = _ROOT / ".env.example"
    _ENV_READ_RE = re.compile(
        r"os\.(?:getenv|environ\.get)\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']"
    )
    _ENV_ASSIGNMENT_RE = re.compile(r"^#?\s*([A-Z][A-Z0-9_]*)=")
    @classmethod
    def _config_read_keys(cls) -> set[str]:
        return set(cls._ENV_READ_RE.findall(cls._CONFIG_PY.read_text(encoding="utf-8")))
    @classmethod
    def _env_example_keys(cls) -> set[str]:
        return {
            match.group(1)
            for line in cls._ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
            for match in [cls._ENV_ASSIGNMENT_RE.match(line.strip())]
            if match
        }


class _TestSettingsHelpContractFixture:
    """Help keys must map to registry metadata or be editor-only.

    The LLM Channel editor uses internal field-level keys prefixed with
    ``settings.llm_channel.``. Those keys are valid for UI only and should not be
    expected in the backend registry.
    """
    _LLM_CHANNEL_HELP_PREFIX = "settings.llm_channel."
    _SETTINGS_HELP_FILE = get_repo_root() / "apps/hrs-web/src/locales/settingsHelp.ts"
    @classmethod
    def _collect_registry_help_keys(cls) -> set[str]:
        keys = set()
        for key in get_registered_field_keys():
            definition = get_field_definition(key)
            help_key = definition.get("help_key")
            if help_key:
                keys.add(help_key)
        return keys
    @classmethod
    def _collect_locale_help_keys(cls) -> set[str]:
        content = cls._SETTINGS_HELP_FILE.read_text(encoding="utf-8")
        return set(re.findall(r"^\s*'([^']+)'\s*:\s*\{", content, flags=re.MULTILINE))


class _TestSensitiveFieldsUsePasswordControlFixture:
    """Every is_sensitive field must use ui_control='password' to avoid
    leaking secrets in the Web settings page."""


class _TestNotificationRouteFieldsRegisteredFixture:
    """P3 notification route keys must be visible and validated in settings schema."""
    _ROUTE_KEYS = (
        "NOTIFICATION_REPORT_CHANNELS",
        "NOTIFICATION_ALERT_CHANNELS",
        "NOTIFICATION_SYSTEM_ERROR_CHANNELS",
    )


class _TestAgentEventAlertRulesJsonFieldFixture:
    """Event Monitor legacy JSON config must advertise its P8 boundary."""


class _TestAgentContextCompressionFieldsFixture:
    """Visible chat context compression config must be exposed consistently."""


class _TestNotificationNoiseFieldsRegisteredFixture:
    """P4 notification noise-control keys must be visible in settings schema."""
    _NOISE_KEYS = (
        "NOTIFICATION_DEDUP_TTL_SECONDS",
        "NOTIFICATION_COOLDOWN_SECONDS",
        "NOTIFICATION_QUIET_HOURS",
        "NOTIFICATION_TIMEZONE",
        "NOTIFICATION_MIN_SEVERITY",
        "NOTIFICATION_DAILY_DIGEST_ENABLED",
    )


class _TestReportDisplayFieldsRegisteredFixture:
    """Report display toggles should be visible in settings schema."""


class _TestMarketReviewFieldsRegisteredFixture:
    """Market review behavior toggles should be visible in settings schema."""


class _TestDingTalkWebhookFieldsRegisteredFixture:
    """DingTalk group robot fields follow the visible settings contract."""


class _TestRegistryDefaultsMatchRuntimeFixture:
    """registry.default_value 必须反映无环境变量时 Config 的真实默认值。

    Web 设置页用 default_value 展示“未配置时的默认行为”，两套定义长期分叉
    会让用户看到与实际运行不一致的默认值。这里以 Config（运行时唯一真源）
    为基准做机械比对。

    例外：以下字段的默认值由其他配置推导，registry 用空串表示“跟随运行时”，
    因此不参与字面比对：

    - AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS / AGENT_CONTEXT_PROTECTED_TURNS
      —— 由压缩档位预设推导；
    - SCHEDULE_TIMES —— 为空时回退 SCHEDULE_TIME；
    - AGENT_SKILL_DIR —— 为空时使用内置 strategies/ 目录。
    """
    _DERIVED_DEFAULT_KEYS = frozenset({
        "AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS",
        "AGENT_CONTEXT_PROTECTED_TURNS",
        "AGENT_SKILL_DIR",
        "SCHEDULE_TIMES",
    })
    @staticmethod
    def _runtime_defaults():
        import os
        from dataclasses import fields
        from unittest.mock import patch

        from src.config import Config

        # 隔离本机环境与 .env：ENV_FILE 指向不存在的路径，其余配置键全部清空。
        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        with patch.dict(os.environ, preserved, clear=True):
            config = Config()
        return {field.name: getattr(config, field.name) for field in fields(config)}


class _TestP1DataSourceFieldsRegisteredFixture:
    """P1 批次：外部行情凭证与板块 / 涨跌停池路由必须是正式注册字段。

    Sector / limit-pool routing mirrors the KLINE_* family. The option list must
    track the sources actually registered in each manager, otherwise the settings
    page offers values that never resolve.
    """
    _ROUTING_KEYS = (
        "SECTOR_DATA_SOURCE",
        "SECTOR_FALLBACK_ENABLED",
        "SECTOR_SOURCE_PRIORITY",
        "LIMITPOOL_DATA_SOURCE",
        "LIMITPOOL_FALLBACK_ENABLED",
        "LIMITPOOL_SOURCE_PRIORITY",
    )
    _CREDENTIAL_KEYS = (
        "ALPHAVANTAGE_API_KEY",
        "FINNHUB_API_KEY",
        "LONGBRIDGE_APP_KEY",
        "LONGBRIDGE_APP_SECRET",
        "LONGBRIDGE_ACCESS_TOKEN",
        "LONGBRIDGE_OAUTH_CLIENT_ID",
        "SOCIAL_SENTIMENT_API_KEY",
    )
    _RUNTIME_DEFAULTS = {
        "SECTOR_DATA_SOURCE": "auto",
        "SECTOR_FALLBACK_ENABLED": "true",
        "SECTOR_SOURCE_PRIORITY": "eastmoney",
        "LIMITPOOL_DATA_SOURCE": "auto",
        "LIMITPOOL_FALLBACK_ENABLED": "true",
        "LIMITPOOL_SOURCE_PRIORITY": "eastmoney",
        "SOCIAL_SENTIMENT_API_URL": "https://api.adanos.org",
    }


class _TestP2NewsFieldsRegisteredFixture:
    """P2 批次：资讯源（快讯 / 财经日历 / 本地资讯池 / NewsNow）必须是正式注册字段。

    这批字段此前只能改 `.env`，而它们直接决定「行情资讯」页面是否有数据。
    除注册形态外，这里额外绑定两件容易漂移的事：

    * 数值字段的 `validation.min/max` 必须与 `parse_env_int/parse_env_float` 的
      收敛边界一致——否则设置页会接受一个运行时被静默 clamp 的值；
    * URL 字段的默认值必须与运行时去尾斜杠后的结果一致。
    """
    _FIELD_KEYS = (
        "WSCN_LIVE_NEWS_ENABLED",
        "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC",
        "WSCN_LIVE_NEWS_IMPORTANT_SCORE",
        "WSCN_LIVE_NEWS_DEFAULT_LIMIT",
        "WSCN_LIVE_NEWS_TIMEOUT_SEC",
        "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
        "WSCN_LIVE_NEWS_BASE_URL",
        "WALLSTREETCN_CALENDAR_ENABLED",
        "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE",
        "WALLSTREETCN_CALENDAR_TIMEOUT",
        "WALLSTREETCN_CALENDAR_BASE_URL",
        "NEWS_INTEL_AUTO_FETCH_ENABLED",
        "NEWS_INTEL_RETENTION_DAYS",
        "NEWS_INTEL_MAX_ITEMS_PER_SOURCE",
        "NEWS_INTEL_FETCH_TIMEOUT_SEC",
        "NEWSNOW_BASE_URL",
    )
    _BOOLEAN_KEYS = (
        "WSCN_LIVE_NEWS_ENABLED",
        "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
        "WALLSTREETCN_CALENDAR_ENABLED",
        "NEWS_INTEL_AUTO_FETCH_ENABLED",
    )
    _NUMERIC_BOUNDS = {
        "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC": (0, 86400),
        "WSCN_LIVE_NEWS_IMPORTANT_SCORE": (1, 10),
        "WSCN_LIVE_NEWS_DEFAULT_LIMIT": (1, 100),
        "WSCN_LIVE_NEWS_TIMEOUT_SEC": (1.0, 30.0),
        "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE": (0, 10),
        "WALLSTREETCN_CALENDAR_TIMEOUT": (1.0, 30.0),
        "NEWS_INTEL_RETENTION_DAYS": (1, 365),
        "NEWS_INTEL_MAX_ITEMS_PER_SOURCE": (1, 200),
        "NEWS_INTEL_FETCH_TIMEOUT_SEC": (1.0, 30.0),
    }
    _HELP_KEY_GROUPS = {
        "settings.data_source.live_news": (
            "WSCN_LIVE_NEWS_ENABLED",
            "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC",
            "WSCN_LIVE_NEWS_IMPORTANT_SCORE",
            "WSCN_LIVE_NEWS_DEFAULT_LIMIT",
            "WSCN_LIVE_NEWS_TIMEOUT_SEC",
            "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
            "WSCN_LIVE_NEWS_BASE_URL",
        ),
        "settings.data_source.live_calendar": (
            "WALLSTREETCN_CALENDAR_ENABLED",
            "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE",
            "WALLSTREETCN_CALENDAR_TIMEOUT",
            "WALLSTREETCN_CALENDAR_BASE_URL",
        ),
        "settings.data_source.news_intel": (
            "NEWS_INTEL_AUTO_FETCH_ENABLED",
            "NEWS_INTEL_RETENTION_DAYS",
            "NEWS_INTEL_MAX_ITEMS_PER_SOURCE",
            "NEWS_INTEL_FETCH_TIMEOUT_SEC",
        ),
        "settings.data_source.newsnow": ("NEWSNOW_BASE_URL",),
    }
    _URL_DEFAULTS = {
        "WSCN_LIVE_NEWS_BASE_URL": "https://api-one.wallstcn.com",
        "WALLSTREETCN_CALENDAR_BASE_URL": "https://api-one-wscn.awtmt.com",
        "NEWSNOW_BASE_URL": "https://newsnow.busiyi.world",
    }
    @staticmethod
    def _build_config(overrides: dict):
        """在清空环境变量（`.env` 指向不存在路径）的前提下从环境变量构建 Config。

        注意：必须走 ``_load_from_env()``，它是环境变量解析入口；直接 ``Config()``
        只会拿到 dataclass 静态默认值，无法验证 clamp / 去尾斜杠行为。
        """
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()


class _TestP3BotFieldsRegisteredFixture:
    """批次 P3：机器人与飞书事件订阅字段必须是正式注册字段。

    这一批的判定标准不是“键属于通知分类”，而是“运行时存在读取方”：
    每个注册键都要能在 ``src/config/settings.py`` 之外找到消费它的代码。

    因此这里同时锁定三件事：

    * 已注册字段的形态、help_key 分组与默认值；
    * 重启边界（分发器单例 / Stream 建连时读取的键标 restart_required，
      按请求或按通知实例读取的键不标）；
    * 无读取方的键不得注册，只能留在 pending 声明表里。
    """
    _FIELD_KEYS = (
        "BOT_ENABLED",
        "BOT_COMMAND_PREFIX",
        "BOT_ADMIN_USERS",
        "FEISHU_VERIFICATION_TOKEN",
        "FEISHU_ENCRYPT_KEY",
        "FEISHU_MAX_BYTES",
        "FEISHU_SEND_AS_FILE",
        "FEISHU_FOLDER_TOKEN",
        "EMAIL_SENDER_NAME",
    )
    _DISPLAY_ORDERS = {
        "BOT_ENABLED": 71,
        "BOT_COMMAND_PREFIX": 72,
        "BOT_ADMIN_USERS": 73,
        "FEISHU_VERIFICATION_TOKEN": 74,
        "FEISHU_ENCRYPT_KEY": 75,
        "FEISHU_MAX_BYTES": 76,
        "FEISHU_SEND_AS_FILE": 77,
        "FEISHU_FOLDER_TOKEN": 78,
        "EMAIL_SENDER_NAME": 79,
    }
    _HELP_KEY_GROUPS = {
        "settings.notification.bot_runtime": (
            "BOT_ENABLED",
            "BOT_COMMAND_PREFIX",
            "BOT_ADMIN_USERS",
        ),
        "settings.notification.feishu_event_security": (
            "FEISHU_VERIFICATION_TOKEN",
            "FEISHU_ENCRYPT_KEY",
        ),
        "settings.notification.feishu_delivery": (
            "FEISHU_MAX_BYTES",
            "FEISHU_SEND_AS_FILE",
            "FEISHU_FOLDER_TOKEN",
        ),
    }
    _CREDENTIAL_KEYS = ("FEISHU_VERIFICATION_TOKEN", "FEISHU_ENCRYPT_KEY")
    _RESTART_BOUNDARY_KEYS = (
        "BOT_COMMAND_PREFIX",
        "BOT_ADMIN_USERS",
        "FEISHU_VERIFICATION_TOKEN",
        "FEISHU_ENCRYPT_KEY",
    )
    _HOT_RELOAD_KEYS = (
        "BOT_ENABLED",
        "FEISHU_MAX_BYTES",
        "FEISHU_SEND_AS_FILE",
        "FEISHU_FOLDER_TOKEN",
        "EMAIL_SENDER_NAME",
    )
    _NO_CONSUMER_KEYS = (
        "WECOM_CORPID",
        "WECOM_TOKEN",
        "WECOM_ENCODING_AES_KEY",
        "WECOM_AGENT_ID",
        "TELEGRAM_WEBHOOK_SECRET",
        "DISCORD_BOT_STATUS",
    )
    _ROOT = get_repo_root()
    @staticmethod
    def _build_config(overrides: dict):
        """从环境变量构建 Config，隔离本机 `.env`。

        必须走 ``_load_from_env()``：直接 ``Config()`` 只拿 dataclass 静态默认值，
        看不到列表切分、bool 解析和数值 clamp。
        """
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()


class _TestP4PortfolioRiskFieldsRegisteredFixture:
    """批次 P4：组合与风险字段必须是正式注册字段。

    沿用 P3 的入库标准：只注册“运行时确有读取方”的键。这 6 个键在
    ``src/config/settings.py`` 之外全部有消费代码：阈值与窗口由
    ``PortfolioRiskService.get_risk_report()`` 组装，开关由
    ``PortfolioService.refresh_fx_rates()`` 读取。

    这批字段与 P3 的区别在于“不只是展示默认值”：阈值会进入风险报告并参与
    持仓告警规则的触发判定，所以这里额外把接近阈值的乘法语义固定住。
    """
    _RISK_KEYS = (
        "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT",
        "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT",
        "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT",
        "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO",
        "PORTFOLIO_RISK_LOOKBACK_DAYS",
    )
    _FX_KEY = "PORTFOLIO_FX_UPDATE_ENABLED"
    _FIELD_KEYS = _RISK_KEYS + (_FX_KEY,)
    _DISPLAY_ORDERS = {
        "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT": 60,
        "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT": 61,
        "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT": 62,
        "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO": 63,
        "PORTFOLIO_RISK_LOOKBACK_DAYS": 64,
        "PORTFOLIO_FX_UPDATE_ENABLED": 65,
    }
    _NUMERIC_BOUNDS = {
        "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT": 0.0,
        "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT": 0.0,
        "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT": 0.0,
        "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO": 0.0,
        "PORTFOLIO_RISK_LOOKBACK_DAYS": 1,
    }
    _ROOT = get_repo_root()
    @staticmethod
    def _build_config(overrides: dict):
        """从环境变量构建 Config，隔离本机 `.env`。

        必须走 ``_load_from_env()``：直接 ``Config()`` 只拿 dataclass 静态默认值，
        看不到数值 clamp 和 bool 解析。
        """
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()


class _TestP5ReportImageAndWechatFormFieldsRegisteredFixture:
    """批次 P5：报告转图片与企业微信消息形态字段必须是正式注册字段。

    入库标准沿用 P3/P4：只注册运行时确有读取方的键。本批 5 个键的读取点
    全部在实例构造或调用时：转图三键由 ``NotificationService.__init__`` / 每次
    转图调用（``src/infrastructure/reporting/img_render.py``）读取，企业微信两键由 ``WechatSender.__init__``
    读取，因此不标 ``restart_required``。

    同批故意不入库的两个 Vision 键另有原因（归属冲突 / 无行为读取方），下面
    把它们停在 pending 固定下来，避免下一批“顺手注册”。
    """
    _MD2IMG_KEYS = (
        "MARKDOWN_TO_IMAGE_CHANNELS",
        "MARKDOWN_TO_IMAGE_MAX_CHARS",
        "MD2IMG_ENGINE",
    )
    _WECHAT_KEYS = (
        "WECHAT_MSG_TYPE",
        "WECHAT_MAX_BYTES",
    )
    _FIELD_KEYS = _WECHAT_KEYS + _MD2IMG_KEYS
    _DISPLAY_ORDERS = {
        "WECHAT_MSG_TYPE": 80,
        "WECHAT_MAX_BYTES": 81,
        "MARKDOWN_TO_IMAGE_CHANNELS": 82,
        "MARKDOWN_TO_IMAGE_MAX_CHARS": 83,
        "MD2IMG_ENGINE": 84,
    }
    _NUMERIC_BOUNDS = {
        "WECHAT_MAX_BYTES": 1,
        "MARKDOWN_TO_IMAGE_MAX_CHARS": 1,
    }
    _SELECT_OPTIONS = {
        "WECHAT_MSG_TYPE": ["markdown", "text"],
        "MD2IMG_ENGINE": ["wkhtmltoimage", "markdown-to-file"],
    }
    _REMAINING_PENDING = ("VISION_MODEL", "VISION_PROVIDER_PRIORITY")
    _ROOT = get_repo_root()
    @staticmethod
    def _build_config(overrides: dict):
        """从环境变量构建 Config，隔离本机 `.env`。

        必须走 ``_load_from_env()``：直接 ``Config()`` 只拿 dataclass 静态默认值，
        看不到“WECHAT_MAX_BYTES 默认值跟随消息类型”这类解析分支。
        """
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()


class _TestP6LlmChannelSwitchStaysPendingFixture:
    """批次 P6 结论：`LLM_ANSPIRE_ENABLED` 不入库，继续留在 pending。

    它不是“还没来得及注册的普通开关”，而是两个条件同时命中：
    1. 写入归属已被「LLM 渠道编辑器」接管：前端把 `LLM_<渠道>_ENABLED` 当编辑器
       草稿命名空间（`isLlmChannelEditorDraftKey` 对任何 `LLM_` 前缀都返回 true），
       编辑器自己负责读回与写回；再注册就是和 P5 的 `VISION_MODEL` 同类的一键两面。
    2. 它只在 `LLM_CHANNELS` 里真的有个名叫 `anspire` 的渠道时才影响行为（已由
       `Config._load_from_env()` 实测）；其他情况下注册等于开放一个默认无效开关。
    """
    _KEY = "LLM_ANSPIRE_ENABLED"
    _EDITOR_OWNED_PENDING = ("VISION_MODEL", "VISION_PROVIDER_PRIORITY", "LLM_ANSPIRE_ENABLED")
    _ROOT = get_repo_root()
    _ANSPIRE_KEY = "akey12345678"
    @staticmethod
    def _build_config(overrides: dict):
        """从环境变量构建 Config，隔离本机 `.env`（同批次 P5 口径）。"""
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()
    def _settings_page_source(self) -> str:
        return (self._ROOT / "apps/hrs-web/src/pages/SettingsPage.tsx").read_text(encoding="utf-8")


class _TestWebUiFieldLocalizationCoverageFixture:
    """每个已注册字段必须在前端中文表里，或在只能收缩的存量名单里。"""
    _ROOT = get_repo_root()
    _I18N_TS = _ROOT / "apps/hrs-web/src/utils/systemConfigI18n.ts"
    _MAP_NAMES = ("fieldTitleMap", "fieldDescriptionMap")
    def _localized_keys(self, map_name: str) -> set:
        """抽取 ``const <map_name>: Record<...> = {...}`` 的顶层键。

        只匹配块内两空格缩进的 ``KEY:`` 行，避免把嵌套的选项标签当成字段名。
        """
        source = self._I18N_TS.read_text(encoding="utf-8")
        start = source.index(f"const {map_name}")
        end = source.index("\n};", start)
        return set(re.findall(r"^  ([A-Z0-9_]+):", source[start:end], re.M))

