# -*- coding: utf-8 -*-
"""LLM 渠道与运行时选择校验（W5.4）。

从 ``system_config_service.py`` 迁出的模块级规则：把 ``.env`` 键值映射
（``effective_map``）解释为 LLM 渠道 / 模型选择，并给出结构化 issue 列表。
本模块不持有 service 状态，也不做网络外调：只消费映射、配置模型列表与
URL 安全规则，供 ``SystemConfigService`` 在保存前校验与解释性告警中复用。

边界：渠道探测（真实请求）、通知试发、单例重置仍在 service / 端口 seam 内。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from src.config import (
    ANSPIRE_LLM_BASE_URL_DEFAULT,
    ANSPIRE_LLM_MODEL_DEFAULT,
    SUPPORTED_LLM_CHANNEL_PROTOCOLS,
    Config,
    _get_litellm_provider,
    _uses_direct_env_provider,
    canonicalize_llm_channel_protocol,
    channel_allows_empty_api_key,
    get_configured_llm_models,
    normalize_agent_litellm_model,
    normalize_llm_channel_model,
    parse_env_bool,
    resolve_llm_channel_protocol,
)
from src.domain.generation.hermes_rules import (
    HERMES_DEFAULT_BASE_URL,
    HERMES_DEFAULT_MODEL,
    HERMES_DEFAULT_PROTOCOL,
    is_reserved_hermes_name,
    parse_hermes_channel,
    route_identity_candidates,
)
from src.domain.shared.url_security import _is_safe_base_url, _is_valid_llm_base_url

@dataclass(frozen=True)
class _LLMDiagnostic:
    """Internal structured diagnosis for LLM test and discovery failures."""

    error_code: str
    retryable: bool
    message: str
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ── SystemConfigService 私有静态规则（§4.3 拆分 F1：自类体内收口为模块级纯函数，
#    消除对外层守卫 forbid_private_members 的跨对象私有访问；行为逐字不变。）────

def _validate_numeric_range(key: str, numeric_value: float, validation: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    min_value = validation.get("min")
    max_value = validation.get("max")

    if min_value is not None and numeric_value < min_value:
        issues.append(
            {
                "key": key,
                "code": "out_of_range",
                "message": "Value is lower than minimum",
                "severity": "error",
                "expected": f">={min_value}",
                "actual": str(numeric_value),
            }
        )
    if max_value is not None and numeric_value > max_value:
        issues.append(
            {
                "key": key,
                "code": "out_of_range",
                "message": "Value is greater than maximum",
                "severity": "error",
                "expected": f"<={max_value}",
                "actual": str(numeric_value),
            }
        )
    return issues


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _anspire_legacy_llm_enabled(effective_map: Dict[str, str]) -> bool:
    if not parse_env_bool(effective_map.get("ANSPIRE_LLM_ENABLED"), default=True):
        return False
    for name in _split_csv(effective_map.get("LLM_CHANNELS") or ""):
        if name.strip().lower() != "anspire":
            continue
        enabled_raw = effective_map.get("LLM_ANSPIRE_ENABLED")
        if not (enabled_raw or "").strip():
            enabled_raw = effective_map.get("ANSPIRE_LLM_ENABLED")
        return parse_env_bool(enabled_raw, default=True)
    return True


def _has_model_not_found_signal(text: str) -> bool:
    lowered = text.lower()

    model_candidates = [
        re.search(r"model\s+not\s+found\s*[:：]?\s*[`\"']?\s*([a-z0-9._/-]{2,})", lowered),
        re.search(r"model\s*[`\"']?\s*([a-z0-9._/-]{2,})\s*[`\"']?\s+does\s+not\s+exist", lowered),
        re.search(r"model\s+does\s+not\s+exist\s*[:：]?\s*[`\"']?\s*([a-z0-9._/-]{2,})", lowered),
        re.search(r"unknown\s+model\s*[:：]?\s*[`\"']?\s*([a-z0-9._/-]{2,})", lowered),
        re.search(r"no\s+such\s+model\s*[:：]?\s*[`\"']?\s*([a-z0-9._/-]{2,})", lowered),
    ]

    for match in model_candidates:
        if not match:
            continue
        model_id = match.group(1).strip()
        if model_id and not model_id.startswith("/") and "http" not in model_id:
            return True

    return False


def _has_model_access_denied_signal(text: str) -> bool:
    lowered = text.lower()
    if "model" not in lowered:
        return False

    # Best-effort classifier for observed provider messages. Keep it gated by
    # an explicit "model" mention plus access/disabled/unavailable signals so
    # unrelated provider-specific failures continue to use the fallback path.
    access_denied_tokens = (
        "not authorized",
        "not allowed",
        "access denied",
        "permission denied",
        "model disabled",
        "model is disabled",
        "disabled model",
        "model has been disabled",
        "model not enabled",
        "model not available",
        "model is not available",
    )
    return any(token in lowered for token in access_denied_tokens)


def _has_request_blocked_signal(text: str) -> bool:
    lowered = text.lower()
    if _has_transport_blocked_signal(lowered):
        return False
    blocked_tokens = (
        "your request was blocked",
        "the request was blocked",
        "request blocked by policy",
        "blocked by policy",
        "blocked due to policy",
        "moderation_blocked",
        "policy_blocked",
        "请求被拦截",
    )
    return any(token in lowered for token in blocked_tokens)


def _has_transport_blocked_signal(text: str) -> bool:
    lowered = text.lower()
    transport_tokens = (
        "connection blocked",
        "connection request was blocked",
        "network blocked",
        "blocked by network policy",
        "blocked by firewall",
        "firewall blocked",
    )
    return any(token in lowered for token in transport_tokens)


def _has_provider_prefix_mismatch_signal(text: str) -> bool:
    lowered = text.lower()
    mismatch_tokens = (
        "provider prefix",
        "llm provider not provided",
        "invalid provider",
        "unknown provider",
        "custom_llm_provider",
        "not a valid llm provider",
    )
    return any(token in lowered for token in mismatch_tokens)


def _validate_llm_channel_map(effective_map: Dict[str, str], updated_keys: Set[str]) -> List[Dict[str, Any]]:
    """Validate channel-style LLM configuration stored in `.env`."""
    issues: List[Dict[str, Any]] = []
    if _uses_litellm_yaml(effective_map):
        return issues

    raw_channels = (effective_map.get("LLM_CHANNELS") or "").strip()
    if not raw_channels:
        return issues

    normalized_names: List[str] = []
    seen_names: Set[str] = set()
    for raw_name in raw_channels.split(","):
        name = raw_name.strip()
        if not name:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            issues.append(
                {
                    "key": "LLM_CHANNELS",
                    "code": "invalid_channel_name",
                    "message": f"LLM channel name '{name}' may only contain letters, numbers, and underscores",
                    "severity": "error",
                    "expected": "letters/numbers/underscores",
                    "actual": name,
                }
            )
            continue

        normalized_upper = name.upper()
        if normalized_upper in seen_names:
            issues.append(
                {
                    "key": "LLM_CHANNELS",
                    "code": "duplicate_channel_name",
                    "message": f"LLM channel '{name}' is declared more than once",
                    "severity": "error",
                    "expected": "unique channel names",
                    "actual": raw_channels,
                }
            )
            continue

        seen_names.add(normalized_upper)
        normalized_names.append(name)

    for name in normalized_names:
        prefix = f"LLM_{name.upper()}"
        protocol_value = (effective_map.get(f"{prefix}_PROTOCOL") or "").strip()
        if name.lower() == "anspire" and not protocol_value:
            protocol_value = "openai"
        base_url_value = (effective_map.get(f"{prefix}_BASE_URL") or "").strip()
        if name.lower() == "anspire" and not base_url_value:
            base_url_value = (
                effective_map.get("ANSPIRE_LLM_BASE_URL")
                or ANSPIRE_LLM_BASE_URL_DEFAULT
            ).strip()
        api_key_value = (
            (effective_map.get(f"{prefix}_API_KEYS") or "").strip()
            or (effective_map.get(f"{prefix}_API_KEY") or "").strip()
        )
        if name.lower() == "anspire" and not api_key_value:
            api_key_value = (effective_map.get("ANSPIRE_API_KEYS") or "").strip()
        models_value = [
            model.strip()
            for model in (effective_map.get(f"{prefix}_MODELS") or "").split(",")
            if model.strip()
        ]
        if name.lower() == "anspire" and not models_value:
            models_value = [
                (
                    effective_map.get("ANSPIRE_LLM_MODEL")
                    or ANSPIRE_LLM_MODEL_DEFAULT
                ).strip()
            ]
        enabled_raw = effective_map.get(f"{prefix}_ENABLED")
        if name.lower() == "anspire" and not (enabled_raw or "").strip():
            enabled_raw = effective_map.get("ANSPIRE_LLM_ENABLED")
        enabled = parse_env_bool(enabled_raw, default=True)
        if is_reserved_hermes_name(name):
            result = parse_hermes_channel(
                enabled=enabled,
                protocol=protocol_value or HERMES_DEFAULT_PROTOCOL,
                base_url=base_url_value or HERMES_DEFAULT_BASE_URL,
                api_key=(effective_map.get(f"{prefix}_API_KEY") or "").strip(),
                api_keys_raw=(effective_map.get(f"{prefix}_API_KEYS") or "").strip(),
                extra_headers_raw=(effective_map.get(f"{prefix}_EXTRA_HEADERS") or "").strip(),
                models=models_value or [HERMES_DEFAULT_MODEL],
            )
            for issue in result.issues:
                issues.append(
                    {
                        "key": issue.field,
                        "code": issue.code,
                        "message": issue.message,
                        "severity": issue.severity,
                        "expected": "valid reserved Hermes channel",
                        "actual": "",
                    }
                )
            continue
        issues.extend(
            _validate_llm_channel_definition(
                channel_name=name,
                protocol_value=protocol_value,
                base_url_value=base_url_value,
                api_key_value=api_key_value,
                model_values=models_value,
                enabled=enabled,
                field_prefix=prefix,
                require_complete=enabled,
            )
        )

    return issues


def _collect_llm_channel_models_from_map(effective_map: Dict[str, str]) -> List[str]:
    """Collect normalized model names from channel-style env values."""
    raw_channels = (effective_map.get("LLM_CHANNELS") or "").strip()
    if not raw_channels:
        return []

    models: List[str] = []
    seen: Set[str] = set()
    for raw_name in raw_channels.split(","):
        name = raw_name.strip()
        if not name:
            continue

        prefix = f"LLM_{name.upper()}"
        enabled_raw = effective_map.get(f"{prefix}_ENABLED")
        if name.lower() == "anspire" and not (enabled_raw or "").strip():
            enabled_raw = effective_map.get("ANSPIRE_LLM_ENABLED")
        enabled = parse_env_bool(enabled_raw, default=True)
        if not enabled:
            continue

        base_url_value = (effective_map.get(f"{prefix}_BASE_URL") or "").strip()
        if name.lower() == "anspire" and not base_url_value:
            base_url_value = (
                effective_map.get("ANSPIRE_LLM_BASE_URL")
                or ANSPIRE_LLM_BASE_URL_DEFAULT
            ).strip()
        protocol_value = (effective_map.get(f"{prefix}_PROTOCOL") or "").strip()
        if name.lower() == "anspire" and not protocol_value:
            protocol_value = "openai"
        raw_models = [
            model.strip()
            for model in (effective_map.get(f"{prefix}_MODELS") or "").split(",")
            if model.strip()
        ]
        if name.lower() == "anspire" and not raw_models:
            raw_models = [
                (
                    effective_map.get("ANSPIRE_LLM_MODEL")
                    or ANSPIRE_LLM_MODEL_DEFAULT
                ).strip()
            ]
        if is_reserved_hermes_name(name):
            result = parse_hermes_channel(
                enabled=True,
                protocol=protocol_value or HERMES_DEFAULT_PROTOCOL,
                base_url=base_url_value or HERMES_DEFAULT_BASE_URL,
                api_key=(effective_map.get(f"{prefix}_API_KEY") or "").strip(),
                api_keys_raw=(effective_map.get(f"{prefix}_API_KEYS") or "").strip(),
                extra_headers_raw=(effective_map.get(f"{prefix}_EXTRA_HEADERS") or "").strip(),
                models=raw_models or [HERMES_DEFAULT_MODEL],
            )
            channel = result.channel or {}
            for model in channel.get("models") or []:
                if model and model not in seen:
                    seen.add(model)
                    models.append(model)
            continue
        resolved_protocol = resolve_llm_channel_protocol(protocol_value, base_url=base_url_value, models=raw_models, channel_name=name)
        for model in raw_models:
            normalized_model = normalize_llm_channel_model(model, resolved_protocol, base_url_value)
            if not normalized_model or normalized_model in seen:
                continue
            seen.add(normalized_model)
            models.append(normalized_model)

    return models


def _collect_hermes_channel_models_from_map(effective_map: Dict[str, str]) -> List[str]:
    """Collect valid reserved Hermes route aliases from channel-style env values."""
    raw_channels = (effective_map.get("LLM_CHANNELS") or "").strip()
    if not raw_channels:
        return []

    models: List[str] = []
    seen: Set[str] = set()
    for raw_name in raw_channels.split(","):
        name = raw_name.strip()
        if not is_reserved_hermes_name(name):
            continue

        prefix = f"LLM_{name.upper()}"
        enabled = parse_env_bool(effective_map.get(f"{prefix}_ENABLED"), default=True)
        if not enabled:
            continue

        raw_models = _split_csv(effective_map.get(f"{prefix}_MODELS") or "")
        result = parse_hermes_channel(
            enabled=True,
            protocol=(effective_map.get(f"{prefix}_PROTOCOL") or HERMES_DEFAULT_PROTOCOL).strip(),
            base_url=(effective_map.get(f"{prefix}_BASE_URL") or HERMES_DEFAULT_BASE_URL).strip(),
            api_key=(effective_map.get(f"{prefix}_API_KEY") or "").strip(),
            api_keys_raw=(effective_map.get(f"{prefix}_API_KEYS") or "").strip(),
            extra_headers_raw=(effective_map.get(f"{prefix}_EXTRA_HEADERS") or "").strip(),
            models=raw_models or [HERMES_DEFAULT_MODEL],
        )
        channel = result.channel or {}
        for model in channel.get("models") or []:
            if model and model not in seen:
                seen.add(model)
                models.append(model)
    return models


def _collect_non_hermes_channel_models_from_map(effective_map: Dict[str, str]) -> List[str]:
    """Collect enabled non-Hermes channel route aliases from channel-style env values."""
    raw_channels = (effective_map.get("LLM_CHANNELS") or "").strip()
    if not raw_channels:
        return []
    models: List[str] = []
    seen: Set[str] = set()
    for raw_name in raw_channels.split(","):
        name = raw_name.strip()
        if not name or is_reserved_hermes_name(name):
            continue
        prefix = f"LLM_{name.upper()}"
        enabled_raw = effective_map.get(f"{prefix}_ENABLED")
        if name.lower() == "anspire" and not (enabled_raw or "").strip():
            enabled_raw = effective_map.get("ANSPIRE_LLM_ENABLED")
        if not parse_env_bool(enabled_raw, default=True):
            continue
        base_url_value = (effective_map.get(f"{prefix}_BASE_URL") or "").strip()
        if name.lower() == "anspire" and not base_url_value:
            base_url_value = (
                effective_map.get("ANSPIRE_LLM_BASE_URL")
                or ANSPIRE_LLM_BASE_URL_DEFAULT
            ).strip()
        protocol_value = (effective_map.get(f"{prefix}_PROTOCOL") or "").strip()
        if name.lower() == "anspire" and not protocol_value:
            protocol_value = "openai"
        raw_models = _split_csv(effective_map.get(f"{prefix}_MODELS") or "")
        if name.lower() == "anspire" and not raw_models:
            raw_models = [
                (
                    effective_map.get("ANSPIRE_LLM_MODEL")
                    or ANSPIRE_LLM_MODEL_DEFAULT
                ).strip()
            ]
        resolved_protocol = resolve_llm_channel_protocol(
            protocol_value,
            base_url=base_url_value,
            models=raw_models,
            channel_name=name,
        )
        for raw_model in raw_models:
            model = normalize_llm_channel_model(raw_model, resolved_protocol, base_url_value)
            if model and model not in seen:
                seen.add(model)
                models.append(model)
    return models


def _collect_mixed_hermes_routes_from_map(effective_map: Dict[str, str]) -> Set[str]:
    hermes_routes = set(_collect_hermes_channel_models_from_map(effective_map))
    non_hermes_routes = set(_collect_non_hermes_channel_models_from_map(effective_map))
    return hermes_routes & non_hermes_routes


def _matches_route_set(model: str, routes: Set[str]) -> bool:
    """Loose safety match for Hermes/provenance checks, not normal route availability."""
    return bool(route_identity_candidates(model) & set(routes or set()))


def _matches_exact_route(model: str, routes: Set[str]) -> bool:
    """Match the Router's top-level model_name exactly for normal availability checks."""
    normalized_model = str(model or "").strip()
    return bool(normalized_model) and normalized_model in set(routes or set())


