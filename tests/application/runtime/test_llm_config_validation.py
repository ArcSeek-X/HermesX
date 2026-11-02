# -*- coding: utf-8 -*-
"""W5.4 拆出的 LLM 渠道校验规则回归。

`SystemConfigService` 原先在本文件里内联了约 930 行模块级校验助手；迁到
`src/application/runtime/llm_config_validation.py` 后，service 只保留编排与
外调端口。这里锁定迁移前的判定口径（数值区间、CSV 拆分、渠道连接必填项、
SSRF 拦截、渠道模型收集），并确认 service 仍以同一对象转发这些助手。
"""

from __future__ import annotations

from src.application.runtime import system_config_service
from src.application.runtime.llm_config_validation import (
    _LLMDiagnostic,
    _anspire_legacy_llm_enabled,
    _collect_llm_channel_models_from_map,
    _split_csv,
    _validate_llm_channel_connection,
    _validate_llm_channel_definition,
    _validate_llm_channel_map,
    _validate_numeric_range,
)


def test_service_reexports_same_rule_objects():
    assert system_config_service._validate_llm_channel_map is _validate_llm_channel_map
    assert system_config_service._split_csv is _split_csv
    assert system_config_service._LLMDiagnostic is _LLMDiagnostic
    assert system_config_service._validate_numeric_range is _validate_numeric_range


def test_validate_numeric_range_reports_both_bounds():
    low = _validate_numeric_range("K", 3, {"min": 5})
    assert [issue["code"] for issue in low] == ["out_of_range"]
    assert low[0]["expected"] == ">=5"
    assert low[0]["actual"] == "3"

    high = _validate_numeric_range("K", 9, {"max": 8})
    assert high[0]["expected"] == "<=8"

    assert _validate_numeric_range("K", 5, {"min": 5, "max": 5}) == []


def test_split_csv_drops_blank_segments():
    assert _split_csv(" a , ,b ") == ["a", "b"]
    assert _split_csv("") == []
    assert _split_csv(None) == []


def test_channel_connection_requires_api_key_for_remote_endpoint():
    issues, resolved_protocol = _validate_llm_channel_connection(
        channel_name="x",
        protocol_value="",
        base_url_value="",
        api_key_value="",
        field_prefix="LLM_X",
        require_base_url=False,
    )
    assert [issue["code"] for issue in issues] == ["missing_api_key"]
    assert issues[0]["key"] == "LLM_X_API_KEY"
    assert resolved_protocol == ""


def test_channel_connection_blocks_metadata_endpoint():
    issues, resolved_protocol = _validate_llm_channel_connection(
        channel_name="x",
        protocol_value="openai",
        base_url_value="http://169.254.169.254/v1",
        api_key_value="sk-test",
        field_prefix="LLM_X",
        require_base_url=False,
    )
    assert [issue["code"] for issue in issues] == ["ssrf_blocked"]
    assert resolved_protocol == "openai"


def test_channel_connection_allows_local_endpoint_without_key():
    issues, _ = _validate_llm_channel_connection(
        channel_name="local",
        protocol_value="openai",
        base_url_value="http://127.0.0.1:11434/v1",
        api_key_value="",
        field_prefix="LLM_LOCAL",
        require_base_url=False,
    )
    assert issues == []


def test_channel_definition_requires_models_when_complete():
    issues = _validate_llm_channel_definition(
        channel_name="x",
        protocol_value="openai",
        base_url_value="https://api.example.com/v1",
        api_key_value="sk-test",
        model_values=[],
        enabled=True,
        field_prefix="LLM_X",
        require_complete=True,
    )
    assert [issue["code"] for issue in issues] == ["missing_models"]
    assert issues[0]["key"] == "LLM_X_MODELS"

    # 不要求完整时直接跳过
    assert (
        _validate_llm_channel_definition(
            channel_name="x",
            protocol_value="",
            base_url_value="",
            api_key_value="",
            model_values=[],
            enabled=False,
            field_prefix="LLM_X",
            require_complete=False,
        )
        == []
    )


def test_collect_llm_channel_models_from_map_respects_channel_switch():
    enabled_map = {
        "LLM_CHANNELS": "main",
        "LLM_MAIN_MODELS": "openai/gpt-4o-mini",
    }
    assert _collect_llm_channel_models_from_map(enabled_map) == ["openai/gpt-4o-mini"]

    disabled_map = dict(enabled_map, LLM_MAIN_ENABLED="false")
    assert _collect_llm_channel_models_from_map(disabled_map) == []
    assert _collect_llm_channel_models_from_map({}) == []


def test_anspire_legacy_switch_defaults_to_enabled():
    assert _anspire_legacy_llm_enabled({"ANSPIRE_API_KEYS": "sk-test"}) is True
    assert _anspire_legacy_llm_enabled({"ANSPIRE_API_KEYS": "sk-test", "ANSPIRE_LLM_ENABLED": "false"}) is False
    # 显式渠道声明时以 LLM_ANSPIRE_ENABLED 为准
    assert (
        _anspire_legacy_llm_enabled(
            {"LLM_CHANNELS": "anspire", "LLM_ANSPIRE_ENABLED": "0"}
        )
        is False
    )
