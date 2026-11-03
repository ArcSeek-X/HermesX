# -*- coding: utf-8 -*-
"""System configuration service for `.env` based settings."""

from __future__ import annotations

import io
import logging
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse, urlunparse

import requests

from src.config import (
    ANSPIRE_LLM_BASE_URL_DEFAULT,
    ANSPIRE_LLM_MODEL_DEFAULT,
    Config,
    _get_litellm_provider,
    _uses_direct_env_provider,
    canonicalize_llm_channel_protocol,
    channel_allows_empty_api_key,
    normalize_agent_litellm_model,
    normalize_news_strategy_profile,
    normalize_llm_channel_model,
    parse_env_bool,
    parse_env_int,
    resolve_news_window_days,
    resolve_llm_channel_protocol,
    setup_env,
)
from src.domain.generation.hermes_rules import (
    HERMES_DEFAULT_BASE_URL,
    HERMES_DEFAULT_MODEL,
    HERMES_DEFAULT_PROTOCOL,
    build_hermes_redaction_values,
    canonicalize_hermes_model_ref,
    canonicalize_hermes_base_url,
    is_masked_secret_placeholder,
    is_reserved_hermes_name,
    parse_hermes_channel,
)
from src.config.env_file import ConfigManager
from src.config.registry import (
    build_schema_response,
    get_category_definitions,
    get_field_definition,
    get_registered_field_keys,
)
from src.application.generation.catalog import (
    normalize_backend_id,
)
from src.domain.generation.backend_identity import (
    AUTO_AGENT_BACKEND_ID,
    CODEX_CLI_BACKEND_ID,
    GENERATION_ONLY_BACKEND_IDS,
    LOCAL_CLI_GENERATION_BACKEND_IDS,
    LITELLM_BACKEND_ID,
)
from src.domain.generation.response_content import strip_leading_think_wrapper
from src.application.generation.runtime_ports import GenerationRuntimePort
from src.domain.notification.contracts import (
    FEISHU_APP_BOT_ENV_GROUP,
    FEISHU_WEBHOOK_ENV_GROUP,
    is_feishu_app_bot_env_configured,
    is_feishu_static_env_configured,
)
from src.domain.notification.noise_rules import validate_notification_timezone
from src.domain.notification.endpoints import (
    resolve_gotify_message_endpoint,
    resolve_ntfy_endpoint,
)
from src.domain.market.stock_list_parser import split_stock_list
from src.application.runtime.generation_backend_status import GenerationBackendStatusService
from src.application.runtime.agent_backend_status import AgentBackendStatusService
from src.application.runtime.llm_config_validation import (
    _LLMDiagnostic,
    _anspire_legacy_llm_enabled,
    _collect_hermes_channel_models_from_map,
    _collect_llm_channel_models_from_map,
    _collect_non_hermes_channel_models_from_map,
    _collect_yaml_models_from_map,
    _has_model_access_denied_signal,
    _has_model_not_found_signal,
    _has_provider_prefix_mismatch_signal,
    _has_request_blocked_signal,
    _has_runtime_source_for_model,
    _has_transport_blocked_signal,
    _split_csv,
    _uses_litellm_yaml,
    _validate_llm_channel_connection,
    _validate_llm_channel_definition,
    _validate_llm_channel_map,
    _validate_llm_runtime_selection,
    _validate_numeric_range,
)
from src.application.runtime.system_config_ports import (
    ConfigProbePort,
    EventAlertRulesValidationError,
    NotificationDispatchPort,
    RuntimeResetPort,
)

# §4.3 拆分 F2：URL/主机安全纯规则已下沉 ``src.domain.shared.url_security``，
# 此处 re-export 保持模块全局访问面（tests 直调/穿透契约不变）。
from src.domain.shared.url_security import (  # noqa: F401
    _build_llm_models_url,
    _canonical_ipv4_numeric_host,
    _is_noncanonical_ipv4_numeric_host,
    _is_safe_base_url,
    _is_valid_llm_base_url,
    _is_valid_url,
    _normalize_hostname_for_security,
)

# ── §4.3 拆分 F3：运行时外调端口 seam（配置探测 / 通知试发 / 单例重置）──────────
# 契约见 ``src.application.runtime.system_config_ports``，真实外调收纳于
# ``src.infrastructure.providers.system_config_runtime`` 适配器，由
# ``src.bootstrap.system_config.configure_system_config_runtime`` 装配（T5e 同型）。
_config_probe_port: Optional[ConfigProbePort] = None
_notification_dispatch_port: Optional[NotificationDispatchPort] = None
_runtime_reset_port: Optional[RuntimeResetPort] = None
_generation_runtime_port: Optional[GenerationRuntimePort] = None


def set_config_probe_port(port: Optional[ConfigProbePort]) -> None:
    """装配配置探测端口（bootstrap 调用；幂等：仅非 None 覆盖，T5d 同型）。"""
    global _config_probe_port
    if port is not None:
        _config_probe_port = port


def set_notification_dispatch_port(port: Optional[NotificationDispatchPort]) -> None:
    """装配通知试发端口（bootstrap 调用；幂等：仅非 None 覆盖）。"""
    global _notification_dispatch_port
    if port is not None:
        _notification_dispatch_port = port


def set_runtime_reset_port(port: Optional[RuntimeResetPort]) -> None:
    """装配运行时单例重置端口（bootstrap 调用；幂等：仅非 None 覆盖）。"""
    global _runtime_reset_port
    if port is not None:
        _runtime_reset_port = port


def set_generation_runtime_port(port: Optional[GenerationRuntimePort]) -> None:
    """装配生成运行时端口（bootstrap 调用；幂等：仅非 None 覆盖）。"""
    global _generation_runtime_port
    if port is not None:
        _generation_runtime_port = port


def _get_generation_runtime_port() -> GenerationRuntimePort:
    """取生成运行时端口；未装配即 fail-fast（同上）。"""
    if _generation_runtime_port is None:  # pragma: no cover - 正常启动链路由 bootstrap 装配
        raise RuntimeError(
            "GenerationRuntimePort 未装配：请经 configure_generation_runtime() 完成 bootstrap 装配。"
        )
    return _generation_runtime_port


def _get_config_probe_port() -> ConfigProbePort:
    """取配置探测端口；未装配即 fail-fast（API/CLI 启动链路必经 bootstrap 装配，
    触发此处说明装配缺失而非运行期降级）。"""
    if _config_probe_port is None:  # pragma: no cover - 正常启动链路由 bootstrap 装配
        raise RuntimeError("ConfigProbePort 未装配：请经 configure_system_config_runtime() 完成 bootstrap 装配。")
    return _config_probe_port