def _uses_litellm_yaml(effective_map: Dict[str, str]) -> bool:
    """Return True when a valid LiteLLM YAML config takes precedence over channels."""
    config_path = (effective_map.get("LITELLM_CONFIG") or "").strip()
    if not config_path:
        return False
    return bool(Config.parse_litellm_yaml(config_path))


def _collect_yaml_models_from_map(effective_map: Dict[str, str]) -> List[str]:
    """Collect declared router model names from LiteLLM YAML config."""
    config_path = (effective_map.get("LITELLM_CONFIG") or "").strip()
    if not config_path:
        return []
    return get_configured_llm_models(Config.parse_litellm_yaml(config_path))


def _has_legacy_key_for_provider(provider: str, effective_map: Dict[str, str]) -> bool:
    """Return True when legacy env config can still back the provider."""
    normalized_provider = canonicalize_llm_channel_protocol(provider)
    if normalized_provider in {"gemini", "vertex_ai"}:
        return bool(
            (effective_map.get("GEMINI_API_KEYS") or "").strip()
            or (effective_map.get("GEMINI_API_KEY") or "").strip()
        )
    if normalized_provider == "anthropic":
        return bool(
            (effective_map.get("ANTHROPIC_API_KEYS") or "").strip()
            or (effective_map.get("ANTHROPIC_API_KEY") or "").strip()
        )
    if normalized_provider == "deepseek":
        return bool(
            (effective_map.get("DEEPSEEK_API_KEYS") or "").strip()
            or (effective_map.get("DEEPSEEK_API_KEY") or "").strip()
        )
    if normalized_provider == "openai":
        return bool(
            (effective_map.get("OPENAI_API_KEYS") or "").strip()
            or (effective_map.get("AIHUBMIX_KEY") or "").strip()
            or (effective_map.get("OPENAI_API_KEY") or "").strip()
            or (
                _anspire_legacy_llm_enabled(effective_map)
                and (effective_map.get("ANSPIRE_API_KEYS") or "").strip()
            )
        )
    return False


