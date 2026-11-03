"""Diagnostic classification, response extraction and redaction for configuration probes.

No I/O or service state; shared by channel probes and notification tests.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import requests
from src.domain.generation.hermes_rules import build_hermes_redaction_values
from src.domain.generation.response_content import strip_leading_think_wrapper
from src.application.runtime.llm_config_validation import (
    _LLMDiagnostic,
    _has_model_access_denied_signal,
    _has_model_not_found_signal,
    _has_provider_prefix_mismatch_signal,
    _has_request_blocked_signal,
    _has_transport_blocked_signal,
)


def _build_skipped_capability_results(
    capability_checks: Sequence[str], reason: str, message: str, *, redaction_values: Optional[Set[str]] = None
) -> Dict[str, Dict[str, Any]]:
    return {
        capability: _build_llm_capability_result(
            capability=capability,
            status="skipped",
            message=message,
            error_code="skipped",
            retryable=False,
            details={"reason": reason},
            redaction_values=redaction_values,
        )
        for capability in capability_checks
    }


def _build_llm_capability_result(
    *,
    capability: str,
    status: str,
    message: str,
    error_code: Optional[str] = None,
    retryable: bool = False,
    latency_ms: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    redaction_values: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "message": _sanitize_llm_error_text(message, redaction_values=redaction_values),
        "error_code": error_code,
        "stage": f"capability_{capability}",
        "retryable": retryable,
        "latency_ms": latency_ms,
        "details": _sanitize_llm_details(
            {"capability": capability, **(details or {})}, redaction_values=redaction_values
        ),
    }


def _build_llm_capability_result_from_diagnostic(
    capability: str, diagnostic: _LLMDiagnostic, error: str, *, redaction_values: Optional[Set[str]] = None
) -> Dict[str, Any]:
    details = _merge_llm_diagnostic_details({"error": error}, diagnostic)
    return _build_llm_capability_result(
        capability=capability,
        status="failed",
        message=diagnostic.message,
        error_code=diagnostic.error_code,
        retryable=diagnostic.retryable,
        details=details,
        redaction_values=redaction_values,
    )


def _extract_llm_tool_call_names(response: Any) -> List[str]:
    choices = response.get("choices") if isinstance(response, dict) else getattr(response, "choices", None)
    if not choices:
        return []
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else getattr(choice, "message", None)
    if isinstance(message, dict):
        tool_calls = message.get("tool_calls")
    else:
        tool_calls = getattr(message, "tool_calls", None) if message is not None else None
    names: List[str] = []
    for call in tool_calls or []:
        function = call.get("function") if isinstance(call, dict) else getattr(call, "function", None)
        if isinstance(function, dict):
            name = str(function.get("name") or "").strip()
        else:
            name = str(getattr(function, "name", "") or "").strip()
        if name:
            names.append(name)
    return names


def _extract_llm_stream_chunk_content(chunk: Any) -> str:
    choices = chunk.get("choices") if isinstance(chunk, dict) else getattr(chunk, "choices", None)
    if not choices:
        return ""
    choice = choices[0]
    delta = choice.get("delta") if isinstance(choice, dict) else getattr(choice, "delta", None)
    message = choice.get("message") if isinstance(choice, dict) else getattr(choice, "message", None)
    for container in (delta, message):
        if not container:
            continue
        content = container.get("content") if isinstance(container, dict) else getattr(container, "content", None)
        if content:
            return str(content)
    content = choice.get("text") if isinstance(choice, dict) else getattr(choice, "text", None)
    return str(content or "")


def _classify_llm_capability_exception(exc: Exception, capability: str) -> _LLMDiagnostic:
    text = str(exc).lower()
    capability_tokens = {
        "json": ("response_format", "json_object", "json mode"),
        "tools": ("tool_choice", "tools", "function calling", "tool call"),
        "stream": ("stream", "streaming"),
        "vision": ("image", "image_url", "vision", "multimodal", "multi-modal"),
    }
    unsupported_markers = (
        "unsupported",
        "not support",
        "not supported",
        "unknown parameter",
        "unrecognized parameter",
        "invalid parameter",
        "unexpected keyword",
        "not allowed",
    )
    has_unsupported_marker = any((marker in text for marker in unsupported_markers))
    has_capability_token = any((token in text for token in capability_tokens.get(capability, ())))
    if has_unsupported_marker and (has_capability_token or capability in text):
        return _LLMDiagnostic(
            "capability_unsupported",
            False,
            f"LLM channel does not support {capability} capability",
            "capability_unsupported",
            {"capability": capability},
        )
    return _classify_llm_exception(exc)


def _build_llm_channel_result(
    *,
    success: bool,
    message: str,
    error: Optional[str],
    stage: Optional[str],
    error_code: Optional[str],
    retryable: Optional[bool],
    details: Optional[Dict[str, Any]] = None,
    resolved_protocol: Optional[str] = None,
    resolved_model: Optional[str] = None,
    models: Optional[List[str]] = None,
    latency_ms: Optional[int] = None,
    capability_results: Optional[Dict[str, Any]] = None,
    redaction_values: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": success,
        "message": _sanitize_llm_error_text(message, redaction_values=redaction_values),
        "error": _sanitize_llm_error_text(error, redaction_values=redaction_values) if error else None,
        "stage": stage,
        "error_code": error_code,
        "retryable": retryable,
        "details": _sanitize_llm_details(details, redaction_values=redaction_values),
        "resolved_protocol": (
            _sanitize_llm_error_text(resolved_protocol, redaction_values=redaction_values)
            if resolved_protocol is not None
            else None
        ),
        "latency_ms": latency_ms,
    }
    if resolved_model is not None or models is None:
        payload["resolved_model"] = (
            _sanitize_llm_error_text(resolved_model, redaction_values=redaction_values)
            if resolved_model is not None
            else resolved_model
        )
    if models is not None:
        payload["models"] = _sanitize_llm_value(models, redaction_values=redaction_values)
    if capability_results is not None:
        payload["capability_results"] = _sanitize_llm_value(capability_results, redaction_values=redaction_values)
    return payload


def _merge_llm_diagnostic_details(base_details: Optional[Dict[str, Any]], diagnostic: _LLMDiagnostic) -> Dict[str, Any]:
    details: Dict[str, Any] = dict(base_details or {})
    if diagnostic.reason:
        details.setdefault("reason", diagnostic.reason)
    details.update(diagnostic.details)
    return details


def _build_redaction_values(*values: Any) -> Set[str]:
    return build_hermes_redaction_values(*values)


def _comma_flexible_secret_pattern(secret: str) -> Optional[re.Pattern[str]]:
    normalized = re.sub("(?i)^\\s*authorization\\s*[:=]\\s*", "", str(secret or "").strip())
    normalized = re.sub("(?i)^\\s*bearer\\s+", "", normalized)
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if len(parts) <= 1:
        return None
    return re.compile(
        "(?i)(?:authorization\\s*[:=]\\s*)?(?:bearer\\s+)?" + "\\s*,\\s*".join((re.escape(part) for part in parts))
    )


def _sanitize_llm_error_text(text: Any, *, redaction_values: Optional[Set[str]] = None) -> str:
    if text is None:
        return ""
    sanitized = str(text).strip()
    if not sanitized:
        return ""
    for secret in sorted(redaction_values or set(), key=len, reverse=True):
        pattern = _comma_flexible_secret_pattern(secret)
        if pattern is not None:
            sanitized = pattern.sub("[REDACTED]", sanitized)
    for secret in sorted(redaction_values or set(), key=len, reverse=True):
        if secret:
            sanitized = sanitized.replace(secret, "[REDACTED]")
    patterns = [
        ("(?i)(authorization\\s*[:=]\\s*)(bearer\\s+)?([^\\s,;]+)", "\\1[REDACTED]"),
        ("(?i)(api[_-]?key\\s*[:=]\\s*)([^\\s,;]+)", "\\1[REDACTED]"),
        ("(?i)(cookie\\s*[:=]\\s*)([^\\s,;]+)", "\\1[REDACTED]"),
        ("(?i)bearer\\s+[a-z0-9._\\-]+", "Bearer [REDACTED]"),
        ("(?i)sk-[a-z0-9_\\-]+", "[REDACTED]"),
    ]
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)
    sanitized = " ".join(sanitized.split())
    return sanitized[:300]


def _sanitize_llm_details(
    details: Optional[Dict[str, Any]], *, redaction_values: Optional[Set[str]] = None
) -> Dict[str, Any]:
    if not details:
        return {}
    sanitized = _sanitize_llm_value(details, redaction_values=redaction_values)
    return sanitized if isinstance(sanitized, dict) else {}


def _sanitize_llm_value(value: Any, *, redaction_values: Optional[Set[str]] = None) -> Any:
    if isinstance(value, str):
        return _sanitize_llm_error_text(value, redaction_values=redaction_values)
    if isinstance(value, dict):
        return {
            _sanitize_llm_error_text(key, redaction_values=redaction_values): _sanitize_llm_value(
                item, redaction_values=redaction_values
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_llm_value(item, redaction_values=redaction_values) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_llm_value(item, redaction_values=redaction_values) for item in value]
    return value


def _classify_llm_http_error(status_code: int, error_text: str) -> _LLMDiagnostic:
    lowered = (error_text or "").lower()
    if _has_model_access_denied_signal(error_text or ""):
        return _LLMDiagnostic(
            "model_not_found", False, "Configured model is not available for this channel", "model_access_denied"
        )
    if "model" in lowered and any((token in lowered for token in ("not found", "does not exist", "unknown"))):
        return _LLMDiagnostic(
            "model_not_found", False, "Configured model could not be found on this channel", "model_not_found"
        )
    if status_code == 402 or any((token in lowered for token in ("billing", "balance", "insufficient balance"))):
        return _LLMDiagnostic(
            "quota", True, "LLM request was rejected by quota or billing limits", "insufficient_balance"
        )
    if any((token in lowered for token in ("quota", "insufficient_quota", "quota exceeded"))):
        return _LLMDiagnostic("quota", True, "LLM request was rejected by quota or rate limiting", "quota_exceeded")
    if status_code == 429 or any((token in lowered for token in ("rate limit", "too many requests", "rpm", "tpm"))):
        return _LLMDiagnostic("quota", True, "LLM request was rejected by quota or rate limiting", "rate_limit")
    if _has_transport_blocked_signal(error_text or ""):
        return _LLMDiagnostic(
            "network_error", True, "LLM request failed before a valid response was returned", "network_error"
        )
    if _has_request_blocked_signal(error_text or ""):
        return _LLMDiagnostic(
            "request_blocked", False, "LLM request was blocked by provider or gateway policy", "provider_blocked"
        )
    if status_code in {401, 403} or any(
        (token in lowered for token in ("unauthorized", "forbidden", "invalid api key", "authentication"))
    ):
        return _LLMDiagnostic("auth", False, "LLM authentication failed", "api_key_rejected")
    if status_code == 404:
        return _LLMDiagnostic(
            "network_error", False, "LLM model discovery endpoint could not be found", "endpoint_not_found"
        )
    if any((token in lowered for token in ("timeout", "timed out"))):
        return _LLMDiagnostic("timeout", True, "LLM request timed out", "timeout")
    return _LLMDiagnostic(
        "network_error", status_code >= 500, "LLM request failed before a valid response was returned", "http_error"
    )


def _classify_llm_exception(exc: Exception) -> _LLMDiagnostic:
    exc_name = type(exc).__name__.lower()
    text = str(exc).lower()
    if isinstance(exc, TimeoutError) or "timeout" in exc_name or "timed out" in text:
        return _LLMDiagnostic("timeout", True, "LLM request timed out", "timeout")
    if any((token in text for token in ("billing", "balance", "insufficient balance"))):
        return _LLMDiagnostic(
            "quota", True, "LLM request was rejected by quota or billing limits", "insufficient_balance"
        )
    if any((token in text for token in ("quota", "insufficient_quota", "quota exceeded"))):
        return _LLMDiagnostic("quota", True, "LLM request was rejected by quota or rate limiting", "quota_exceeded")
    if "ratelimit" in exc_name or any((token in text for token in ("rate limit", "too many requests", "rpm", "tpm"))):
        return _LLMDiagnostic("quota", True, "LLM request was rejected by quota or rate limiting", "rate_limit")
    if _has_provider_prefix_mismatch_signal(text):
        return _LLMDiagnostic(
            "model_not_found", False, "Configured model prefix does not match this channel", "provider_prefix_mismatch"
        )
    if _has_model_access_denied_signal(str(exc)):
        return _LLMDiagnostic(
            "model_not_found", False, "Configured model is not available for this channel", "model_access_denied"
        )
    if _has_request_blocked_signal(str(exc)):
        return _LLMDiagnostic(
            "request_blocked", False, "LLM request was blocked by provider or gateway policy", "provider_blocked"
        )
    if any((token in exc_name for token in ("auth", "permission"))) or any(
        (token in text for token in ("unauthorized", "forbidden", "invalid api key", "authentication"))
    ):
        return _LLMDiagnostic("auth", False, "LLM authentication failed", "api_key_rejected")
    if (
        ("notfound" in exc_name or "model" in text)
        and ("not found" in text or "does not exist" in text or "unknown model" in text)
        and _has_model_not_found_signal(text)
    ):
        return _LLMDiagnostic(
            "model_not_found", False, "Configured model could not be found on this channel", "model_not_found"
        )
    if "dns" in text or "name resolution" in text or "temporary failure in name resolution" in text:
        return _LLMDiagnostic(
            "network_error", True, "LLM request failed before a valid response was returned", "dns_error"
        )
    if "refused" in text or "connection refused" in text:
        return _LLMDiagnostic(
            "network_error", True, "LLM request failed before a valid response was returned", "connection_refused"
        )
    if "ssl" in text or "tls" in text or "certificate" in text:
        return _LLMDiagnostic(
            "network_error", True, "LLM request failed before a valid response was returned", "tls_error"
        )
    if any((token in exc_name for token in ("connection", "network"))) or any(
        (token in text for token in ("connection", "network", "firewall"))
    ):
        return _LLMDiagnostic(
            "network_error", True, "LLM request failed before a valid response was returned", "network_error"
        )
    return _LLMDiagnostic("network_error", False, "LLM channel test failed", "unknown_error")


def _extract_llm_completion_content(response: Any) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:

    def _field(obj: Any, key: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    def _text_from_blocks(blocks: Any) -> str:
        if not isinstance(blocks, list):
            return ""
        text_parts: List[str] = []
        for block in blocks:
            if isinstance(block, str):
                text_parts.append(block)
                continue
            block_type = str(_field(block, "type") or "").strip().lower()
            if block_type and block_type not in {"text", "output_text"}:
                continue
            text = _field(block, "text")
            if text is None:
                text = _field(block, "content")
            if isinstance(text, str) and text:
                text_parts.append(text)
        return strip_leading_think_wrapper("".join(text_parts))

    if response is None:
        return ("", "empty_response", "Completion returned no response object", "null_response")
    choices = _field(response, "choices")
    if not choices:
        return ("", "format_error", "Completion response did not include choices", "malformed_choices")
    choice = choices[0]
    content_blocks = _field(choice, "content_blocks")
    message = _field(choice, "message")
    if content_blocks is None:
        if message is not None:
            content_blocks = _field(message, "content_blocks")
    if content_blocks is not None:
        content = _text_from_blocks(content_blocks)
        if content:
            return (content, None, None, None)
    if message is None:
        return ("", "format_error", "Completion response did not include a message object", "malformed_choices")
    if isinstance(message, dict):
        has_content = "content" in message
    else:
        has_content = hasattr(message, "content")
    if not has_content:
        return ("", "format_error", "Completion message did not include a content field", "malformed_choices")
    raw_content = _field(message, "content")
    if raw_content is None:
        return ("", "empty_response", "Completion returned null message content", "null_content")
    content = (
        _text_from_blocks(raw_content)
        if isinstance(raw_content, list)
        else strip_leading_think_wrapper(str(raw_content))
    )
    if not content:
        return ("", "empty_response", "Completion returned an empty message content", "empty_content")
    return (content, None, None, None)


def _extract_llm_discovery_error(response: requests.Response) -> str:
    """Extract a concise error message from a failed model discovery response."""
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            message = str(error_payload.get("message") or error_payload.get("code") or "").strip()
            if message:
                return message
        message = str(payload.get("message") or payload.get("detail") or "").strip()
        if message:
            return message
    text = response.text.strip()
    if text:
        return text[:200]
    return f"HTTP {response.status_code}"


def _extract_discovered_llm_models(payload: Any) -> List[str]:
    """Normalize common `/models` response shapes into a unique model ID list."""
    raw_models: List[Any] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            raw_models = payload["data"]
        elif isinstance(payload.get("models"), list):
            raw_models = payload["models"]
    elif isinstance(payload, list):
        raw_models = payload
    models: List[str] = []
    seen: Set[str] = set()
    for entry in raw_models:
        if isinstance(entry, str):
            model_id = entry.strip()
        elif isinstance(entry, dict):
            model_id = str(entry.get("id") or entry.get("model") or entry.get("name") or "").strip()
        else:
            model_id = ""
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        models.append(model_id)
    return models
