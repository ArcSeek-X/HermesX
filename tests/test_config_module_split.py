# -*- coding: utf-8 -*-
"""W5.3 配置模块拆分后的契约回归。

`settings.py`（3724 行）与 `registry.py`（6954 行）按「运行时值 / 声明数据 / 解析
助手」拆成多个模块，但对外 import 面必须保持不变：

- ``src.config.settings`` 继续转发导出解析助手与 LLM 渠道规则（同一对象，非副本）；
- ``src.config.registry`` 的 schema 仍由声明表 + 帮助文案装配，字段数与分类数不变；
- 帮助文案不得出现「有文案无声明」的孤儿键；
- 拆出的模块只能向内依赖（domain / 同包），不得 import application / infrastructure。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import src.config as config_package
from src.config import env_parsers, llm_channels
from src.config import settings as settings_module
from src.config.field_definitions import FIELD_DEFINITIONS
from src.config.field_help import FIELD_HELP_METADATA
from src.config.registry import (
    SCHEMA_VERSION,
    build_schema_response,
    get_field_definition,
    get_registered_field_keys,
)


def test_settings_reexports_same_helper_objects():
    assert settings_module.parse_env_bool is env_parsers.parse_env_bool
    assert settings_module.parse_env_int is env_parsers.parse_env_int
    assert settings_module.normalize_tickflow_kline_adjust is env_parsers.normalize_tickflow_kline_adjust
    assert settings_module.resolve_news_window_days is env_parsers.resolve_news_window_days
    assert settings_module.AGENT_CONTEXT_COMPRESSION_PROFILES is env_parsers.AGENT_CONTEXT_COMPRESSION_PROFILES
    assert settings_module.normalize_llm_channel_model is llm_channels.normalize_llm_channel_model
    assert settings_module.resolve_unified_llm_temperature is llm_channels.resolve_unified_llm_temperature
    assert settings_module.SUPPORTED_LLM_CHANNEL_PROTOCOLS is llm_channels.SUPPORTED_LLM_CHANNEL_PROTOCOLS
    # 配置包门面仍指向同一对象
    assert config_package.Config is settings_module.Config
    assert config_package.parse_env_bool is env_parsers.parse_env_bool


def test_registry_uses_split_declaration_tables_directly():
    assert set(get_registered_field_keys()) == set(FIELD_DEFINITIONS)
    assert len(FIELD_DEFINITIONS) == len(get_registered_field_keys()) == 254


def test_help_metadata_has_no_orphan_keys():
    orphan_keys = sorted(set(FIELD_HELP_METADATA) - set(FIELD_DEFINITIONS))
    assert orphan_keys == [], f"帮助文案缺少字段声明: {orphan_keys}"


def test_schema_response_still_assembles_all_fields():
    schema = build_schema_response()
    assert schema["schema_version"] == SCHEMA_VERSION
    assert len(schema["categories"]) == 8
    rendered = sum(len(category.get("fields") or []) for category in schema["categories"])
    assert rendered == len(FIELD_DEFINITIONS)


def test_help_metadata_is_merged_into_field_definition():
    # 有帮助文案的字段必须能取到 help 相关键；无文案字段不臆造。
    key_with_help = next(iter(FIELD_HELP_METADATA))
    merged = get_field_definition(key_with_help)
    for help_key in FIELD_HELP_METADATA[key_with_help]:
        assert merged.get(help_key) == FIELD_HELP_METADATA[key_with_help][help_key]

    key_without_help = next(key for key in FIELD_DEFINITIONS if key not in FIELD_HELP_METADATA)
    assert get_field_definition(key_without_help)["category"] == FIELD_DEFINITIONS[key_without_help]["category"]


def test_extracted_helpers_keep_original_semantics():
    # 整数解析：空值回退、越界钳制
    assert env_parsers.parse_env_int("", 5, field_name="X") == 5
    assert env_parsers.parse_env_int("abc", 5, field_name="X") == 5
    assert env_parsers.parse_env_int("999", 5, field_name="X", maximum=10) == 10
    # 布尔解析：仅 falsey 集合为假
    assert env_parsers.parse_env_bool("off", True) is False
    assert env_parsers.parse_env_bool("yes", False) is True
    # 复权方式：非法值回退 none
    assert env_parsers.normalize_tickflow_kline_adjust("forward") == "forward"
    assert env_parsers.normalize_tickflow_kline_adjust("qfq") == "none"
    # 新闻窗口：不超过全局上限
    assert env_parsers.resolve_news_window_days(30, "ultra_short") == 1
    assert env_parsers.resolve_news_window_days(2, "long") == 2


def test_extracted_llm_helpers_keep_original_semantics():
    assert llm_channels.canonicalize_llm_channel_protocol("claude") == "anthropic"
    assert llm_channels.resolve_llm_channel_protocol(None, base_url="http://localhost:8000/v1") == "openai"
    assert llm_channels.channel_allows_empty_api_key("ollama", None) is True
    assert llm_channels.normalize_llm_channel_model("gpt-4o-mini", "openai") == "openai/gpt-4o-mini"

    config = SimpleNamespace(
        agent_litellm_model="",
        litellm_model="openai/main",
        litellm_fallback_models=["openai/backup", "openai/main"],
        llm_model_list=[],
    )
    assert llm_channels.get_effective_agent_primary_model(config) == "openai/main"
    assert llm_channels.get_effective_agent_models_to_try(config) == ["openai/main", "openai/backup"]


def test_split_modules_stay_inside_config_and_domain():
    for module_name in ("env_parsers.py", "llm_channels.py", "field_definitions.py", "field_help.py"):
        source = Path("src/config") / module_name
        text = source.read_text(encoding="utf-8")
        for forbidden in ("src.application", "src.infrastructure", "src.bootstrap", "api.v1"):
            assert forbidden not in text, f"{module_name} 不应依赖 {forbidden}"
