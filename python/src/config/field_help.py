# -*- coding: utf-8 -*-
"""Web 设置页帮助面板文案（W5.3）。

从 ``registry.py`` 拆出的纯声明数据：``help_key`` / ``examples`` / ``docs`` 锚点。
与 ``field_definitions.py`` 的字段声明按 key 合并后渲染帮助面板；文件顶部的
``_DOC_*`` 列表是文档锚点片段，供多个字段复用，改动时注意同步引用者。
"""

from __future__ import annotations

from typing import Any, Dict

_DOC_FULL_GUIDE_ENV = [
    {
        "label": "完整指南：环境变量完整列表",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/full-guide.md#环境变量完整列表",
    },
]

_DOC_FULL_GUIDE_SEARCH = [
    {
        "label": "完整指南：搜索服务配置",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/full-guide.md#搜索服务配置",
    },
]

_DOC_FULL_GUIDE_DATA_SOURCE = [
    {
        "label": "完整指南：数据源配置",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/full-guide.md#数据源配置",
    },
]

_DOC_FULL_GUIDE_NEWS = [
    {
        "label": "完整指南：资讯源配置",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/full-guide.md#资讯源配置",
    },
]

_DOC_FULL_GUIDE_NOTIFICATION = [
    {
        "label": "完整指南：通知渠道配置",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/full-guide.md#通知渠道详细配置",
    },
]

_DOC_FULL_GUIDE_BOT = [
    {
        "label": "完整指南：机器人与事件回调配置",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/full-guide.md#机器人与事件回调配置",
    },
]

_DOC_BOT_COMMAND = [
    {
        "label": "机器人命令与接入说明",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/bot-command.md",
    },
]

_DOC_FEISHU_BOT = [
    {
        "label": "飞书机器人配置专题",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/bot/feishu-bot-config.md",
    },
]

_DOC_LLM_CONFIG = [
    {
        "label": "LLM 配置指南",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/LLM_CONFIG_GUIDE.md",
    },
    {
        "label": "LLM 服务商配置速查",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/llm-providers.md",
    },
]

_DOC_FULL_GUIDE_PORTFOLIO = [
    {
        "label": "完整指南：组合与风险配置",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/full-guide.md#组合与风险配置",
    },
]

_DOC_CUSTOM_WEBHOOK = [
    {
        "label": "完整指南：自定义 Webhook",
        "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/full-guide.md#自定义-webhook",
    },
]

