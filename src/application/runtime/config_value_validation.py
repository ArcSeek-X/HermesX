"""Field normalization and cross-field validation for system configuration."""

from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Set
from src.config import parse_env_bool
from src.domain.notification.contracts import is_feishu_app_bot_env_configured, is_feishu_static_env_configured
from src.domain.notification.noise_rules import validate_notification_timezone
from src.domain.notification.endpoints import resolve_gotify_message_endpoint, resolve_ntfy_endpoint
from src.application.runtime.llm_config_validation import (
    _validate_llm_channel_map,
    _validate_llm_runtime_selection,
    _validate_numeric_range,
)
from src.application.runtime.system_config_ports import EventAlertRulesValidationError
from src.domain.shared.url_security import _is_valid_url


class ConfigValueValidator:
    """Validate field values and cross-field constraints before persistence."""

    def __init__(self, probe_port_provider):
        """构造配置值校验器：装配探测端口提供者。"""
        self._probe_port_provider = probe_port_provider

    def validate_value(self, key: str, value: str, field_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate a single field value against schema metadata."""
        issues: List[Dict[str, Any]] = []
        data_type = field_schema.get("data_type", "string")
        validation = field_schema.get("validation", {}) or {}
        is_required = field_schema.get("is_required", False)

        # Empty values are valid for non-required fields (skip type validation)
        if not value.strip() and not is_required:
            return issues

        if ("\n" in value or "\r" in value) and data_type != "json":
            issues.append(
                {
                    "key": key,
                    "code": "invalid_value",
                    "message": "Value cannot contain newline characters",
                    "severity": "error",
                    "expected": "single-line value",
                    "actual": "contains newline",
                }
            )
            return issues

        if data_type == "integer":
            try:
                numeric = int(value)
            except ValueError:
                return [
                    {
                        "key": key,
                        "code": "invalid_type",
                        "message": "Value must be an integer",
                        "severity": "error",
                        "expected": "integer",
                        "actual": value,
                    }
                ]
            issues.extend(_validate_numeric_range(key, numeric, validation))

        elif data_type == "number":
            try:
                numeric = float(value)
            except ValueError:
                return [
                    {
                        "key": key,
                        "code": "invalid_type",
                        "message": "Value must be a number",
                        "severity": "error",
                        "expected": "number",
                        "actual": value,
                    }
                ]
            issues.extend(_validate_numeric_range(key, numeric, validation))

        elif data_type == "boolean":
            if value.strip().lower() not in {"true", "false"}:
                issues.append(
                    {
                        "key": key,
                        "code": "invalid_type",
                        "message": "Value must be true or false",
                        "severity": "error",
                        "expected": "true|false",
                        "actual": value,
                    }
                )

        elif data_type == "time":
            pattern = validation.get("pattern") or r"^([01]\d|2[0-3]):[0-5]\d$"
            if not re.match(pattern, value.strip()):
                issues.append(
                    {
                        "key": key,
                        "code": "invalid_format",
                        "message": "Value must be in HH:MM format",
                        "severity": "error",
                        "expected": "HH:MM",
                        "actual": value,
                    }
                )

        elif data_type == "json":
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                issues.append(
                    {
                        "key": key,
                        "code": "invalid_json",
                        "message": "Value must be valid JSON",
                        "severity": "error",
                        "expected": "valid JSON",
                        "actual": value[:120],
                    }
                )
            else:
                if key == "AGENT_EVENT_ALERT_RULES_JSON":
                    try:
                        self._probe_port_provider().validate_event_alert_rules(parsed)
                    except EventAlertRulesValidationError as exc:
                        issues.append(
                            {
                                "key": key,
                                "code": "invalid_event_rule",
                                "message": f"Rule validation failed: {exc}",
                                "severity": "error",
                                "expected": "supported EventMonitor rule fields and enum values",
                                "actual": f"rule #{exc.rule_index or 1}",
                            }
                        )

        elif validation.get("pattern"):
            pattern = validation["pattern"]
            if not re.match(pattern, value.strip()):
                issues.append(
                    {
                        "key": key,
                        "code": "invalid_format",
                        "message": "Value does not match the required format",
                        "severity": "error",
                        "expected": pattern,
                        "actual": value,
                    }
                )

        if validation.get("timezone") and value:
            try:
                validate_notification_timezone(value)
            except ValueError as exc:
                issues.append(
                    {
                        "key": key,
                        "code": "invalid_timezone",
                        "message": str(exc),
                        "severity": "error",
                        "expected": "valid IANA timezone or empty",
                        "actual": value,
                    }
                )

        if "enum" in validation and value and value not in validation["enum"]:
            issues.append(
                {
                    "key": key,
                    "code": "invalid_enum",
                    "message": "Value is not in allowed options",
                    "severity": "error",
                    "expected": ",".join(validation["enum"]),
                    "actual": value,
                }
            )

        if "allowed_values" in validation and value:
            delimiter = validation.get("delimiter")
            raw_values = value.split(delimiter) if delimiter else [value]
            allowed_values = {str(item).strip().lower() for item in validation["allowed_values"]}
            invalid_values = []
            seen_invalid = set()
            for raw_item in raw_values:
                item = raw_item.strip().lower()
                if not item:
                    continue
                if item not in allowed_values and item not in seen_invalid:
                    invalid_values.append(item)
                    seen_invalid.add(item)
            if invalid_values:
                issues.append(
                    {
                        "key": key,
                        "code": "invalid_allowed_value",
                        "message": "Value contains unsupported item(s)",
                        "severity": "error",
                        "expected": ",".join(str(item) for item in validation["allowed_values"]),
                        "actual": ", ".join(invalid_values),
                    }
                )

        if validation.get("item_type") == "url":
            delimiter = validation.get("delimiter", ",")
            values = (
                [item.strip() for item in value.split(delimiter)] if validation.get("multi_value") else [value.strip()]
            )
            allowed_schemes = tuple(validation.get("allowed_schemes", ["http", "https"]))
            invalid_values = [
                item for item in values if item and not _is_valid_url(item, allowed_schemes=allowed_schemes)
            ]
            if invalid_values:
                issues.append(
                    {
                        "key": key,
                        "code": "invalid_url",
                        "message": "Value must contain valid URLs with scheme and host",
                        "severity": "error",
                        "expected": ",".join(allowed_schemes) + " URL(s)",
                        "actual": ", ".join(invalid_values[:3]),
                    }
                )

        if key == "NTFY_URL" and value.strip():
            allowed_schemes = tuple(validation.get("allowed_schemes", ["http", "https"]))
            if _is_valid_url(value.strip(), allowed_schemes=allowed_schemes):
                ntfy_server_url, ntfy_topic = resolve_ntfy_endpoint(value)
                if not ntfy_server_url or not ntfy_topic:
                    issues.append(
                        {
                            "key": key,
                            "code": "invalid_ntfy_url",
                            "message": "NTFY_URL must include a topic path, e.g. https://ntfy.sh/my-topic",
                            "severity": "error",
                            "expected": "ntfy publish endpoint with topic path",
                            "actual": value,
                        }
                    )

        if key == "GOTIFY_URL" and value.strip():
            allowed_schemes = tuple(validation.get("allowed_schemes", ["http", "https"]))
            if _is_valid_url(value.strip(), allowed_schemes=allowed_schemes):
                gotify_endpoint = resolve_gotify_message_endpoint(value)
                if not gotify_endpoint:
                    issues.append(
                        {
                            "key": key,
                            "code": "invalid_gotify_url",
                            "message": "GOTIFY_URL must be a Gotify server base URL and must not include /message",
                            "severity": "error",
                            "expected": "Gotify server base URL, e.g. https://gotify.example",
                            "actual": value,
                        }
                    )

        return issues

    @staticmethod
    def validate_cross_field(effective_map: Dict[str, str], updated_keys: Set[str]) -> List[Dict[str, Any]]:
        """Validate dependencies across multiple keys."""
        issues: List[Dict[str, Any]] = []

        agent_backend = (effective_map.get("AGENT_BACKEND") or "auto").strip().lower()
        agent_arch = (effective_map.get("AGENT_ARCH") or "single").strip().lower()
        if (
            agent_backend == "codex_app_server"
            and agent_arch != "single"
            and ({"AGENT_BACKEND", "AGENT_ARCH"} & updated_keys)
        ):
            issues.append(
                {
                    "key": "AGENT_ARCH",
                    "code": "unsupported_agent_arch",
                    "message": "Codex 本地 Agent 当前只支持单 Agent 问股，请切换为 single。",
                    "severity": "error",
                    "expected": "single",
                    "actual": agent_arch,
                }
            )

        timeout_raw = (effective_map.get("AGENT_ORCHESTRATOR_TIMEOUT_S") or "600").strip()
        try:
            agent_timeout = int(timeout_raw)
        except ValueError:
            agent_timeout = None
        if (
            agent_backend == "codex_app_server"
            and agent_timeout is not None
            and agent_timeout <= 0
            and ({"AGENT_BACKEND", "AGENT_ORCHESTRATOR_TIMEOUT_S"} & updated_keys)
        ):
            issues.append(
                {
                    "key": "AGENT_ORCHESTRATOR_TIMEOUT_S",
                    "code": "codex_timeout_required",
                    "message": "Codex 本地 Agent 必须设置大于 0 的整体时限，确保每次问股都会结束。",
                    "severity": "error",
                    "expected": ">0 when AGENT_BACKEND=codex_app_server",
                    "actual": timeout_raw,
                }
            )

        token_value = (effective_map.get("TELEGRAM_BOT_TOKEN") or "").strip()
        chat_id_value = (effective_map.get("TELEGRAM_CHAT_ID") or "").strip()
        if (
            token_value
            and not chat_id_value
            and ("TELEGRAM_BOT_TOKEN" in updated_keys or "TELEGRAM_CHAT_ID" in updated_keys)
        ):
            issues.append(
                {
                    "key": "TELEGRAM_CHAT_ID",
                    "code": "missing_dependency",
                    "message": "TELEGRAM_CHAT_ID is required when TELEGRAM_BOT_TOKEN is set",
                    "severity": "error",
                    "expected": "non-empty TELEGRAM_CHAT_ID",
                    "actual": chat_id_value,
                }
            )

        feishu_relevant_keys = {
            "FEISHU_APP_ID",
            "FEISHU_APP_SECRET",
            "FEISHU_WEBHOOK_URL",
            "FEISHU_WEBHOOK_SECRET",
            "FEISHU_WEBHOOK_KEYWORD",
            "FEISHU_STREAM_ENABLED",
            "FEISHU_FOLDER_TOKEN",
            "FEISHU_CHAT_ID",
        }
        has_feishu_app_id = bool((effective_map.get("FEISHU_APP_ID") or "").strip())
        has_feishu_app_secret = bool((effective_map.get("FEISHU_APP_SECRET") or "").strip())
        has_feishu_app_credentials_complete = has_feishu_app_id and has_feishu_app_secret
        has_feishu_app_credentials = has_feishu_app_id or has_feishu_app_secret
        has_feishu_folder_token = bool((effective_map.get("FEISHU_FOLDER_TOKEN") or "").strip())
        has_feishu_full_cloud_doc_credentials = has_feishu_app_credentials_complete and has_feishu_folder_token
        # Match runtime semantics: Config.from_env only enables stream mode
        # when the value is exactly "true" (case-insensitive).
        feishu_stream_enabled = (effective_map.get("FEISHU_STREAM_ENABLED") or "false").strip().lower() == "true"
        has_feishu_stream_route = feishu_stream_enabled and has_feishu_app_credentials_complete
        has_feishu_app_bot_route = is_feishu_app_bot_env_configured(effective_map)
        if (
            has_feishu_app_credentials
            and not has_feishu_full_cloud_doc_credentials
            and not is_feishu_static_env_configured(effective_map)
            and not has_feishu_stream_route
            and not has_feishu_app_bot_route
            and (updated_keys & feishu_relevant_keys)
        ):
            issues.append(
                {
                    "key": "FEISHU_CHAT_ID",
                    "code": "feishu_mode_mismatch",
                    "message": (
                        "仅配置 FEISHU_APP_ID / FEISHU_APP_SECRET 不会开启飞书静态通知；"
                        "App Bot 主动推送需要同时配置 FEISHU_CHAT_ID，"
                        "Webhook 推送请填写 FEISHU_WEBHOOK_URL；"
                        "事件订阅请使用 FEISHU_STREAM_ENABLED=true 并完成应用发布与权限配置。"
                    ),
                    "severity": "warning",
                    "expected": (
                        "static notification: FEISHU_WEBHOOK_URL or "
                        "FEISHU_APP_ID + FEISHU_APP_SECRET + FEISHU_CHAT_ID; "
                        "event subscription: FEISHU_STREAM_ENABLED=true"
                    ),
                    "actual": "app credentials without notification target",
                }
            )

        issues.extend(
            _validate_llm_channel_map(
                effective_map=effective_map,
                updated_keys=updated_keys,
            )
        )
        issues.extend(_validate_llm_runtime_selection(effective_map=effective_map))

        if parse_env_bool(effective_map.get("NOTIFICATION_DAILY_DIGEST_ENABLED"), default=False):
            issues.append(
                {
                    "key": "NOTIFICATION_DAILY_DIGEST_ENABLED",
                    "code": "reserved_notification_daily_digest",
                    "message": (
                        "NOTIFICATION_DAILY_DIGEST_ENABLED is reserved; "
                        "the current P4 implementation does not send daily digests."
                    ),
                    "severity": "warning",
                    "expected": "reserved flag only",
                    "actual": effective_map.get("NOTIFICATION_DAILY_DIGEST_ENABLED", ""),
                }
            )

        return issues

    @staticmethod
    def normalize_value_for_storage(value: str, field_schema: Dict[str, Any]) -> str:
        """Normalize submitted values before persisting to the single-line .env file."""
        if field_schema.get("data_type", "string") != "json":
            return value

        if not value.strip():
            return value

        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value

        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
