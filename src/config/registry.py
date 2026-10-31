# -*- coding: utf-8 -*-
"""Configuration field metadata registry.

字段声明数据与帮助文案已拆到 ``src.config.field_definitions`` 与
``src.config.field_help``（W5.3）；本模块保留分类元数据、可见性表，以及
把两者装配成 Web 设置页 schema 的查询逻辑。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Set

from src.config.field_definitions import FIELD_DEFINITIONS
from src.config.field_help import FIELD_HELP_METADATA

SCHEMA_VERSION = "2026-06-29-claude-code-cli-backend"

_CATEGORY_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "category": "base",
        "title": "Base Settings",
        "description": "Watchlist and foundational application settings.",
        "display_order": 10,
    },
    {
        "category": "ai_model",
        "title": "AI Model",
        "description": "Model providers, model names, and inference parameters.",
        "display_order": 20,
    },
    {
        "category": "data_source",
        "title": "Data Source",
        "description": "Market data provider credentials and priority settings.",
        "display_order": 30,
    },
    {
        "category": "notification",
        "title": "Notification",
        "description": "Bot, webhook, and push channel related settings.",
        "display_order": 40,
    },
    {
        "category": "system",
        "title": "System",
        "description": "Runtime and scheduling controls.",
        "display_order": 50,
    },
    {
        "category": "agent",
        "title": "Agent",
        "description": "Agent mode and strategy-skill settings.",
        "display_order": 55,
    },
    {
        "category": "backtest",
        "title": "Backtest",
        "description": "Backtest engine behavior and evaluation parameters.",
        "display_order": 60,
    },
    {
        "category": "uncategorized",
        "title": "Uncategorized",
        "description": "Keys not mapped in the field registry.",
        "display_order": 99,
    },
]

WEB_SETTINGS_HIDDEN_FROM_UI: Set[str] = {
    # 数据落盘与 SQLite 调优：改错会改变数据库位置或写入行为，由部署侧统一管理。
    "DATABASE_PATH",
    "ENV_FILE",
    "SQLITE_WAL_ENABLED",
    "SQLITE_BUSY_TIMEOUT_MS",
    "SQLITE_WRITE_RETRY_MAX",
    "SQLITE_WRITE_RETRY_BASE_DELAY",
    # 网络代理：进程级出口配置，通常由容器或宿主机注入。
    "USE_PROXY",
    "PROXY_HOST",
    "PROXY_PORT",
    "HTTPS_PROXY",
    "NO_PROXY",
    # 模型调用重试与限速：属于运行时编排参数，需配合具体 provider 行为调整。
    "GEMINI_MAX_RETRIES",
    "GEMINI_REQUEST_DELAY",
    "GEMINI_RETRY_DELAY",
    # 子 Agent 超时：内部编排调优，会随 Agent 架构变化。
    "AGENT_DECISION_AGENT_TIMEOUT_S",
    "AGENT_INTEL_AGENT_TIMEOUT_S",
    "AGENT_PORTFOLIO_AGENT_TIMEOUT_S",
    "AGENT_RISK_AGENT_TIMEOUT_S",
    "AGENT_SKILL_AGENT_TIMEOUT_S",
    "AGENT_TECHNICAL_AGENT_TIMEOUT_S",
    # 基本面管道：抓取超时、重试与缓存参数，需要与数据源策略一起评估。
    "FUNDAMENTAL_CACHE_MAX_ENTRIES",
    "FUNDAMENTAL_CACHE_TTL_SECONDS",
    "FUNDAMENTAL_FETCH_TIMEOUT_SECONDS",
    "FUNDAMENTAL_RETRY_MAX",
    "FUNDAMENTAL_STAGE_TIMEOUT_SECONDS",
    # 缓存与熔断：内部性能保护参数，误调会放大数据源压力或降低新鲜度。
    "CALENDAR_COUNTRIES_CACHE_TTL",
    "CIRCUIT_BREAKER_COOLDOWN",
    "PREFETCH_REALTIME_QUOTES",
    "REALTIME_CACHE_TTL",
    # 启动期与实验性开关：修改后必须重启，且可能改变进程退出行为。
    "CONFIG_VALIDATE_MODE",
    "ENABLE_EASTMONEY_PATCH",
    "ENABLE_FUNDAMENTAL_PIPELINE",
    # Bot 运行时保护：限流与消息分段阈值，属于内部防刷策略。
    "BOT_RATE_LIMIT_REQUESTS",
    "BOT_RATE_LIMIT_WINDOW",
    "DISCORD_MAX_WORDS",
}

# Web 设置页可见性契约
#
# 设置页只渲染 _FIELD_DEFINITIONS 中注册的字段：build_schema_response() 只遍历
# 该字典，system_config_service._get_schema_config_keys() 也只按注册键组装接口返回。
# 因此“未注册”等价于“设置页不可见、不可改”，这些键仍可通过 .env 文件、配置
# 导入导出或部署环境变量维护。
#
# 为避免 config.py 新增读取键后静默变成“隐形配置”，未注册键必须登记到下面三张表
# 之一，并由 tests/test_config_registry.py 强制校验。三张表与 _FIELD_DEFINITIONS
# 互不相交；某个键正式注册后，必须同时从表中移除，否则测试会失败。
WEB_SETTINGS_PENDING_EXPOSURE: Dict[str, str] = {
    # P1 数据源凭证与路由（LONGBRIDGE_* / SECTOR_* / LIMITPOOL_* /
    # ALPHAVANTAGE / FINNHUB / SOCIAL_SENTIMENT_*）已注册到 _FIELD_DEFINITIONS。
    # P2 资讯源（WSCN_LIVE_NEWS_* / WALLSTREETCN_CALENDAR_* / NEWS_INTEL_* /
    # NEWSNOW_BASE_URL）已注册到 _FIELD_DEFINITIONS。
    # P3 通知与机器人：有运行时读取方的 9 个键（BOT_* / 飞书事件订阅与发送形态 /
    # EMAIL_SENDER_NAME）已注册到 _FIELD_DEFINITIONS。
    # P4 组合与风险：运行时确有读取方的 6 个键（风险阈值 / 回撤窗口 / 汇率刷新
    # 开关）已注册到 _FIELD_DEFINITIONS。
    #
    # 以下 6 个键不能在后续批次里“顺手注册”：企业微信和 Telegram 平台还没有实现
    # （bot/platforms/ 下无对应适配器，DISCORD_BOT_STATUS 全仓无读取方），注册后
    # 只会得到“设置页能填、保存了没人读”的字段。等对应平台落地并接上 Config
    # 读取路径后，再随该平台的接入批次注册。
    "DISCORD_BOT_STATUS": "P3",
    "TELEGRAM_WEBHOOK_SECRET": "P3",
    "WECOM_AGENT_ID": "P3",
    "WECOM_CORPID": "P3",
    "WECOM_ENCODING_AES_KEY": "P3",
    "WECOM_TOKEN": "P3",
    # P5 视觉与图片渲染：确有运行时读取方的 5 个键（报告转图片三键 + 企业微信
    # 消息形态两键）已注册到 _FIELD_DEFINITIONS。
    #
    # 剩下两个 Vision 键不随本批入库，原因不同但都不能直接当普通卡片开放：
    # - VISION_MODEL：它已由「AI 模型接入」分类的通道编辑器卡片接管（该卡片把它
    #   写回 LiteLLM 通道配置）。而通用卡片列表只按隐藏集过滤、不排除编辑器托管键，
    #   所以一旦注册就会在同一页出现两个编辑入口、两处都能写，先定归属才能入库。
    # - VISION_PROVIDER_PRIORITY：运行时唯一读取点是 `Config.validate()` 的告警范围
    #   （决定除主模型自身 provider 外还提醒哪些 provider 缺 Key），真正的 Vision
    #   provider 推断顺序是硬编码的 gemini → anthropic → openai，与调用失败时的重试
    #   行为都不受该键影响。专题文档此前描述不准确（写的是“按已配 key 的 provider
    #   依次尝试/自动切换”），已在本批次修正 `docs/full-guide.md`、`docs/LLM_CONFIG_GUIDE.md`、
    #   `docs/LLM_CONFIG_GUIDE_EN.md` 三处，使其与代码事实一致。漂移消除后，该键仍不入库：
    #   保存一个不影响行为的值是偏差设计，需先定调是否要实现真正的可配置优先级才能入库。
    "VISION_MODEL": "P5",
    "VISION_PROVIDER_PRIORITY": "P5",
    # P6 LLM 渠道开关：勘察后结论是“不入库”，不是“下次再补”。两个条件同时命中：
    # - 写入归属已被「LLM 渠道编辑器」接管：前端把任何 `LLM_` 前缀的键当编辑器
    #   草稿命名空间（SettingsPage.tsx 的 isLlmChannelEditorDraftKey），本键还直接
    #   匹配 `LLM_<渠道>_ENABLED` 正则；编辑器自己按渠道名读回并写回该键（
    #   LLMChannelEditor.tsx）。再注册就是和 VISION_MODEL 同类的一键两面，而且
    #   ai_model 分类在已配渠道时还会把这张卡片静默过滤掉，“注册 = 可编辑”不成立。
    # - 行为读取有条件：只有 `LLM_CHANNELS` 里真有个名叫 anspire 的渠道时才会
    #   改变解析结果（settings.py 的渠道循环内才读它）；其余情况下它是一个怎么拨
    #   都不生效的开关，违反批次 P3 确立的“运行时确有读取方”入库标准。
    # 由 tests/test_config_registry.py::TestP6LlmChannelSwitchStaysPending 锁定。先定
    # 编辑器与通用卡片的归属，再评估是否入库。
    "LLM_ANSPIRE_ENABLED": "P6",
}

# 新旧键名并存时的兼容别名：config.py 先读新键，再回退到这里的旧键。
# 旧键不再作为独立配置项展示，值到 canonical 键，便于后续清理。
WEB_SETTINGS_LEGACY_ALIASES: Dict[str, str] = {
    "AGENT_STRATEGY_AUTOWEIGHT": "AGENT_SKILL_AUTOWEIGHT",
    "AGENT_STRATEGY_ROUTING": "AGENT_SKILL_ROUTING",
    "AGENT_STRATEGY_DIR": "AGENT_SKILL_DIR",
    "DISCORD_CHANNEL_ID": "DISCORD_MAIN_CHANNEL_ID",
}

# 全部未注册运行时键的并集，供守卫测试与 .env.example 覆盖校验使用。
WEB_SETTINGS_UNREGISTERED_KEYS: Set[str] = (
    WEB_SETTINGS_HIDDEN_FROM_UI
    | set(WEB_SETTINGS_PENDING_EXPOSURE)
    | set(WEB_SETTINGS_LEGACY_ALIASES)
)


# W5.3：字段声明与帮助文案已分别拆到 src.config.field_definitions / field_help，
# 本模块只保留分类元数据、可见性表与查询/装配逻辑。


def get_category_definitions() -> List[Dict[str, Any]]:
    """Return deep-copied category metadata."""
    return deepcopy(_CATEGORY_DEFINITIONS)


def get_registered_field_keys() -> List[str]:
    """Return all explicitly registered keys."""
    return list(FIELD_DEFINITIONS.keys())


def _extract_option_values(options: List[Any]) -> List[str]:
    """Extract canonical option values from string/object style select options."""
    values: List[str] = []
    for option in options:
        if isinstance(option, str):
            values.append(option)
            continue
        if isinstance(option, dict):
            value = option.get("value")
            if isinstance(value, str) and value:
                values.append(value)
    return values


def get_field_definition(key: str, value_hint: Optional[str] = None) -> Dict[str, Any]:
    """Return field definition for key, including inferred fallback metadata."""
    key_upper = key.upper()
    if key_upper in FIELD_DEFINITIONS:
        field = deepcopy(FIELD_DEFINITIONS[key_upper])
        if key_upper in FIELD_HELP_METADATA:
            field.update(deepcopy(FIELD_HELP_METADATA[key_upper]))
        field["key"] = key_upper
        validation = deepcopy(field.get("validation") or {})
        option_values = _extract_option_values(field.get("options", []))
        if field.get("ui_control") == "select" and option_values and "enum" not in validation:
            validation["enum"] = option_values
        field["validation"] = validation
        return field

    category = _infer_category(key_upper)
    data_type = _infer_data_type(key_upper, value_hint)
    field = {
        "key": key_upper,
        "title": key_upper.replace("_", " ").title(),
        "description": "Auto-inferred field metadata.",
        "category": category,
        "data_type": data_type,
        "ui_control": _infer_ui_control(data_type, key_upper),
        "is_sensitive": _is_sensitive_key(key_upper),
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 9000,
    }
    return field


def build_schema_response() -> Dict[str, Any]:
    """Build schema payload grouped by category."""
    category_map: Dict[str, Dict[str, Any]] = {}
    for category in get_category_definitions():
        category_map[category["category"]] = {**category, "fields": []}

    for key in sorted(FIELD_DEFINITIONS.keys()):
        field = get_field_definition(key)
        category_map[field["category"]]["fields"].append(field)

    categories = sorted(category_map.values(), key=lambda item: item["display_order"])
    for category in categories:
        category["fields"] = sorted(
            category["fields"],
            key=lambda item: (item.get("display_order", 9999), item["key"]),
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "categories": categories,
    }


def _is_sensitive_key(key: str) -> bool:
    markers = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    return any(marker in key for marker in markers)


def _infer_category(key: str) -> str:
    if key == "STOCK_LIST":
        return "base"
    if key.startswith("BACKTEST_"):
        return "backtest"
    if key.startswith(("GEMINI_", "OPENAI_", "ANTHROPIC_", "LITELLM_", "AIHUBMIX_", "DEEPSEEK_", "LLM_")):
        return "ai_model"
    if key.endswith("_PRIORITY") or key.startswith(
        (
            "TUSHARE",
            "TICKFLOW",
            "AKSHARE",
            "EFINANCE",
            "PYTDX",
            "BAOSTOCK",
            "YFINANCE",
            "TAVILY",
            "SERPAPI",
            "BRAVE",
            "BOCHA",
            "ANSPIRE",
            "SEARXNG",
            "NEWS_",
            "BIAS_",
        )
    ) or key in ("ENABLE_REALTIME_QUOTE", "ENABLE_CHIP_DISTRIBUTION"):
        return "data_source"
    if key.startswith((
        "WECHAT",
        "FEISHU",
        "TELEGRAM",
        "EMAIL",
        "PUSHOVER",
        "NTFY",
        "GOTIFY",
        "PUSHPLUS",
        "SERVERCHAN",
        "DINGTALK",
        "DISCORD",
        "SLACK",
        "CUSTOM_WEBHOOK",
        "WECOM",
        "ASTRBOT",
    )) or "WEBHOOK" in key:
        return "notification"
    if key.startswith(("LOG_", "SCHEDULE_", "WEBUI_", "HTTP_", "HTTPS_", "MAX_", "DEBUG", "MARKET_REVIEW_", "TRADING_DAY_", "ANALYSIS_DELAY")):
        return "system"
    return "uncategorized"


def _infer_data_type(key: str, value_hint: Optional[str]) -> str:
    if key.endswith("_TIME"):
        return "time"
    if value_hint is None:
        return "string"

    lowered = value_hint.strip().lower()
    if lowered in {"true", "false"}:
        return "boolean"

    try:
        int(value_hint)
        return "integer"
    except (TypeError, ValueError):
        pass

    try:
        float(value_hint)
        return "number"
    except (TypeError, ValueError):
        pass

    if key in {"STOCK_LIST", "EMAIL_RECEIVERS", "CUSTOM_WEBHOOK_URLS"}:
        return "array"
    return "string"


def _infer_ui_control(data_type: str, key: str) -> str:
    if _is_sensitive_key(key):
        return "password"
    if data_type == "boolean":
        return "switch"
    if data_type in {"integer", "number"}:
        return "number"
    if data_type == "time":
        return "time"
    if data_type == "array":
        return "textarea"
    return "text"