def _has_runtime_source_for_model(model: str, effective_map: Dict[str, str]) -> bool:
    """Whether the selected model still has a backing runtime source."""
    if not model or _uses_direct_env_provider(model):
        return True
    provider = _get_litellm_provider(model)
    return _has_legacy_key_for_provider(provider, effective_map)


def _validate_llm_runtime_selection(effective_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """Validate selected primary/fallback/vision models against configured channels."""
    issues: List[Dict[str, Any]] = []

    available_models = (
        _collect_yaml_models_from_map(effective_map)
        or _collect_llm_channel_models_from_map(effective_map)
    )
    available_model_set = set(available_models)
    hermes_route_set = set(_collect_hermes_channel_models_from_map(effective_map))
    mixed_hermes_routes = _collect_mixed_hermes_routes_from_map(effective_map)
    if not available_model_set:
        raw_channels = (effective_map.get("LLM_CHANNELS") or "").strip()
        if not raw_channels:
            return issues

        configured_agent_model_raw = (effective_map.get("AGENT_LITELLM_MODEL") or "").strip()
        configured_agent_model = normalize_agent_litellm_model(
            configured_agent_model_raw,
            configured_models=available_model_set,
        )
        primary_model = (effective_map.get("LITELLM_MODEL") or "").strip()
        if primary_model and not _has_runtime_source_for_model(primary_model, effective_map):
            issues.append(
                {
                    "key": "LITELLM_MODEL",
                    "code": "missing_runtime_source",
                    "message": (
                        "A primary model is selected, but no usable runtime source was found. "
                        "Enable at least one channel with available models, or provide the "
                        "matching provider API key so the model can be resolved."
                    ),
                    "severity": "error",
                    "expected": "enabled channel model or matching legacy API key",
                    "actual": primary_model,
                }
            )

        if (
            configured_agent_model_raw
            and configured_agent_model
            and not _has_runtime_source_for_model(
                configured_agent_model,
                effective_map,
            )
        ):
            issues.append(
                {
                    "key": "AGENT_LITELLM_MODEL",
                    "code": "missing_runtime_source",
                    "message": (
                        "An Agent primary model is selected, but no usable runtime source was found. "
                        "Enable at least one channel with available models, or provide the "
                        "matching provider API key so the model can be resolved."
                    ),
                    "severity": "error",
                    "expected": "enabled channel model or matching legacy API key",
                    "actual": configured_agent_model,
                }
            )
        elif (
            configured_agent_model_raw
            and configured_agent_model
            and _matches_route_set(configured_agent_model, hermes_route_set)
            and not _matches_route_set(configured_agent_model, mixed_hermes_routes)
        ):
            issues.append(
                {
                    "key": "AGENT_LITELLM_MODEL",
                    "code": "explicit_agent_model_no_safe_deployment",
                    "message": (
                        "Hermes-only routes are not valid Agent models in Phase 3. "
                        "Choose a route with at least one non-Hermes deployment."
                    ),
                    "severity": "error",
                    "expected": "Agent-safe route with non-Hermes deployment",
                    "actual": configured_agent_model,
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
                        "Some fallback models do not have an enabled channel "
                        "or matching API key available"
                    ),
                    "severity": "error",
                    "expected": "enabled channel models or matching legacy API keys",
                    "actual": ", ".join(invalid_fallbacks[:3]),
                }
            )

        vision_model = (effective_map.get("VISION_MODEL") or "").strip()
        if vision_model and _matches_route_set(vision_model, hermes_route_set):
            issues.append(
                {
                    "key": "VISION_MODEL",
                    "code": "hermes_vision_unsupported",
                    "message": (
                        "Hermes routes are not valid Vision models in Phase 3. "
                        "Choose a pure non-Hermes Vision-capable route."
                    ),
                    "severity": "error",
                    "expected": "pure non-Hermes Vision route",
                    "actual": vision_model,
                }
            )
        elif vision_model and not _has_runtime_source_for_model(vision_model, effective_map):
            issues.append(
                {
                    "key": "VISION_MODEL",
                    "code": "missing_runtime_source",
                    "message": (
                        "A Vision model is selected, but there is no enabled channel "
                        "or matching API key available for it"
                    ),
                    "severity": "warning",
                    "expected": "enabled channel model or matching legacy API key",
                    "actual": vision_model,
                }
            )

        return issues

    primary_model = (effective_map.get("LITELLM_MODEL") or "").strip()
    if _matches_route_set(primary_model, mixed_hermes_routes):
        issues.append(
            {
                "key": "LITELLM_MODEL",
                "code": "mixed_hermes_route_unsupported",
                "message": (
                    "Mixed Hermes/non-Hermes generation routes are not supported in Phase 3. "
                    "Choose a pure Hermes or pure non-Hermes route."
                ),
                "severity": "error",
                "expected": "pure generation route",
                "actual": primary_model,
            }
        )
    if (
        primary_model
        and not _matches_exact_route(primary_model, available_model_set)
        and not _uses_direct_env_provider(primary_model)
    ):
        issues.append(
            {
                "key": "LITELLM_MODEL",
                "code": "unknown_model",
                "message": (
                    "The selected primary model is not declared by the current enabled channels "
                    "or advanced model routing config. "
                    f"Available models: {', '.join(available_models[:6])}"
                ),
                "severity": "error",
                "expected": "one configured channel model",
                "actual": primary_model,
            }
        )

    configured_agent_model_raw = (effective_map.get("AGENT_LITELLM_MODEL") or "").strip()
    configured_agent_model = normalize_agent_litellm_model(
        configured_agent_model_raw,
        configured_models=available_model_set,
    )
    if (
        configured_agent_model_raw
        and configured_agent_model
        and not _matches_exact_route(configured_agent_model, available_model_set)
        and not _uses_direct_env_provider(configured_agent_model)
    ):
        issues.append(
            {
                "key": "AGENT_LITELLM_MODEL",
                "code": "unknown_model",
                "message": (
                    "The selected Agent primary model is not declared by the current enabled channels "
                    "or advanced model routing config. "
                    f"Available models: {', '.join(available_models[:6])}"
                ),
                "severity": "error",
                "expected": "one configured channel model",
                "actual": configured_agent_model,
            }
        )
    elif (
            configured_agent_model_raw
            and configured_agent_model
            and _matches_route_set(configured_agent_model, hermes_route_set)
            and not _matches_route_set(configured_agent_model, mixed_hermes_routes)
        ):
        issues.append(
            {
                "key": "AGENT_LITELLM_MODEL",
                "code": "explicit_agent_model_no_safe_deployment",
                "message": (
                    "Hermes-only routes are not valid Agent models in Phase 3. "
                    "Choose a route with at least one non-Hermes deployment."
                ),
                "severity": "error",
                "expected": "Agent-safe route with non-Hermes deployment",
                "actual": configured_agent_model,
            }
        )

    fallback_models = [
        model.strip()
        for model in (effective_map.get("LITELLM_FALLBACK_MODELS") or "").split(",")
        if model.strip()
    ]
    mixed_fallbacks = [
        model for model in fallback_models
        if _matches_route_set(model, mixed_hermes_routes)
    ]
    if mixed_fallbacks:
        issues.append(
            {
                "key": "LITELLM_FALLBACK_MODELS",
                "code": "mixed_hermes_route_unsupported",
                "message": (
                    "Mixed Hermes/non-Hermes generation routes are not supported as fallback models in Phase 3."
                ),
                "severity": "error",
                "expected": "pure generation fallback routes",
                "actual": ", ".join(mixed_fallbacks[:3]),
            }
        )
    invalid_fallbacks = [
        model for model in fallback_models
        if not _matches_exact_route(model, available_model_set)
        and not _uses_direct_env_provider(model)
    ]
    if invalid_fallbacks:
        issues.append(
            {
                "key": "LITELLM_FALLBACK_MODELS",
                "code": "unknown_model",
                "message": (
                    "Fallback models include entries that are not declared by the current enabled channels "
                    "or advanced model routing config"
                ),
                "severity": "error",
                "expected": ",".join(available_models[:6]),
                "actual": ", ".join(invalid_fallbacks[:3]),
            }
        )

    vision_model = (effective_map.get("VISION_MODEL") or "").strip()
    if vision_model and _matches_route_set(vision_model, hermes_route_set):
        issues.append(
            {
                "key": "VISION_MODEL",
                "code": "hermes_vision_unsupported",
                "message": (
                    "Hermes routes are not valid Vision models in Phase 3. "
                    "Choose a pure non-Hermes Vision-capable route."
                ),
                "severity": "error",
                "expected": "pure non-Hermes Vision route",
                "actual": vision_model,
            }
        )
    elif (
        vision_model
        and not _matches_exact_route(vision_model, available_model_set)
        and not _uses_direct_env_provider(vision_model)
    ):
        issues.append(
            {
                "key": "VISION_MODEL",
                "code": "unknown_model",
                "message": (
                    "The selected Vision model is not declared by the current enabled channels "
                    "or advanced model routing config"
                ),
                "severity": "warning",
                "expected": ",".join(available_models[:6]),
                "actual": vision_model,
            }
        )

    return issues