def _get_notification_dispatch_port() -> NotificationDispatchPort:
    """取通知试发端口；未装配即 fail-fast（同上）。"""
    if _notification_dispatch_port is None:  # pragma: no cover - 正常启动链路由 bootstrap 装配
        raise RuntimeError("NotificationDispatchPort 未装配：请经 configure_system_config_runtime() 完成 bootstrap 装配。")
    return _notification_dispatch_port


def _get_runtime_reset_port() -> RuntimeResetPort:
    """取运行时单例重置端口；未装配即 fail-fast（同上）。"""
    if _runtime_reset_port is None:  # pragma: no cover - 正常启动链路由 bootstrap 装配
        raise RuntimeError("RuntimeResetPort 未装配：请经 configure_system_config_runtime() 完成 bootstrap 装配。")
    return _runtime_reset_port


from src.application.runtime.config_probe_diagnostics import (
    _build_skipped_capability_results,
    _build_llm_capability_result,
    _build_llm_capability_result_from_diagnostic,
    _extract_llm_tool_call_names,
    _extract_llm_stream_chunk_content,
    _classify_llm_capability_exception,
    _build_llm_channel_result,
    _merge_llm_diagnostic_details,
    _build_redaction_values,
    _comma_flexible_secret_pattern,
    _sanitize_llm_error_text,
    _sanitize_llm_details,
    _sanitize_llm_value,
    _classify_llm_http_error,
    _classify_llm_exception,
    _extract_llm_completion_content,
    _extract_llm_discovery_error,
    _extract_discovered_llm_models,
)
from src.application.runtime.notification_channel_test import (
    NotificationChannelTester,
    _NOTIFICATION_TEST_CHANNELS,
    _NOTIFICATION_TEST_KEY_MAP,
    _NOTIFICATION_REQUIRED_KEY_GROUPS,
    _NOTIFICATION_TEST_TARGET_KEYS,
)
from src.application.runtime.llm_channel_probe import LlmChannelProbe
from src.application.runtime.setup_status import SetupStatusBuilder
from src.application.runtime.config_value_validation import ConfigValueValidator

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when one or more submitted fields fail validation."""

    def __init__(self, issues: List[Dict[str, Any]]):
        super().__init__("Configuration validation failed")
        self.issues = issues


class ConfigConflictError(Exception):
    """Raised when submitted config_version is stale."""

    def __init__(self, current_version: str):
        super().__init__("Configuration version conflict")
        self.current_version = current_version


class ConfigImportError(Exception):
    """Raised when an imported `.env` payload is invalid."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class SystemConfigService:
    """Service layer for reading, validating, and updating runtime configuration."""

    _GENERATION_BACKEND_STATUS_EXACT_KEYS = {
        "GENERATION_BACKEND",
        "GENERATION_FALLBACK_BACKEND",
        "GENERATION_BACKEND_TIMEOUT_SECONDS",
        "GENERATION_BACKEND_MAX_OUTPUT_BYTES",
        "GENERATION_BACKEND_MAX_CONCURRENCY",
        "LOCAL_CLI_BACKEND_MAX_CONCURRENCY",
        "OPENCODE_CLI_MODEL",
        "LITELLM_CONFIG",
        "LITELLM_MODEL",
        "LITELLM_FALLBACK_MODELS",
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
        "OLLAMA_API_BASE",
        "OLLAMA_MODEL",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEYS",
        "AIHUBMIX_KEY",
        "ANSPIRE_LLM_ENABLED",
        "ANSPIRE_LLM_BASE_URL",
        "ANSPIRE_LLM_MODEL",
        "ANSPIRE_API_KEYS",
    }
    _GENERATION_BACKEND_STATUS_LLM_CHANNEL_RE = re.compile(
        r"^LLM_[A-Z0-9_]+_(PROTOCOL|BASE_URL|API_KEY|API_KEYS|MODELS|EXTRA_HEADERS|ENABLED)$"
    )
    _AGENT_BACKEND_STATUS_EXACT_KEYS = {
        "AGENT_BACKEND",
        "AGENT_GENERATION_BACKEND",
        "AGENT_LITELLM_MODEL",
        "AGENT_MODE",
        "AGENT_ARCH",
        "AGENT_ORCHESTRATOR_TIMEOUT_S",
    }

    _WEB_SETTINGS_LLM_CHANNEL_SUPPORT_KEY_RE = re.compile(
        r"^LLM_([A-Z0-9_]+)_(PROTOCOL|BASE_URL|API_KEY|API_KEYS|MODELS|EXTRA_HEADERS|ENABLED)$"
    )

    _DISPLAY_KEY_ALIASES: Dict[str, Tuple[str, ...]] = {
        "AGENT_SKILL_DIR": ("AGENT_SKILL_DIR", "AGENT_STRATEGY_DIR"),
        "AGENT_SKILL_AUTOWEIGHT": ("AGENT_SKILL_AUTOWEIGHT", "AGENT_STRATEGY_AUTOWEIGHT"),
        "AGENT_SKILL_ROUTING": ("AGENT_SKILL_ROUTING", "AGENT_STRATEGY_ROUTING"),
    }
    _DISPLAY_VALUE_ALIASES: Dict[str, Dict[str, str]] = {
        "AGENT_ORCHESTRATOR_MODE": {
            "strategy": "specialist",
            "skill": "specialist",
        }
    }
    _SERVER_MASKED_CONFIG_KEYS: Set[str] = {
        "ALPHASIFT_INSTALL_SPEC",
        "LLM_HERMES_API_KEY",
        "LLM_HERMES_API_KEYS",
        "LLM_HERMES_EXTRA_HEADERS",
        "LLM_USAGE_HMAC_SECRET",
    }
    _NOTIFICATION_TEST_CHANNELS = _NOTIFICATION_TEST_CHANNELS
    _NOTIFICATION_TEST_KEY_MAP = _NOTIFICATION_TEST_KEY_MAP
    _NOTIFICATION_REQUIRED_KEY_GROUPS = _NOTIFICATION_REQUIRED_KEY_GROUPS
    _NOTIFICATION_TEST_TARGET_KEYS = _NOTIFICATION_TEST_TARGET_KEYS

    def __init__(self, manager: Optional[ConfigManager] = None, runtime_scheduler: Optional[Any] = None):
        self._manager = manager or ConfigManager()
        self._runtime_scheduler = runtime_scheduler

    def _channel_probe(self) -> LlmChannelProbe:
        return LlmChannelProbe(
            self._manager,
            probe_port_provider=_get_config_probe_port,
            generation_runtime_provider=_get_generation_runtime_port,
            runtime_config=getattr(self, "_config", None),
        )

    def get_schema(self) -> Dict[str, Any]:
        """Return grouped schema metadata for UI rendering."""
        return build_schema_response()

    @staticmethod
    def _reload_runtime_singletons() -> None:
        """Reset runtime singleton services after config reload."""
        _get_runtime_reset_port().reload_runtime_singletons()

    @classmethod
    def _normalize_display_value(cls, key: str, value: str) -> str:
        alias_map = cls._DISPLAY_VALUE_ALIASES.get(key.upper())
        if not alias_map:
            return value
        return alias_map.get(value.strip().lower(), value)

    @classmethod
    def _build_display_config_map(cls, raw_config_map: Dict[str, str]) -> Dict[str, str]:
        raw_upper = {key.upper(): value for key, value in raw_config_map.items()}
        aliased_keys = {
            alias
            for candidates in cls._DISPLAY_KEY_ALIASES.values()
            for alias in candidates
        }
        display_map: Dict[str, str] = {}

        for key, value in raw_upper.items():
            if key in aliased_keys:
                continue
            display_map[key] = cls._normalize_display_value(key, value)

        for canonical_key, candidates in cls._DISPLAY_KEY_ALIASES.items():
            canonical_env_key = candidates[0]
            if canonical_env_key in raw_upper:
                display_map[canonical_key] = cls._normalize_display_value(
                    canonical_key,
                    raw_upper[canonical_env_key],
                )
                continue

            selected_value: Optional[str] = None
            candidate_seen = False
            for candidate_key in candidates[1:]:
                if candidate_key not in raw_upper:
                    continue
                candidate_seen = True
                candidate_value = raw_upper[candidate_key]
                if candidate_value:
                    selected_value = candidate_value
                    break
            if candidate_seen:
                if selected_value is None:
                    for candidate_key in candidates[1:]:
                        if candidate_key in raw_upper:
                            selected_value = raw_upper[candidate_key]
                            break
                if selected_value is None:
                    selected_value = ""
                display_map[canonical_key] = cls._normalize_display_value(
                    canonical_key,
                    selected_value,
                )

        return display_map

    @staticmethod
    def _resolve_display_value(raw_value: str, field_schema: Dict[str, Any], raw_value_exists: bool) -> str:
        if raw_value_exists:
            return raw_value

        if field_schema.get("ui_control") == "switch" and raw_value:
            return raw_value

        if field_schema.get("ui_control") == "switch":
            default_value = field_schema.get("default_value")
            if isinstance(default_value, str) and default_value:
                return default_value

        return raw_value

    @classmethod
    def _get_schema_config_keys(cls, config_map: Dict[str, str], registered_keys: Set[str]) -> Set[str]:
        """Return keys needed by the Web schema payload.

        Ordinary settings must be registry-backed. LLM channel detail keys are
        kept only as editor support data for channels declared in LLM_CHANNELS.
        """
        keys = set(registered_keys)
        channel_names = {
            segment.strip().upper()
            for segment in config_map.get("LLM_CHANNELS", "").split(",")
            if segment.strip()
        }
        if not channel_names:
            return keys

        for key in config_map:
            match = cls._WEB_SETTINGS_LLM_CHANNEL_SUPPORT_KEY_RE.match(key)
            if match and match.group(1) in channel_names:
                keys.add(key)

        return keys

    @classmethod
    def _build_runtime_display_config_map(cls, saved_config_map: Dict[str, str]) -> Dict[str, str]:
        """Return Web settings values injected through the process environment.

        Docker ``env_file`` / ``--env-file`` only populate process environment
        variables; they do not create an active ``.env`` file inside the
        container. Use these values as display fallbacks so Settings can show
        startup-injected config without letting it override later WebUI saves.
        """
        registered_keys = {key.upper() for key in get_registered_field_keys()}
        channel_names = {
            segment.strip().upper()
            for raw_channels in (
                saved_config_map.get("LLM_CHANNELS", ""),
                os.environ.get("LLM_CHANNELS", ""),
            )
            for segment in raw_channels.split(",")
            if segment.strip()
        }
        runtime_map: Dict[str, str] = {}

        for raw_key, raw_value in os.environ.items():
            key = str(raw_key).upper()
            llm_channel_match = cls._WEB_SETTINGS_LLM_CHANNEL_SUPPORT_KEY_RE.match(key)
            if (
                key in registered_keys
                or (llm_channel_match and llm_channel_match.group(1) in channel_names)
            ):
                runtime_map[key] = "" if raw_value is None else str(raw_value)

        return cls._build_display_config_map(runtime_map)

    def get_config(self, include_schema: bool = True, mask_token: str = "******") -> Dict[str, Any]:
        """Return display config values with mask metadata for server-masked fields."""
        saved_config_map = self._build_display_config_map(self._manager.read_config_map())
        runtime_config_map = self._build_runtime_display_config_map(saved_config_map)
        config_map = {
            **runtime_config_map,
            **saved_config_map,
        }
        registered_keys = set(get_registered_field_keys())
        all_keys = set(config_map.keys()) | registered_keys
        if include_schema:
            all_keys = self._get_schema_config_keys(config_map, registered_keys)

        category_orders = {
            item["category"]: item["display_order"]
            for item in get_category_definitions()
        }

        schema_by_key: Dict[str, Dict[str, Any]] = {
            key: get_field_definition(key, config_map.get(key, ""))
            for key in all_keys
        }

        items: List[Dict[str, Any]] = []
        for key in all_keys:
            raw_value_exists = key in saved_config_map
            raw_value = config_map.get(key, "")
            field_schema = schema_by_key[key]
            display_value = self._resolve_display_value(raw_value, field_schema, raw_value_exists)
            is_masked = False
            if key in self._SERVER_MASKED_CONFIG_KEYS and display_value:
                display_value = mask_token
                is_masked = True
            item: Dict[str, Any] = {
                "key": key,
                "value": display_value,
                "raw_value_exists": raw_value_exists,
                "is_masked": is_masked,
            }
            if include_schema:
                item["schema"] = field_schema
            items.append(item)

        items.sort(
            key=lambda item: (
                category_orders.get(schema_by_key[item["key"]].get("category", "uncategorized"), 999),
                schema_by_key[item["key"]].get("display_order", 9999),
                item["key"],
            )
        )

        return {
            "config_version": self._manager.get_config_version(),
            "mask_token": mask_token,
            "items": items,
            "updated_at": self._manager.get_updated_at(),
        }

    def validate(self, items: Sequence[Dict[str, str]], mask_token: str = "******") -> Dict[str, Any]:
        """Validate submitted items without writing to `.env`."""
        issues = self._collect_issues(items=items, mask_token=mask_token)
        valid = not any(issue["severity"] == "error" for issue in issues)
        return {
            "valid": valid,
            "issues": issues,
        }

    def test_notification_channel(
        self,
        *,
        channel: str,
        items: Sequence[Dict[str, str]],
        mask_token: str = "******",
        title: str = "HRS 通知测试",
        content: str = "这是一条来自 HRS Web 设置页的通知测试消息。",
        timeout_seconds: float = 20.0,
    ) -> Dict[str, Any]:
        normalized_channel = (channel or "").strip().lower()
        if normalized_channel not in self._NOTIFICATION_TEST_CHANNELS:
            raise ValueError(f"Unsupported notification channel: {channel}")
        effective_map = self._build_notification_test_effective_map(items=items, mask_token=mask_token)
        return NotificationChannelTester(_get_notification_dispatch_port).test_notification_channel(
            channel=normalized_channel, effective_map=effective_map, title=title,
            content=content, timeout_seconds=timeout_seconds,
        )

    def get_setup_status(self) -> Dict[str, Any]:
        """Return first-run status without persisting or reloading configuration."""
        return SetupStatusBuilder(_get_generation_runtime_port).get_setup_status(
            self._build_setup_effective_config_map()
        )

    def get_generation_backend_status(self) -> Dict[str, Any]:
        """Return cheap generation backend status for saved/runtime config only."""
        effective_map = self._build_generation_backend_base_map()
        service = GenerationBackendStatusService(
            effective_map=effective_map,
            validation_issues=self._collect_generation_backend_issues_from_map(effective_map),
        )
        return service.get_status()

    def preview_generation_backend_status(
        self,
        *,
        items: Sequence[Dict[str, str]],
        mask_token: str = "******",
    ) -> Dict[str, Any]:
        """Return cheap generation backend status for unsaved settings draft."""
        issues = self._collect_generation_backend_issues(items=items, mask_token=mask_token)
        errors = [issue for issue in issues if issue["severity"] == "error"]
        if errors:
            raise ConfigValidationError(issues=errors)
        effective_map = self._build_generation_backend_effective_map(
            items=items,
            mask_token=mask_token,
        )
        service = GenerationBackendStatusService(
            effective_map=effective_map,
            validation_issues=issues,
        )
        return service.get_status()

    def test_generation_backend(
        self,
        *,
        backend_id: Optional[str] = None,
        mode: str = "json",
        items: Sequence[Dict[str, str]] = (),
        mask_token: str = "******",
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run an explicit generation backend smoke test without persisting config."""
        issues = self._collect_generation_backend_issues(items=items, mask_token=mask_token)
        errors = [issue for issue in issues if issue["severity"] == "error"]
        if errors:
            raise ConfigValidationError(issues=errors)
        effective_map = self._build_generation_backend_effective_map(
            items=items,
            mask_token=mask_token,
        )
        service = GenerationBackendStatusService(
            effective_map=effective_map,
            validation_issues=issues,
        )
        return service.smoke_test(
            backend_id=backend_id,
            mode=mode,
            timeout_seconds=timeout_seconds,
        )

    def get_agent_backend_status(self) -> Dict[str, Any]:
        """Return cheap Agent Chat backend status for saved/runtime config."""
        return AgentBackendStatusService(
            config=Config.get_instance(),
        ).get_status()

    def preview_agent_backend_status(
        self,
        *,
        items: Sequence[Dict[str, str]],
        mask_token: str = "******",
    ) -> Dict[str, Any]:
        """Return Agent Chat backend status for an unsaved settings draft."""
        filtered = self._filter_agent_backend_items(items)
        return AgentBackendStatusService(
            effective_map=self._build_agent_backend_effective_map(
                items=filtered,
                mask_token=mask_token,
            ),
        ).get_status()

    def export_env(self) -> Dict[str, Any]:
        """Return the raw active `.env` content for backup."""
        if self._manager.env_path.exists():
            content = self._manager.env_path.read_text(encoding="utf-8")
        else:
            content = ""

        return {
            "content": content,
            "config_version": self._manager.get_config_version(),
            "updated_at": self._manager.get_updated_at(),
        }

    def export_desktop_env(self) -> Dict[str, Any]:
        """Return the raw active `.env` content for desktop backup compatibility."""
        return self.export_env()

    def import_env(
        self,
        *,
        config_version: str,
        content: str,
        reload_now: bool = True,
    ) -> Dict[str, Any]:
        """Merge imported `.env` assignments into the active config."""
        current_version = self._manager.get_config_version()
        if current_version != config_version:
            raise ConfigConflictError(current_version=current_version)

        updates = self._parse_imported_env_content(content)
        return self.update(
            config_version=config_version,
            items=updates,
            mask_token="__HRS_IMPORT_LITERAL_MASK__",
            reload_now=reload_now,
        )

    def import_desktop_env(
        self,
        *,
        config_version: str,
        content: str,
        reload_now: bool = True,
    ) -> Dict[str, Any]:
        """Merge imported `.env` assignments for desktop backup compatibility."""
        return self.import_env(
            config_version=config_version,
            content=content,
            reload_now=reload_now,
        )


    def discover_llm_channel_models(
        self,
        *,
        name: str,
        protocol: str,
        base_url: str,
        api_key: str,
        models: Sequence[str] = (),
        timeout_seconds: float = 20.0,
        use_saved_secret: bool = False,
    ) -> Dict[str, Any]:
        return self._channel_probe().discover_llm_channel_models(name=name, protocol=protocol, base_url=base_url, api_key=api_key, models=models, timeout_seconds=timeout_seconds, use_saved_secret=use_saved_secret)

    def test_llm_channel(
        self,
        *,
        name: str,
        protocol: str,
        base_url: str,
        api_key: str,
        models: Sequence[str],
        enabled: bool = True,
        timeout_seconds: float = 20.0,
        capability_checks: Sequence[str] = (),
        use_saved_secret: bool = False,
    ) -> Dict[str, Any]:
        return self._channel_probe().test_llm_channel(name=name, protocol=protocol, base_url=base_url, api_key=api_key, models=models, enabled=enabled, timeout_seconds=timeout_seconds, capability_checks=capability_checks, use_saved_secret=use_saved_secret)


    _build_skipped_capability_results = staticmethod(_build_skipped_capability_results)


    _build_llm_capability_result = staticmethod(_build_llm_capability_result)

    _build_llm_capability_result_from_diagnostic = staticmethod(_build_llm_capability_result_from_diagnostic)

    _extract_llm_tool_call_names = staticmethod(_extract_llm_tool_call_names)

    _extract_llm_stream_chunk_content = staticmethod(_extract_llm_stream_chunk_content)

    _classify_llm_capability_exception = staticmethod(_classify_llm_capability_exception)

    def update(
        self,
        config_version: str,
        items: Sequence[Dict[str, str]],
        mask_token: str = "******",
        reload_now: bool = True,
    ) -> Dict[str, Any]:
        """Validate and persist updates into `.env`, then reload runtime config."""
        current_version = self._manager.get_config_version()
        if current_version != config_version:
            raise ConfigConflictError(current_version=current_version)

        issues = self._collect_issues(items=items, mask_token=mask_token)
        errors = [issue for issue in issues if issue["severity"] == "error"]
        if errors:
            raise ConfigValidationError(issues=errors)

        previous_map = self._manager.read_config_map()
        submitted_keys: Set[str] = set()
        updates: List[Tuple[str, str]] = []
        sensitive_keys: Set[str] = set()
        for item in items:
            key = item["key"].upper()
            value = item["value"]
            field_schema = get_field_definition(key, value)
            normalized_value = self._normalize_value_for_storage(value, field_schema)
            submitted_keys.add(key)
            updates.append((key, normalized_value))
            if bool(field_schema.get("is_sensitive", False)):
                sensitive_keys.add(key)

        updated_keys, skipped_masked_keys, new_version = self._manager.apply_updates(
            updates=updates,
            sensitive_keys=sensitive_keys,
            mask_token=mask_token,
        )

        warnings: List[str] = []
        reload_triggered = False
        if reload_now:
            try:
                Config.reset_instance()
                self._reload_runtime_singletons()
                setup_env(override=True)
                config = Config.get_instance()
                warnings.extend(config.validate())
                reload_triggered = True
            except Exception as exc:  # pragma: no cover - defensive branch
                logger.error("Configuration reload failed: %s", exc, exc_info=True)
                warnings.append("Configuration updated but reload failed")

        warnings.extend(
            self._build_explainability_warnings(
                submitted_keys=submitted_keys,
                reload_now=reload_now,
            )
        )
        update_map = dict(updates)
        warnings.extend(
            self._build_runtime_model_cleanup_warnings(
                previous_map=previous_map,
                updates=update_map,
            )
        )
        warnings.extend(
            self._build_hermes_unsupported_key_cleanup_warnings(
                previous_map=previous_map,
                updates=update_map,
            )
        )
        if self._runtime_scheduler is not None and submitted_keys & {
            "SCHEDULE_ENABLED",
            "SCHEDULE_TIME",
            "SCHEDULE_TIMES",
        }:
            try:
                self._runtime_scheduler.reconcile_from_config(
                    clear_enabled_override="SCHEDULE_ENABLED" in submitted_keys,
                )
            except Exception as exc:  # pragma: no cover - defensive branch
                logger.error("Runtime scheduler reconcile failed: %s", exc, exc_info=True)
                warnings.append("Configuration updated but runtime scheduler reconcile failed")

        return {
            "success": True,
            "config_version": new_version,
            "applied_count": len(updated_keys),
            "skipped_masked_count": len(skipped_masked_keys),
            "reload_triggered": reload_triggered,
            "updated_keys": updated_keys,
            "warnings": warnings,
        }

    def _build_explainability_warnings(
        self,
        *,
        submitted_keys: Set[str],
        reload_now: bool,
    ) -> List[str]:
        """Append user-facing runtime explainability warnings for key settings."""
        warnings: List[str] = []
        if not submitted_keys:
            return warnings

        current_map = self._manager.read_config_map()

        if submitted_keys & {"NEWS_MAX_AGE_DAYS", "NEWS_STRATEGY_PROFILE"}:
            raw_profile = current_map.get("NEWS_STRATEGY_PROFILE", "short")
            profile = normalize_news_strategy_profile(raw_profile)
            try:
                max_age = max(1, int(current_map.get("NEWS_MAX_AGE_DAYS", "3") or "3"))
            except (TypeError, ValueError):
                max_age = 3
            effective_days = resolve_news_window_days(
                news_max_age_days=max_age,
                news_strategy_profile=profile,
            )
            warnings.append(
                (
                    "新闻窗口已按策略计算："
                    f"NEWS_STRATEGY_PROFILE={profile}, "
                    f"NEWS_MAX_AGE_DAYS={max_age}, "
                    f"effective_days={effective_days} "
                    "(effective_days=min(profile_days, NEWS_MAX_AGE_DAYS))."
                )
            )

        if "MAX_WORKERS" in submitted_keys:
            try:
                max_workers = max(1, int(current_map.get("MAX_WORKERS", "3") or "3"))
            except (TypeError, ValueError):
                max_workers = 3
            if reload_now:
                warnings.append(
                    (
                        f"MAX_WORKERS={max_workers} 已保存。任务队列空闲时会自动应用；"
                        "若当前存在运行中任务，将在队列空闲后生效。"
                    )
                )
            else:
                warnings.append(
                    (
                        f"MAX_WORKERS={max_workers} 已写入 .env，但本次未触发运行时重载"
                        "（reload_now=false）；重载后才会应用。"
                    )
                )

        startup_only_run_keys = submitted_keys & {
            "RUN_IMMEDIATELY",
        }
        if startup_only_run_keys:
            warnings.append(
                (
                    f"{', '.join(sorted(startup_only_run_keys))} 已写入 .env。"
                    "它属于启动期单次运行配置：当前已运行的 WebUI/API 进程不会因为本次保存立即触发分析；"
                    "请重启当前进程后，在非 schedule 模式下按新值生效。"
                )
            )

        startup_only_schedule_keys = submitted_keys & {
            "SCHEDULE_RUN_IMMEDIATELY",
        }
        if startup_only_schedule_keys:
            warnings.append(
                (
                    f"{', '.join(sorted(startup_only_schedule_keys))} 已写入 .env。"
                    "这些属于启动期调度模式配置：当前已运行的 WebUI/API 进程不会因为本次保存启动、"
                    "停止或重建 scheduler；请重启当前进程，并以 schedule 模式重新启动后生效。"
                )
            )

        if "SCHEDULE_ENABLED" in submitted_keys:
            schedule_enabled = (current_map.get("SCHEDULE_ENABLED", "false") or "false").strip().lower()
            warnings.append(
                (
                    f"SCHEDULE_ENABLED={schedule_enabled} 已写入 .env。"
                    "如果当前进程是 WebUI/API/Desktop 长运行进程，runtime scheduler 会按新配置启停；"
                    "CLI schedule 模式仍按启动参数和配置运行。"
                )
            )

        if "SCHEDULE_TIMES" in submitted_keys:
            schedule_times = (current_map.get("SCHEDULE_TIMES", "") or "").strip()
            schedule_time = (current_map.get("SCHEDULE_TIME", "") or "").strip() or "18:00"
            effective = schedule_times or schedule_time
            warnings.append(
                (
                    f"SCHEDULE_TIMES={effective} 已写入 .env。"
                    "有效时间点会去重、排序；为空时继续使用 SCHEDULE_TIME。"
                    "如果当前进程存在 runtime scheduler，会按新时间重建 daily jobs。"
                )
            )

        if "SCHEDULE_TIME" in submitted_keys:
            schedule_time = (current_map.get("SCHEDULE_TIME", "") or "").strip() or "18:00"
            warnings.append(
                (
                    f"SCHEDULE_TIME={schedule_time} 已写入 .env。"
                    "如果当前进程已经以 schedule 模式运行，scheduler 会在下一轮检查中自动重建 daily job；"
                    "如果当前进程未以 schedule 模式运行，本次保存不会启动 scheduler。"
                )
            )

        startup_only_bind_keys = submitted_keys & {
            "WEBUI_HOST",
            "WEBUI_PORT",
        }
        if startup_only_bind_keys:
            warnings.append(
                (
                    f"{', '.join(sorted(startup_only_bind_keys))} 已写入 .env。"
                    "这些属于启动期监听配置：当前已运行的 WebUI/API 进程不会因为本次保存重新绑定监听地址或端口；"
                    "请重启当前进程、Docker 容器或服务管理器后生效。"
                )
            )

        return warnings

    @staticmethod
    def _build_runtime_model_cleanup_warnings(
        *,
        previous_map: Dict[str, str],
        updates: Dict[str, str],
    ) -> List[str]:
        """Explain when save payload clears stale runtime model references."""
        runtime_labels = {
            "LITELLM_MODEL": "主模型",
            "AGENT_LITELLM_MODEL": "Agent 主模型",
            "VISION_MODEL": "Vision 模型",
        }
        cleared_labels: List[str] = []
        for key, label in runtime_labels.items():
            if previous_map.get(key, "").strip() and key in updates and not updates[key].strip():
                cleared_labels.append(label)

        removed_fallbacks: List[str] = []
        if "LITELLM_FALLBACK_MODELS" in updates:
            previous_fallbacks = [
                item.strip()
                for item in previous_map.get("LITELLM_FALLBACK_MODELS", "").split(",")
                if item.strip()
            ]
            next_fallbacks = {
                item.strip()
                for item in updates["LITELLM_FALLBACK_MODELS"].split(",")
                if item.strip()
            }
            removed_fallbacks = [item for item in previous_fallbacks if item not in next_fallbacks]

        if not cleared_labels and not removed_fallbacks:
            return []

        cleaned_targets = list(cleared_labels)
        if removed_fallbacks:
            cleaned_targets.append("备选模型中的失效项")

        cleaned_text = " / ".join(cleaned_targets)
        warning = (
            f"检测到已同步清理失效的运行时模型引用：{cleaned_text}。"
            "如需恢复，请先补回对应渠道模型列表后重新选择；"
            "也可用桌面端导出备份或手动 .env 还原之前的 LLM_* / "
            "LITELLM_MODEL / AGENT_LITELLM_MODEL / VISION_MODEL / LLM_TEMPERATURE。"
        )
        return [warning]

    @staticmethod
    def _build_hermes_unsupported_key_cleanup_warnings(
        *,
        previous_map: Dict[str, str],
        updates: Dict[str, str],
    ) -> List[str]:
        """Explain when Hermes save clears unsupported Phase 3 key/header fields."""
        unsupported_labels = {
            "LLM_HERMES_API_KEYS": "LLM_HERMES_API_KEYS",
            "LLM_HERMES_EXTRA_HEADERS": "LLM_HERMES_EXTRA_HEADERS",
        }
        cleared = [
            label
            for key, label in unsupported_labels.items()
            if previous_map.get(key, "").strip() and key in updates and not updates[key].strip()
        ]
        if not cleared:
            return []

        return [
            (
                "检测到已清理 Hermes Phase 3 不支持的配置项："
                f"{', '.join(cleared)}。"
                "Hermes reserved channel 只支持单个 LLM_HERMES_API_KEY，不支持多 Key 或额外 Header；"
                "如需恢复旧值，请从 .env 备份、Git 历史或桌面端导出备份手动还原，"
                "但非空 LLM_HERMES_API_KEYS / LLM_HERMES_EXTRA_HEADERS 仍会被后端校验拒绝。"
            )
        ]

    def apply_simple_updates(
        self,
        updates: Sequence[Tuple[str, str]],
        mask_token: str = "******",
    ) -> None:
        """Apply raw key updates without validation (internal service use only)."""
        self._manager.apply_updates(
            updates=updates,
            sensitive_keys=set(),
            mask_token=mask_token,
        )

    @staticmethod
    def _parse_imported_env_content(content: str) -> List[Dict[str, str]]:
        """Parse raw `.env` text into update items without expanding app templates."""
        normalized_content = content.replace("\ufeff", "")
        if not normalized_content.strip():
            raise ConfigImportError("未识别到有效 .env 配置")

        from dotenv import dotenv_values

        parsed = dotenv_values(stream=io.StringIO(normalized_content), interpolate=False)
        updates: List[Dict[str, str]] = []
        for key, value in parsed.items():
            if key is None:
                continue
            updates.append(
                {
                    "key": str(key).upper(),
                    "value": "" if value is None else str(value),
                }
            )

        if not updates:
            raise ConfigImportError("未识别到有效 .env 配置")

        return updates

    def _collect_issues(self, items: Sequence[Dict[str, str]], mask_token: str) -> List[Dict[str, Any]]:
        """Collect field-level and cross-field validation issues."""
        saved_config_map = self._manager.read_config_map()
        display_config_map = self._build_display_config_map(saved_config_map)
        runtime_config_map = self._build_runtime_display_config_map(display_config_map)
        effective_map = {
            **runtime_config_map,
            **display_config_map,
        }
        issues: List[Dict[str, Any]] = []
        updated_map: Dict[str, str] = {}

        for item in items:
            key = item["key"].upper()
            value = item["value"]
            field_schema = get_field_definition(key, value)
            is_sensitive = bool(field_schema.get("is_sensitive", False))

            if is_sensitive and value == mask_token and saved_config_map.get(key):
                continue

            updated_map[key] = value
            effective_map[key] = value
            issues.extend(self._validate_value(key=key, value=value, field_schema=field_schema))

        issues.extend(self._validate_cross_field(effective_map=effective_map, updated_keys=set(updated_map.keys())))
        return issues

    @classmethod
    def _is_generation_backend_status_key(cls, key: str) -> bool:
        normalized = str(key or "").strip().upper()
        return (
            normalized in cls._GENERATION_BACKEND_STATUS_EXACT_KEYS
            or normalized == "LLM_CHANNELS"
            or bool(cls._GENERATION_BACKEND_STATUS_LLM_CHANNEL_RE.fullmatch(normalized))
        )

    @classmethod
    def _filter_generation_backend_items(
        cls,
        items: Sequence[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        filtered: List[Dict[str, str]] = []
        for item in items:
            key = str(item.get("key", "")).strip().upper()
            if not key or not cls._is_generation_backend_status_key(key):
                continue
            filtered.append({"key": key, "value": "" if item.get("value") is None else str(item.get("value"))})
        return filtered

    @classmethod
    def _filter_agent_backend_items(
        cls,
        items: Sequence[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        return [
            {
                "key": str(item.get("key", "")).strip().upper(),
                "value": "" if item.get("value") is None else str(item.get("value")),
            }
            for item in items
            if (
                str(item.get("key", "")).strip().upper() in cls._AGENT_BACKEND_STATUS_EXACT_KEYS
                or cls._is_generation_backend_status_key(
                    str(item.get("key", "")).strip().upper()
                )
            )
        ]

    def _collect_generation_backend_issues(
        self,
        *,
        items: Sequence[Dict[str, str]],
        mask_token: str,
    ) -> List[Dict[str, Any]]:
        """Collect only config issues that affect generation backend status/smoke."""
        issues = self._collect_issues(
            items=self._filter_generation_backend_items(items),
            mask_token=mask_token,
        )
        effective_map = self._build_generation_backend_effective_map(
            items=items,
            mask_token=mask_token,
        )
        issues.extend(self._validate_generation_backend_litellm_runtime_source(effective_map))
        return [
            issue for issue in issues
            if self._is_generation_backend_status_key(str(issue.get("key", "")))
        ]

    @staticmethod
    def _validate_generation_backend_litellm_runtime_source(effective_map: Dict[str, str]) -> List[Dict[str, Any]]:
        """Validate explicit LiteLLM models when no route list can back them."""
        primary_backend = normalize_backend_id(
            effective_map.get("GENERATION_BACKEND"),
            default=LITELLM_BACKEND_ID,
        )
        fallback_backend = (
            LITELLM_BACKEND_ID
            if "GENERATION_FALLBACK_BACKEND" not in effective_map
            else (effective_map.get("GENERATION_FALLBACK_BACKEND") or "").strip().lower()
        )
        litellm_selected = (
            primary_backend == LITELLM_BACKEND_ID
            or (fallback_backend == LITELLM_BACKEND_ID and primary_backend != LITELLM_BACKEND_ID)
        )
        if not litellm_selected:
            return []
        if _uses_litellm_yaml(effective_map):
            return []
        if _collect_llm_channel_models_from_map(effective_map):
            return []
        if (effective_map.get("LLM_CHANNELS") or "").strip():
            return []

        issues: List[Dict[str, Any]] = []
        primary_model = (effective_map.get("LITELLM_MODEL") or "").strip()
        if primary_model and not _has_runtime_source_for_model(primary_model, effective_map):
            issues.append(
                {
                    "key": "LITELLM_MODEL",
                    "code": "missing_runtime_source",
                    "message": (
                        "A primary model is selected, but no usable runtime source was found. "
                        "Configure a matching provider API key, LLM channel, or LiteLLM YAML route."
                    ),
                    "severity": "error",
                    "expected": "matching provider API key, enabled channel model, or YAML model",
                    "actual": primary_model,
                }
            )

        fallback_models = [
            model.strip()
            for model in (effective_map.get("LITELLM_FALLBACK_MODELS") or "").split(",")
            if model.strip()
        ]
        invalid_fallbacks = [
            model for model in fallback_models
            if not _has_runtime_source_for_model(model, effective_map)
        ]
        if invalid_fallbacks:
            issues.append(
                {
                    "key": "LITELLM_FALLBACK_MODELS",
                    "code": "missing_runtime_source",
                    "message": (
                        "Some fallback models do not have a matching provider API key, "
                        "enabled channel, or LiteLLM YAML route."
                    ),
                    "severity": "error",
                    "expected": "matching provider API key, enabled channel model, or YAML model",
                    "actual": ", ".join(invalid_fallbacks[:3]),
                }
            )
        return issues

    def _collect_generation_backend_issues_from_map(
        self,
        effective_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        items = [
            {"key": key, "value": value}
            for key, value in effective_map.items()
            if self._is_generation_backend_status_key(key)
        ]
        return self._collect_generation_backend_issues(items=items, mask_token="******")

    @staticmethod
    def _validate_value(key: str, value: str, field_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return ConfigValueValidator(_get_config_probe_port).validate_value(key=key, value=value, field_schema=field_schema)

    _normalize_value_for_storage = staticmethod(ConfigValueValidator.normalize_value_for_storage)

    def _build_notification_test_effective_map(
        self,
        *,
        items: Sequence[Dict[str, str]],
        mask_token: str,
    ) -> Dict[str, str]:
        """Merge saved/runtime config with unsaved notification test items."""
        allowed_keys = set(self._NOTIFICATION_TEST_KEY_MAP)
        effective = {
            key: value
            for key, value in self._build_display_config_map(self._manager.read_config_map()).items()
            if key in allowed_keys
        }

        for raw_key, raw_value in os.environ.items():
            key = str(raw_key).upper()
            if key in allowed_keys:
                effective[key] = "" if raw_value is None else str(raw_value)

        for item in items:
            key = str(item.get("key", "")).strip().upper()
            if key not in allowed_keys:
                continue
            value = "" if item.get("value") is None else str(item.get("value"))
            if value == mask_token:
                continue
            effective[key] = value

        return effective


    @staticmethod
    def _is_setup_relevant_env_key(key: str) -> bool:
        if key in {
            "STOCK_LIST",
            "DATABASE_PATH",
            "LITELLM_CONFIG",
            "LITELLM_MODEL",
            "LITELLM_FALLBACK_MODELS",
            "AGENT_LITELLM_MODEL",
            "VISION_MODEL",
            "OPENAI_BASE_URL",
            "OLLAMA_API_BASE",
            "FEISHU_STREAM_ENABLED",
        }:
            return True
        prefixes = (
            "LLM_",
            "GEMINI_",
            "OPENAI_",
            "ANTHROPIC_",
            "DEEPSEEK_",
            "OLLAMA_",
            "FEISHU_",
            "TELEGRAM_",
            "EMAIL_",
            "DISCORD_",
            "SLACK_",
            "DINGTALK_",
            "WECHAT_",
            "PUSHOVER_",
            "NTFY_",
            "GOTIFY_",
            "PUSHPLUS_",
            "SERVERCHAN",
            "CUSTOM_WEBHOOK",
            "WECOM_",
            "ASTRBOT_",
        )
        return key.startswith(prefixes) or key.endswith("_API_KEY") or key.endswith("_API_KEYS")

    def _build_setup_effective_config_map(self) -> Dict[str, str]:
        """Combine saved `.env` values with injected runtime env values for status checks."""
        saved_map = self._build_display_config_map(self._manager.read_config_map())
        effective_map = dict(saved_map)
        registered_keys = {key.upper() for key in get_registered_field_keys()}

        for raw_key, raw_value in os.environ.items():
            key = str(raw_key).upper()
            value = "" if raw_value is None else str(raw_value)
            if key in registered_keys or self._is_setup_relevant_env_key(key):
                effective_map[key] = value

        return self._build_display_config_map(effective_map)

    def _build_generation_backend_base_map(self) -> Dict[str, str]:
        """Build generation backend status config with saved values taking precedence."""
        saved_map = self._build_display_config_map(self._manager.read_config_map())
        effective_map = dict(saved_map)
        registered_keys = {key.upper() for key in get_registered_field_keys()}

        for raw_key, raw_value in os.environ.items():
            key = str(raw_key).upper()
            if key in effective_map:
                continue
            value = "" if raw_value is None else str(raw_value)
            if key in registered_keys or self._is_setup_relevant_env_key(key):
                effective_map[key] = value

        return self._build_display_config_map(effective_map)

    def _build_generation_backend_effective_map(
        self,
        *,
        items: Sequence[Dict[str, str]],
        mask_token: str,
    ) -> Dict[str, str]:
        """Merge saved/runtime config with unsaved status/smoke preview items."""
        effective_map = self._build_generation_backend_base_map()
        saved_map = self._build_display_config_map(self._manager.read_config_map())

        for item in self._filter_generation_backend_items(items):
            key = str(item.get("key", "")).strip().upper()
            if not key:
                continue
            value = "" if item.get("value") is None else str(item.get("value"))
            field_schema = get_field_definition(key, value)
            if bool(field_schema.get("is_sensitive", False)) and value == mask_token:
                if key in saved_map:
                    continue
            effective_map[key] = value

        return self._build_display_config_map(effective_map)

    def _build_agent_backend_effective_map(
        self,
        *,
        items: Sequence[Dict[str, str]],
        mask_token: str,
    ) -> Dict[str, str]:
        """Overlay Agent backend draft fields on the runtime-effective config."""
        effective_map = self._build_setup_effective_config_map()
        runtime_config = Config.get_instance()
        effective_map.update(
            {
                "AGENT_BACKEND": runtime_config.agent_backend,
                "AGENT_GENERATION_BACKEND": runtime_config.agent_generation_backend,
                "AGENT_LITELLM_MODEL": runtime_config.agent_litellm_model,
                "AGENT_ARCH": runtime_config.agent_arch,
                "AGENT_ORCHESTRATOR_TIMEOUT_S": str(
                    runtime_config.agent_orchestrator_timeout_s
                ),
            }
        )
        if runtime_config.agent_mode_explicit:
            effective_map["AGENT_MODE"] = "true" if runtime_config.agent_mode else "false"
        else:
            effective_map.pop("AGENT_MODE", None)
        saved_map = self._build_display_config_map(self._manager.read_config_map())
        for item in self._filter_agent_backend_items(items):
            key = item["key"]
            value = item["value"]
            field_schema = get_field_definition(key, value)
            if bool(field_schema.get("is_sensitive", False)) and value == mask_token and key in saved_map:
                continue
            effective_map[key] = value
        return self._build_display_config_map(effective_map)


    _build_llm_channel_result = staticmethod(_build_llm_channel_result)

    _merge_llm_diagnostic_details = staticmethod(_merge_llm_diagnostic_details)

    _build_redaction_values = staticmethod(_build_redaction_values)

    _comma_flexible_secret_pattern = staticmethod(_comma_flexible_secret_pattern)

    _sanitize_llm_error_text = staticmethod(_sanitize_llm_error_text)

    _sanitize_llm_details = staticmethod(_sanitize_llm_details)

    _sanitize_llm_value = staticmethod(_sanitize_llm_value)

    _classify_llm_http_error = staticmethod(_classify_llm_http_error)

    _classify_llm_exception = staticmethod(_classify_llm_exception)

    _extract_llm_completion_content = staticmethod(_extract_llm_completion_content)

    _extract_llm_discovery_error = staticmethod(_extract_llm_discovery_error)

    _extract_discovered_llm_models = staticmethod(_extract_discovered_llm_models)

    _validate_cross_field = staticmethod(ConfigValueValidator.validate_cross_field)