FIELD_HELP_METADATA: Dict[str, Dict[str, Any]] = {
    # ------------------------------------------------------------------
    # 数据源路由与本地桥接字段
    #
    # 这批字段随“统一数据源策略”引入，_FIELD_DEFINITIONS 里已有字段定义，
    # 但 Web 设置页还需要 help_key / examples / docs 才能渲染帮助面板。
    # 为减少重复文案，同一数据源族的字段共用一个 help_key
    # （与既有 settings.data_source.pytdx 的做法一致）。
    # ------------------------------------------------------------------
    "STOCKDB_ENABLED": {
        "help_key": "settings.data_source.stockdb",
        "examples": [
            "STOCKDB_ENABLED=true",
            "STOCKDB_BASE_URL=http://127.0.0.1:7899",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKDB_BASE_URL": {
        "help_key": "settings.data_source.stockdb",
        "examples": [
            "STOCKDB_BASE_URL=http://127.0.0.1:7899",
            "STOCKDB_BASE_URL=http://stockdb.internal:7899",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKDB_TIMEOUT_MS": {
        "help_key": "settings.data_source.stockdb",
        "examples": [
            "STOCKDB_TIMEOUT_MS=5000",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKDB_MAX_ROWS": {
        "help_key": "settings.data_source.stockdb",
        "examples": [
            "STOCKDB_MAX_ROWS=5000",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKDB_CACHE_TTL_SEC": {
        "help_key": "settings.data_source.stockdb",
        "examples": [
            "STOCKDB_CACHE_TTL_SEC=60",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKDB_COOLDOWN_SEC": {
        "help_key": "settings.data_source.stockdb",
        "examples": [
            "STOCKDB_COOLDOWN_SEC=10",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKSDK_ENABLED": {
        "help_key": "settings.data_source.stocksdk",
        "examples": [
            "STOCKSDK_ENABLED=true",
            "STOCKSDK_NODE_BIN=node",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKSDK_NODE_BIN": {
        "help_key": "settings.data_source.stocksdk",
        "examples": [
            "STOCKSDK_NODE_BIN=node",
            "STOCKSDK_NODE_BIN=/usr/local/bin/node",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKSDK_BRIDGE_ENTRY": {
        "help_key": "settings.data_source.stocksdk",
        "examples": [
            "STOCKSDK_BRIDGE_ENTRY=scripts/stocksdk_bridge/bridge.mjs",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKSDK_TIMEOUT_MS": {
        "help_key": "settings.data_source.stocksdk",
        "examples": [
            "STOCKSDK_TIMEOUT_MS=8000",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKSDK_RATE_LIMIT_RPS": {
        "help_key": "settings.data_source.stocksdk",
        "examples": [
            "STOCKSDK_RATE_LIMIT_RPS=3",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKSDK_KLINE_FALLBACK": {
        "help_key": "settings.data_source.stocksdk",
        "examples": [
            "STOCKSDK_KLINE_FALLBACK=true",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "KLINE_DATA_SOURCE": {
        "help_key": "settings.data_source.kline_routing",
        "examples": [
            "KLINE_DATA_SOURCE=auto",
            "KLINE_DATA_SOURCE=eastmoney",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "KLINE_FALLBACK_ENABLED": {
        "help_key": "settings.data_source.kline_routing",
        "examples": [
            "KLINE_FALLBACK_ENABLED=true",
            "KLINE_SOURCE_PRIORITY=local,sina,eastmoney,tencent,stocksdk",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "KLINE_SOURCE_PRIORITY": {
        "help_key": "settings.data_source.kline_routing",
        "examples": [
            "KLINE_SOURCE_PRIORITY=local,sina,eastmoney,tencent,stocksdk",
            "KLINE_SOURCE_PRIORITY=stocksdk,eastmoney,sina,tencent,local",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKINFO_DATA_SOURCE": {
        "help_key": "settings.data_source.stockinfo_routing",
        "examples": [
            "STOCKINFO_DATA_SOURCE=auto",
            "STOCKINFO_DATA_SOURCE=eastmoney",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKINFO_FALLBACK_ENABLED": {
        "help_key": "settings.data_source.stockinfo_routing",
        "examples": [
            "STOCKINFO_FALLBACK_ENABLED=true",
            "STOCKINFO_SOURCE_PRIORITY=local,eastmoney,tencent,stocksdk",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "STOCKINFO_SOURCE_PRIORITY": {
        "help_key": "settings.data_source.stockinfo_routing",
        "examples": [
            "STOCKINFO_SOURCE_PRIORITY=local,eastmoney,tencent,stocksdk",
            "STOCKINFO_SOURCE_PRIORITY=eastmoney,stocksdk,local",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "CODESEARCH_DATA_SOURCE": {
        "help_key": "settings.data_source.codesearch_routing",
        "examples": [
            "CODESEARCH_DATA_SOURCE=auto",
            "CODESEARCH_DATA_SOURCE=eastmoney",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "CODESEARCH_FALLBACK_ENABLED": {
        "help_key": "settings.data_source.codesearch_routing",
        "examples": [
            "CODESEARCH_FALLBACK_ENABLED=true",
            "CODESEARCH_SOURCE_PRIORITY=local,eastmoney,stocksdk",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "CODESEARCH_SOURCE_PRIORITY": {
        "help_key": "settings.data_source.codesearch_routing",
        "examples": [
            "CODESEARCH_SOURCE_PRIORITY=local,eastmoney,stocksdk",
            "CODESEARCH_SOURCE_PRIORITY=eastmoney,stocksdk,local",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "SECTOR_DATA_SOURCE": {
        "help_key": "settings.data_source.sector_routing",
        "examples": [
            "SECTOR_DATA_SOURCE=auto",
            "SECTOR_DATA_SOURCE=eastmoney",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "SECTOR_FALLBACK_ENABLED": {
        "help_key": "settings.data_source.sector_routing",
        "examples": [
            "SECTOR_FALLBACK_ENABLED=true",
            "SECTOR_SOURCE_PRIORITY=eastmoney",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "SECTOR_SOURCE_PRIORITY": {
        "help_key": "settings.data_source.sector_routing",
        "examples": [
            "SECTOR_SOURCE_PRIORITY=eastmoney",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "LIMITPOOL_DATA_SOURCE": {
        "help_key": "settings.data_source.limitpool_routing",
        "examples": [
            "LIMITPOOL_DATA_SOURCE=auto",
            "LIMITPOOL_DATA_SOURCE=stocksdk",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "LIMITPOOL_FALLBACK_ENABLED": {
        "help_key": "settings.data_source.limitpool_routing",
        "examples": [
            "LIMITPOOL_FALLBACK_ENABLED=true",
            "LIMITPOOL_SOURCE_PRIORITY=eastmoney,stocksdk",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "LIMITPOOL_SOURCE_PRIORITY": {
        "help_key": "settings.data_source.limitpool_routing",
        "examples": [
            "LIMITPOOL_SOURCE_PRIORITY=eastmoney",
            "LIMITPOOL_SOURCE_PRIORITY=eastmoney,stocksdk",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "ALPHAVANTAGE_API_KEY": {
        "help_key": "settings.data_source.alphavantage",
        "examples": [
            "ALPHAVANTAGE_API_KEY=your-alphavantage-key",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "FINNHUB_API_KEY": {
        "help_key": "settings.data_source.finnhub",
        "examples": [
            "FINNHUB_API_KEY=your-finnhub-key",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "LONGBRIDGE_APP_KEY": {
        "help_key": "settings.data_source.longbridge",
        "examples": [
            "LONGBRIDGE_OAUTH_CLIENT_ID=your-oauth-client-id",
            "LONGBRIDGE_APP_KEY=your-app-key",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "LONGBRIDGE_APP_SECRET": {
        "help_key": "settings.data_source.longbridge",
        "examples": [
            "LONGBRIDGE_APP_SECRET=your-app-secret",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "LONGBRIDGE_ACCESS_TOKEN": {
        "help_key": "settings.data_source.longbridge",
        "examples": [
            "LONGBRIDGE_ACCESS_TOKEN=your-access-token",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "LONGBRIDGE_OAUTH_CLIENT_ID": {
        "help_key": "settings.data_source.longbridge",
        "examples": [
            "LONGBRIDGE_OAUTH_CLIENT_ID=your-oauth-client-id",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "SOCIAL_SENTIMENT_API_KEY": {
        "help_key": "settings.data_source.social_sentiment",
        "examples": [
            "SOCIAL_SENTIMENT_API_KEY=your-provider-key",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "SOCIAL_SENTIMENT_API_URL": {
        "help_key": "settings.data_source.social_sentiment",
        "examples": [
            "SOCIAL_SENTIMENT_API_URL=https://api.adanos.org",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "WSCN_LIVE_NEWS_ENABLED": {
        "help_key": "settings.data_source.live_news",
        "examples": [
            "WSCN_LIVE_NEWS_ENABLED=true",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC": {
        "help_key": "settings.data_source.live_news",
        "examples": [
            "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC=300",
            "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC=0",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WSCN_LIVE_NEWS_IMPORTANT_SCORE": {
        "help_key": "settings.data_source.live_news",
        "examples": [
            "WSCN_LIVE_NEWS_IMPORTANT_SCORE=3",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WSCN_LIVE_NEWS_DEFAULT_LIMIT": {
        "help_key": "settings.data_source.live_news",
        "examples": [
            "WSCN_LIVE_NEWS_DEFAULT_LIMIT=30",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WSCN_LIVE_NEWS_TIMEOUT_SEC": {
        "help_key": "settings.data_source.live_news",
        "examples": [
            "WSCN_LIVE_NEWS_TIMEOUT_SEC=8",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW": {
        "help_key": "settings.data_source.live_news",
        "examples": [
            "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW=true",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WSCN_LIVE_NEWS_BASE_URL": {
        "help_key": "settings.data_source.live_news",
        "examples": [
            "WSCN_LIVE_NEWS_BASE_URL=https://api-one.wallstcn.com",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WALLSTREETCN_CALENDAR_ENABLED": {
        "help_key": "settings.data_source.live_calendar",
        "examples": [
            "WALLSTREETCN_CALENDAR_ENABLED=true",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE": {
        "help_key": "settings.data_source.live_calendar",
        "examples": [
            "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE=3",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WALLSTREETCN_CALENDAR_TIMEOUT": {
        "help_key": "settings.data_source.live_calendar",
        "examples": [
            "WALLSTREETCN_CALENDAR_TIMEOUT=8",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "WALLSTREETCN_CALENDAR_BASE_URL": {
        "help_key": "settings.data_source.live_calendar",
        "examples": [
            "WALLSTREETCN_CALENDAR_BASE_URL=https://api-one-wscn.awtmt.com",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "NEWS_INTEL_AUTO_FETCH_ENABLED": {
        "help_key": "settings.data_source.news_intel",
        "examples": [
            "NEWS_INTEL_AUTO_FETCH_ENABLED=false",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "NEWS_INTEL_RETENTION_DAYS": {
        "help_key": "settings.data_source.news_intel",
        "examples": [
            "NEWS_INTEL_RETENTION_DAYS=30",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "NEWS_INTEL_MAX_ITEMS_PER_SOURCE": {
        "help_key": "settings.data_source.news_intel",
        "examples": [
            "NEWS_INTEL_MAX_ITEMS_PER_SOURCE=50",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "NEWS_INTEL_FETCH_TIMEOUT_SEC": {
        "help_key": "settings.data_source.news_intel",
        "examples": [
            "NEWS_INTEL_FETCH_TIMEOUT_SEC=8",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "NEWSNOW_BASE_URL": {
        "help_key": "settings.data_source.newsnow",
        "examples": [
            "NEWSNOW_BASE_URL=https://newsnow.busiyi.world",
        ],
        "docs": _DOC_FULL_GUIDE_NEWS,
        "warning_codes": [],
    },
    "ANSPIRE_LLM_ENABLED": {
        "help_key": "settings.ai_model.anspire_llm",
        "examples": [
            "ANSPIRE_LLM_ENABLED=true",
            "ANSPIRE_API_KEYS=your_anspire_key",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": [],
    },
    "ANSPIRE_LLM_BASE_URL": {
        "help_key": "settings.ai_model.anspire_llm",
        "examples": [
            "ANSPIRE_LLM_BASE_URL=https://open-gateway.anspire.cn/v6",
            "ANSPIRE_LLM_BASE_URL=https://open-gateway.anspire.ai/v6",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["base_url_must_match_provider"],
    },
    "ANSPIRE_LLM_MODEL": {
        "help_key": "settings.ai_model.anspire_llm",
        "examples": [
            "ANSPIRE_LLM_MODEL=Doubao-Seed-2.0-lite",
            "LITELLM_MODEL=openai/Doubao-Seed-2.0-lite",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": [],
    },
    "DEEPSEEK_API_KEYS": {
        "help_key": "settings.ai_model.provider_keys",
        "examples": [
            "DEEPSEEK_API_KEYS=sk-xxxx,sk-yyyy",
            "LITELLM_MODEL=deepseek/deepseek-v4-flash",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["secret_value", "comma_separated_keys"],
    },
    "GEMINI_API_KEYS": {
        "help_key": "settings.ai_model.provider_keys",
        "examples": [
            "GEMINI_API_KEYS=your_gemini_key_1,your_gemini_key_2",
            "LITELLM_MODEL=gemini/gemini-3.1-pro-preview",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["secret_value", "comma_separated_keys"],
    },
    "GEMINI_MODEL": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "GEMINI_MODEL=gemini-3.1-pro-preview",
            "LITELLM_MODEL=gemini/gemini-3.1-pro-preview",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "GEMINI_MODEL_FALLBACK": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "GEMINI_MODEL_FALLBACK=gemini-3-flash-preview",
            "LITELLM_FALLBACK_MODELS=gemini/gemini-3-flash-preview",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "GEMINI_TEMPERATURE": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "GEMINI_TEMPERATURE=0.7",
            "LLM_TEMPERATURE=0.7",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "OPENAI_API_KEYS": {
        "help_key": "settings.ai_model.provider_keys",
        "examples": [
            "OPENAI_API_KEYS=sk-xxxx,sk-yyyy",
            "OPENAI_BASE_URL=https://api.example.com/v1",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["secret_value", "comma_separated_keys"],
    },
    "OPENAI_MODEL": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "OPENAI_MODEL=gpt-5.5",
            "LITELLM_MODEL=openai/gpt-5.5",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "OPENAI_VISION_MODEL": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "OPENAI_VISION_MODEL=gpt-5.5",
            "VISION_MODEL=openai/gpt-5.5",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "OPENAI_TEMPERATURE": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "OPENAI_TEMPERATURE=0.7",
            "LLM_TEMPERATURE=0.7",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "ANTHROPIC_API_KEYS": {
        "help_key": "settings.ai_model.provider_keys",
        "examples": [
            "ANTHROPIC_API_KEYS=sk-ant-xxxx,sk-ant-yyyy",
            "LITELLM_MODEL=anthropic/claude-sonnet-4-6",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["secret_value", "comma_separated_keys"],
    },
    "ANTHROPIC_MODEL": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "ANTHROPIC_MODEL=claude-sonnet-4-6",
            "LITELLM_MODEL=anthropic/claude-sonnet-4-6",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "ANTHROPIC_TEMPERATURE": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "ANTHROPIC_TEMPERATURE=0.7",
            "LLM_TEMPERATURE=0.7",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "ANTHROPIC_MAX_TOKENS": {
        "help_key": "settings.ai_model.legacy_provider_params",
        "examples": [
            "ANTHROPIC_MAX_TOKENS=8192",
        ],
        "docs": _DOC_LLM_CONFIG,
        "warning_codes": ["legacy_provider_setting"],
    },
    "TICKFLOW_API_KEY": {
        "help_key": "settings.data_source.TICKFLOW_API_KEY",
        "examples": [
            "TICKFLOW_API_KEY=your_tickflow_key",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": ["secret_value"],
    },
    "TICKFLOW_PRIORITY": {
        "help_key": "settings.data_source.TICKFLOW_PRIORITY",
        "examples": ["TICKFLOW_PRIORITY=2"],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
    },
    "TICKFLOW_KLINE_ADJUST": {
        "help_key": "settings.data_source.TICKFLOW_KLINE_ADJUST",
        "examples": ["TICKFLOW_KLINE_ADJUST=none"],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
    },
    "TICKFLOW_BATCH_DAILY_ENABLED": {
        "help_key": "settings.data_source.TICKFLOW_BATCH_DAILY_ENABLED",
        "examples": ["TICKFLOW_BATCH_DAILY_ENABLED=true"],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
    },
    "TICKFLOW_BATCH_SIZE": {
        "help_key": "settings.data_source.TICKFLOW_BATCH_SIZE",
        "examples": ["TICKFLOW_BATCH_SIZE=100"],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
    },
    "SERPAPI_API_KEYS": {
        "help_key": "settings.data_source.search_api_keys",
        "examples": [
            "SERPAPI_API_KEYS=serpapi_key_1,serpapi_key_2",
        ],
        "docs": _DOC_FULL_GUIDE_SEARCH,
        "warning_codes": ["secret_value", "comma_separated_keys"],
    },
    "BRAVE_API_KEYS": {
        "help_key": "settings.data_source.search_api_keys",
        "examples": [
            "BRAVE_API_KEYS=brave_key_1,brave_key_2",
        ],
        "docs": _DOC_FULL_GUIDE_SEARCH,
        "warning_codes": ["secret_value", "comma_separated_keys"],
    },
    "BOCHA_API_KEYS": {
        "help_key": "settings.data_source.search_api_keys",
        "examples": [
            "BOCHA_API_KEYS=bocha_key_1,bocha_key_2",
        ],
        "docs": _DOC_FULL_GUIDE_SEARCH,
        "warning_codes": ["secret_value", "comma_separated_keys"],
    },
    "MINIMAX_API_KEYS": {
        "help_key": "settings.data_source.search_api_keys",
        "examples": [
            "MINIMAX_API_KEYS=minimax_key_1,minimax_key_2",
        ],
        "docs": _DOC_FULL_GUIDE_SEARCH,
        "warning_codes": ["secret_value", "comma_separated_keys"],
    },
    "SEARXNG_PUBLIC_INSTANCES_ENABLED": {
        "help_key": "settings.data_source.SEARXNG_BASE_URLS",
        "examples": [
            "SEARXNG_PUBLIC_INSTANCES_ENABLED=true",
            "SEARXNG_PUBLIC_INSTANCES_ENABLED=false",
        ],
        "docs": _DOC_FULL_GUIDE_SEARCH,
        "warning_codes": ["public_instance_stability"],
    },
    "BIAS_THRESHOLD": {
        "help_key": "settings.data_source.BIAS_THRESHOLD",
        "examples": [
            "BIAS_THRESHOLD=5.0",
            "BIAS_THRESHOLD=8.0",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "PYTDX_HOST": {
        "help_key": "settings.data_source.pytdx",
        "examples": [
            "PYTDX_HOST=119.147.212.81",
            "PYTDX_PORT=7709",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "PYTDX_PORT": {
        "help_key": "settings.data_source.pytdx",
        "examples": [
            "PYTDX_PORT=7709",
            "PYTDX_HOST=119.147.212.81",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": [],
    },
    "PYTDX_SERVERS": {
        "help_key": "settings.data_source.pytdx",
        "examples": [
            "PYTDX_SERVERS=119.147.212.81:7709,119.147.212.81:7711",
        ],
        "docs": _DOC_FULL_GUIDE_DATA_SOURCE,
        "warning_codes": ["overrides_pytdx_host_port"],
    },
    "DINGTALK_APP_KEY": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "DINGTALK_APP_KEY=your_dingtalk_app_key",
            "DINGTALK_APP_SECRET=your_dingtalk_app_secret",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    "DINGTALK_APP_SECRET": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "DINGTALK_APP_SECRET=your_dingtalk_app_secret",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    "PUSHPLUS_TOKEN": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "PUSHPLUS_TOKEN=your_pushplus_token",
            "PUSHPLUS_TOPIC=your_pushplus_topic",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    "CUSTOM_WEBHOOK_BEARER_TOKEN": {
        "help_key": "settings.notification.CUSTOM_WEBHOOK_URLS",
        "examples": [
            "CUSTOM_WEBHOOK_BEARER_TOKEN=your_bearer_token",
        ],
        "docs": _DOC_CUSTOM_WEBHOOK,
        "warning_codes": ["secret_value"],
    },
    "CUSTOM_WEBHOOK_BODY_TEMPLATE": {
        "help_key": "settings.notification.CUSTOM_WEBHOOK_URLS",
        "examples": [
            'CUSTOM_WEBHOOK_BODY_TEMPLATE={"msg_type":"text","content":$content_json}',
            'CUSTOM_WEBHOOK_BODY_TEMPLATE={"title":$title_json,"text":$content_json}',
        ],
        "docs": _DOC_CUSTOM_WEBHOOK,
        "warning_codes": ["json_template_must_render_object"],
    },
    "FEISHU_WEBHOOK_SECRET": {
        "help_key": "settings.notification.FEISHU_WEBHOOK_URL",
        "examples": [
            "FEISHU_WEBHOOK_SECRET=your_feishu_webhook_secret",
        ],
        "docs": [
            *_DOC_FULL_GUIDE_NOTIFICATION,
            {
                "label": "飞书机器人配置专题",
                "href": "https://github.com/ArcSeek-X/HermesX/blob/main/docs/bot/feishu-bot-config.md",
            },
        ],
        "warning_codes": ["secret_value"],
    },
    "FEISHU_WEBHOOK_KEYWORD": {
        "help_key": "settings.notification.FEISHU_WEBHOOK_URL",
        "examples": [
            "FEISHU_WEBHOOK_KEYWORD=股票日报",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": [],
    },
    "FEISHU_APP_ID": {
        "help_key": "settings.notification.FEISHU_WEBHOOK_URL",
        "examples": [
            "FEISHU_APP_ID=cli_xxxxx",
            "FEISHU_APP_SECRET=your_feishu_app_secret",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["not_webhook_delivery"],
    },
    "FEISHU_APP_SECRET": {
        "help_key": "settings.notification.FEISHU_WEBHOOK_URL",
        "examples": [
            "FEISHU_APP_SECRET=your_feishu_app_secret",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value", "not_webhook_delivery"],
    },
    "TELEGRAM_MESSAGE_THREAD_ID": {
        "help_key": "settings.notification.telegram",
        "examples": [
            "TELEGRAM_MESSAGE_THREAD_ID=123",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": [],
    },
    "DISCORD_MAIN_CHANNEL_ID": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "DISCORD_MAIN_CHANNEL_ID=123456789012345678",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": [],
    },
    "DISCORD_INTERACTIONS_PUBLIC_KEY": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "DISCORD_INTERACTIONS_PUBLIC_KEY=your_discord_public_key",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": [],
    },
    "SLACK_CHANNEL_ID": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "SLACK_CHANNEL_ID=C0123456789",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": [],
    },
    "SLACK_WEBHOOK_URL": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["webhook_secret_value"],
    },
    "PUSHOVER_USER_KEY": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "PUSHOVER_USER_KEY=your_pushover_user_key",
            "PUSHOVER_API_TOKEN=your_pushover_api_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    "PUSHOVER_API_TOKEN": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "PUSHOVER_API_TOKEN=your_pushover_api_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    "NTFY_URL": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "NTFY_URL=https://ntfy.sh/your_topic",
            "NTFY_TOKEN=your_ntfy_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["webhook_secret_value"],
    },
    "NTFY_TOKEN": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "NTFY_TOKEN=your_ntfy_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    "GOTIFY_URL": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "GOTIFY_URL=https://gotify.example.com",
            "GOTIFY_TOKEN=your_gotify_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["webhook_secret_value"],
    },
    "GOTIFY_TOKEN": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "GOTIFY_TOKEN=your_gotify_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    "PUSHPLUS_TOPIC": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "PUSHPLUS_TOPIC=your_pushplus_topic",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": [],
    },
    "SERVERCHAN3_SENDKEY": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "SERVERCHAN3_SENDKEY=your_serverchan3_sendkey",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    "ASTRBOT_URL": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "ASTRBOT_URL=https://astrbot.example.com/webhook",
            "ASTRBOT_TOKEN=your_astrbot_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["webhook_secret_value"],
    },
    "ASTRBOT_TOKEN": {
        "help_key": "settings.notification.chat_bots",
        "examples": [
            "ASTRBOT_TOKEN=your_astrbot_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
        "warning_codes": ["secret_value"],
    },
    # ------------------------------------------------------------------
    # 批次 P3：机器人运行时 / 飞书事件订阅 / 飞书发送形态
    #
    # warning_codes 不在这里重复：重启边界写在 _FIELD_DEFINITIONS 的
    # 字段定义里，这里再写一份会在两处飘移。
    # ------------------------------------------------------------------
    "BOT_ENABLED": {
        "help_key": "settings.notification.bot_runtime",
        "examples": [
            "BOT_ENABLED=true",
            "BOT_ENABLED=false",
        ],
        "docs": _DOC_FULL_GUIDE_BOT + _DOC_BOT_COMMAND,
    },
    "BOT_COMMAND_PREFIX": {
        "help_key": "settings.notification.bot_runtime",
        "examples": [
            "BOT_COMMAND_PREFIX=/",
            "BOT_COMMAND_PREFIX=!",
        ],
        "docs": _DOC_FULL_GUIDE_BOT + _DOC_BOT_COMMAND,
    },
    "BOT_ADMIN_USERS": {
        "help_key": "settings.notification.bot_runtime",
        "examples": [
            "BOT_ADMIN_USERS=ou_xxxxxxxx,ou_yyyyyyyy",
            "BOT_ADMIN_USERS=123456789",
        ],
        "docs": _DOC_FULL_GUIDE_BOT + _DOC_BOT_COMMAND,
    },
    "FEISHU_VERIFICATION_TOKEN": {
        "help_key": "settings.notification.feishu_event_security",
        "examples": [
            "FEISHU_VERIFICATION_TOKEN=your_feishu_verification_token",
            "FEISHU_ENCRYPT_KEY=your_feishu_encrypt_key",
        ],
        "docs": _DOC_FEISHU_BOT + _DOC_BOT_COMMAND,
    },
    "FEISHU_ENCRYPT_KEY": {
        "help_key": "settings.notification.feishu_event_security",
        "examples": [
            "FEISHU_ENCRYPT_KEY=your_feishu_encrypt_key",
        ],
        "docs": _DOC_FEISHU_BOT + _DOC_BOT_COMMAND,
    },
    "FEISHU_MAX_BYTES": {
        "help_key": "settings.notification.feishu_delivery",
        "examples": [
            "FEISHU_MAX_BYTES=20000",
            "FEISHU_MAX_BYTES=9000",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION + _DOC_FEISHU_BOT,
    },
    "FEISHU_SEND_AS_FILE": {
        "help_key": "settings.notification.feishu_delivery",
        "examples": [
            "FEISHU_SEND_AS_FILE=false",
            "FEISHU_SEND_AS_FILE=true",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION + _DOC_FEISHU_BOT,
    },
    "FEISHU_FOLDER_TOKEN": {
        "help_key": "settings.notification.feishu_delivery",
        "examples": [
            "FEISHU_FOLDER_TOKEN=your_feishu_drive_folder_token",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION + _DOC_FEISHU_BOT,
    },
    "EMAIL_SENDER_NAME": {
        "help_key": "settings.notification.email",
        "examples": [
            "EMAIL_SENDER_NAME=HermesX股票分析助手",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION,
    },
    # ------------------------------------------------------------------
    # 批次 P4：组合风险阈值 / 回撤窗口 / 汇率刷新开关
    #
    # 同 P3：warning_codes 不在这里重复，本批字段都不需要重启。
    # ------------------------------------------------------------------
    "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT": {
        "help_key": "settings.system.portfolio_risk",
        "examples": [
            "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT=35.0",
            "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT=20.0",
        ],
        "docs": _DOC_FULL_GUIDE_PORTFOLIO + _DOC_FULL_GUIDE_ENV,
    },
    "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT": {
        "help_key": "settings.system.portfolio_risk",
        "examples": [
            "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT=15.0",
            "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT=8.0",
        ],
        "docs": _DOC_FULL_GUIDE_PORTFOLIO + _DOC_FULL_GUIDE_ENV,
    },
    "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT": {
        "help_key": "settings.system.portfolio_risk",
        "examples": [
            "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT=10.0",
            "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT=6.0",
        ],
        "docs": _DOC_FULL_GUIDE_PORTFOLIO + _DOC_FULL_GUIDE_ENV,
    },
    "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO": {
        "help_key": "settings.system.portfolio_risk",
        "examples": [
            "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO=0.8",
            "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO=0.9",
        ],
        "docs": _DOC_FULL_GUIDE_PORTFOLIO + _DOC_FULL_GUIDE_ENV,
    },
    "PORTFOLIO_RISK_LOOKBACK_DAYS": {
        "help_key": "settings.system.portfolio_risk",
        "examples": [
            "PORTFOLIO_RISK_LOOKBACK_DAYS=180",
            "PORTFOLIO_RISK_LOOKBACK_DAYS=90",
        ],
        "docs": _DOC_FULL_GUIDE_PORTFOLIO + _DOC_FULL_GUIDE_ENV,
    },
    "PORTFOLIO_FX_UPDATE_ENABLED": {
        "help_key": "settings.system.portfolio_fx",
        "examples": [
            "PORTFOLIO_FX_UPDATE_ENABLED=true",
            "PORTFOLIO_FX_UPDATE_ENABLED=false",
        ],
        "docs": _DOC_FULL_GUIDE_PORTFOLIO + _DOC_FULL_GUIDE_ENV,
    },
    # ------------------------------------------------------------------
    # 批次 P5：企业微信消息形态 / 报告转图片
    #
    # warning_codes 不在这里重复，本批字段都不需要重启。
    # ------------------------------------------------------------------
    "WECHAT_MSG_TYPE": {
        "help_key": "settings.notification.wechat_delivery",
        "examples": [
            "WECHAT_MSG_TYPE=markdown",
            "WECHAT_MSG_TYPE=text",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION + _DOC_FULL_GUIDE_ENV,
    },
    "WECHAT_MAX_BYTES": {
        "help_key": "settings.notification.wechat_delivery",
        "examples": [
            "WECHAT_MAX_BYTES=4000",
            "WECHAT_MAX_BYTES=2048",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION + _DOC_FULL_GUIDE_ENV,
    },
    "MARKDOWN_TO_IMAGE_CHANNELS": {
        "help_key": "settings.notification.markdown_to_image",
        "examples": [
            "MARKDOWN_TO_IMAGE_CHANNELS=telegram,wechat,custom,email,slack",
            "MARKDOWN_TO_IMAGE_CHANNELS=",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION + _DOC_FULL_GUIDE_ENV,
    },
    "MARKDOWN_TO_IMAGE_MAX_CHARS": {
        "help_key": "settings.notification.markdown_to_image",
        "examples": [
            "MARKDOWN_TO_IMAGE_MAX_CHARS=15000",
            "MARKDOWN_TO_IMAGE_MAX_CHARS=30000",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION + _DOC_FULL_GUIDE_ENV,
    },
    "MD2IMG_ENGINE": {
        "help_key": "settings.notification.markdown_to_image",
        "examples": [
            "MD2IMG_ENGINE=wkhtmltoimage",
            "MD2IMG_ENGINE=markdown-to-file",
        ],
        "docs": _DOC_FULL_GUIDE_NOTIFICATION + _DOC_FULL_GUIDE_ENV,
    },
}