def _validate_llm_channel_definition(
    *,
    channel_name: str,
    protocol_value: str,
    base_url_value: str,
    api_key_value: str,
    model_values: Sequence[str],
    enabled: bool,
    field_prefix: str,
    require_complete: bool,
) -> List[Dict[str, Any]]:
    """Validate one normalized LLM channel definition."""
    if not require_complete:
        return []

    issues, resolved_protocol = _validate_llm_channel_connection(
        channel_name=channel_name,
        protocol_value=protocol_value,
        base_url_value=base_url_value,
        api_key_value=api_key_value,
        model_values=model_values,
        field_prefix=field_prefix,
        require_base_url=False,
    )
    models_key = f"{field_prefix}_MODELS" if field_prefix != "test_channel" else "models"

    if not model_values:
        issues.append(
            {
                "key": models_key,
                "code": "missing_models",
                "message": f"LLM channel '{channel_name}' requires at least one model",
                "severity": "error",
                "expected": "comma-separated model list",
                "actual": "",
            }
        )
    elif not resolved_protocol:
        unresolved = [model for model in model_values if "/" not in model]
        if unresolved:
            issues.append(
                {
                    "key": models_key,
                    "code": "missing_protocol",
                    "message": (
                        f"LLM channel '{channel_name}' uses bare model names. "
                        "Set PROTOCOL or add provider/model prefixes."
                    ),
                    "severity": "error",
                    "expected": "protocol or provider/model",
                    "actual": ", ".join(unresolved[:3]),
                }
            )

    return issues


def _validate_llm_channel_connection(
    *,
    channel_name: str,
    protocol_value: str,
    base_url_value: str,
    api_key_value: str,
    model_values: Sequence[str] = (),
    field_prefix: str,
    require_base_url: bool,
) -> Tuple[List[Dict[str, Any]], str]:
    """Validate connection-level fields shared by test and discovery flows."""
    issues: List[Dict[str, Any]] = []
    protocol_key = f"{field_prefix}_PROTOCOL" if field_prefix != "test_channel" else "protocol"
    base_url_key = f"{field_prefix}_BASE_URL" if field_prefix != "test_channel" else "base_url"
    api_key_key = f"{field_prefix}_API_KEY" if field_prefix != "test_channel" else "api_key"

    normalized_protocol = canonicalize_llm_channel_protocol(protocol_value)
    if normalized_protocol and normalized_protocol not in SUPPORTED_LLM_CHANNEL_PROTOCOLS:
        issues.append(
            {
                "key": protocol_key,
                "code": "invalid_protocol",
                "message": (
                    f"Unsupported LLM channel protocol '{protocol_value}'. "
                    f"Supported: {', '.join(SUPPORTED_LLM_CHANNEL_PROTOCOLS)}"
                ),
                "severity": "error",
                "expected": ",".join(SUPPORTED_LLM_CHANNEL_PROTOCOLS),
                "actual": protocol_value,
            }
        )

    if require_base_url and not base_url_value.strip():
        issues.append(
            {
                "key": base_url_key,
                "code": "missing_base_url",
                "message": f"LLM channel '{channel_name}' requires a base URL to discover models",
                "severity": "error",
                "expected": "http(s)://host/v1",
                "actual": "",
            }
        )
    elif base_url_value and not _is_valid_llm_base_url(base_url_value):
        issues.append(
            {
                "key": base_url_key,
                "code": "invalid_url",
                "message": "LLM channel base URL must be a valid absolute URL",
                "severity": "error",
                "expected": "http(s)://host",
                "actual": base_url_value,
            }
        )
    elif base_url_value and not _is_safe_base_url(base_url_value):
        issues.append(
            {
                "key": base_url_key,
                "code": "ssrf_blocked",
                "message": "LLM channel base URL points to a restricted address (cloud metadata services are not allowed)",
                "severity": "error",
                "expected": "publicly reachable or local LLM endpoint",
                "actual": base_url_value,
            }
        )

    resolved_protocol = resolve_llm_channel_protocol(
        protocol_value,
        base_url=base_url_value,
        models=list(model_values) if model_values else None,
        channel_name=channel_name,
    )
    # Validate parsed key segments so that inputs like "," or " , " are
    # treated as empty (they produce zero usable keys after split+strip).
    _parsed_api_keys = [seg.strip() for seg in api_key_value.split(",") if seg.strip()]
    if not _parsed_api_keys and not channel_allows_empty_api_key(resolved_protocol, base_url_value):
        issues.append(
            {
                "key": api_key_key,
                "code": "missing_api_key",
                "message": f"LLM channel '{channel_name}' requires an API key",
                "severity": "error",
                "expected": "non-empty API key",
                "actual": api_key_value,
            }
        )
    return issues, resolved_protocol
