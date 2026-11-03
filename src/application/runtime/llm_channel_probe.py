"""LLM channel discovery and capability probing through existing runtime ports."""

from __future__ import annotations
import json
import os
import time
import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import requests
from src.config import Config, normalize_llm_channel_model, resolve_llm_channel_protocol
from src.domain.generation.hermes_rules import (
    canonicalize_hermes_model_ref,
    canonicalize_hermes_base_url,
    is_masked_secret_placeholder,
    is_reserved_hermes_name,
)
from src.config.env_file import ConfigManager
from src.application.generation.runtime_ports import GenerationRuntimePort
from src.application.runtime.llm_config_validation import (
    _validate_llm_channel_connection,
    _validate_llm_channel_definition,
)
from src.application.runtime.system_config_ports import ConfigProbePort
from src.domain.shared.url_security import _build_llm_models_url
from typing import Callable
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
    _sanitize_llm_error_text,
    _classify_llm_http_error,
    _classify_llm_exception,
    _extract_llm_completion_content,
    _extract_llm_discovery_error,
    _extract_discovered_llm_models,
)

logger = logging.getLogger("src.application.runtime.system_config_service")


class LlmChannelProbe:
    """Discover and probe a channel without persisting its submitted configuration."""

    _LLM_CAPABILITY_ORDER: Tuple[str, ...] = ("json", "tools", "stream", "vision")
    _LLM_STREAM_CHUNK_LIMIT = 8
    _LLM_CAPABILITY_PROBE_IMAGE = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    def __init__(
        self,
        manager: ConfigManager,
        *,
        probe_port_provider: Callable[[], ConfigProbePort],
        generation_runtime_provider: Callable[[], GenerationRuntimePort],
        runtime_config: Optional[Config] = None,
    ):
        self._manager = manager
        self._probe_port_provider = probe_port_provider
        self._generation_runtime_provider = generation_runtime_provider
        self._config = runtime_config

    def _resolve_hermes_saved_secret(
        self,
        *,
        channel_name: str,
        protocol: str,
        base_url: str,
        submitted_api_key: str,
        use_saved_secret: bool,
        stage: str,
    ) -> Tuple[Optional[str], Dict[str, Any], Set[str]]:
        """Resolve a saved Hermes key only when the submitted endpoint is unchanged."""

        redaction_values = _build_redaction_values(submitted_api_key)
        if not use_saved_secret:
            return submitted_api_key, {}, redaction_values

        if not is_reserved_hermes_name(channel_name):
            return (
                None,
                _build_llm_channel_result(
                    success=False,
                    message="Saved secret scope mismatch",
                    error="Saved Hermes secret can only be used with the reserved hermes channel",
                    stage=stage,
                    error_code="saved_secret_scope_mismatch",
                    retryable=False,
                    details={"reason": "channel_identity_mismatch"},
                    resolved_protocol=None,
                    models=[] if stage == "model_discovery" else None,
                    latency_ms=None,
                    redaction_values=redaction_values,
                ),
                redaction_values,
            )

        saved_map = self._manager.read_config_map()
        saved_key = (saved_map.get("LLM_HERMES_API_KEY") or "").strip()
        if not saved_key or is_masked_secret_placeholder(saved_key):
            error_code = (
                "runtime_secret_not_reusable"
                if is_masked_secret_placeholder(saved_key) or (os.environ.get("LLM_HERMES_API_KEY") or "").strip()
                else "missing_saved_secret"
            )
            return (
                None,
                _build_llm_channel_result(
                    success=False,
                    message=(
                        "Runtime Hermes secret is not reusable"
                        if error_code == "runtime_secret_not_reusable"
                        else "Missing saved Hermes secret"
                    ),
                    error=(
                        "Runtime-injected LLM_HERMES_API_KEY cannot be reused from the settings test flow"
                        if error_code == "runtime_secret_not_reusable"
                        else "No saved LLM_HERMES_API_KEY is available for this endpoint"
                    ),
                    stage=stage,
                    error_code=error_code,
                    retryable=False,
                    details={"reason": error_code},
                    resolved_protocol=None,
                    models=[] if stage == "model_discovery" else None,
                    latency_ms=None,
                    redaction_values=redaction_values,
                ),
                redaction_values,
            )

        redaction_values.update(_build_redaction_values(saved_key))
        saved_protocol = (saved_map.get("LLM_HERMES_PROTOCOL") or "openai").strip()
        saved_base_url = (saved_map.get("LLM_HERMES_BASE_URL") or "").strip()
        try:
            submitted_protocol = (protocol or "openai").strip().lower() or "openai"
            saved_protocol_canonical = (saved_protocol or "openai").strip().lower() or "openai"
            submitted_base = canonicalize_hermes_base_url(base_url)
            saved_base = canonicalize_hermes_base_url(saved_base_url)
        except ValueError as exc:
            return (
                None,
                _build_llm_channel_result(
                    success=False,
                    message="Saved secret scope mismatch",
                    error=str(exc),
                    stage=stage,
                    error_code="saved_secret_scope_mismatch",
                    retryable=False,
                    details={"reason": "invalid_hermes_endpoint"},
                    resolved_protocol=None,
                    models=[] if stage == "model_discovery" else None,
                    latency_ms=None,
                    redaction_values=redaction_values,
                ),
                redaction_values,
            )

        if submitted_protocol != saved_protocol_canonical or submitted_base != saved_base:
            return (
                None,
                _build_llm_channel_result(
                    success=False,
                    message="Saved secret scope mismatch",
                    error="Hermes endpoint changed; re-enter LLM_HERMES_API_KEY before testing",
                    stage=stage,
                    error_code="saved_secret_scope_mismatch",
                    retryable=False,
                    details={
                        "reason": "endpoint_mismatch",
                        "submitted_base_url": submitted_base,
                        "saved_base_url": saved_base,
                    },
                    resolved_protocol=submitted_protocol,
                    models=[] if stage == "model_discovery" else None,
                    latency_ms=None,
                    redaction_values=redaction_values,
                ),
                redaction_values,
            )

        return saved_key, {}, redaction_values

    def _validate_hermes_submitted_secret(
        self,
        *,
        api_key: str,
        use_saved_secret: bool,
        stage: str,
        models: Optional[List[str]] = None,
        capability_checks: Sequence[str] = (),
        redaction_values: Optional[Set[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Reject Hermes secret shapes that must not reach an outbound request."""

        secret = (api_key or "").strip()
        redactions = set(redaction_values or set())
        redactions.update(_build_redaction_values(secret))
        if is_masked_secret_placeholder(secret):
            return _build_llm_channel_result(
                success=False,
                message="Runtime Hermes secret is not reusable",
                error=(
                    "Runtime-injected Hermes secret is masked and cannot be reused by "
                    "test/discovery. Re-enter the key or save it to .env."
                ),
                stage=stage,
                error_code="runtime_secret_not_reusable",
                retryable=False,
                details={"reason": "runtime_secret_not_reusable"},
                resolved_protocol=None,
                models=models if stage == "model_discovery" else None,
                latency_ms=None,
                capability_results=(
                    _build_skipped_capability_results(
                        capability_checks,
                        "base_test_failed",
                        "Skipped because the base channel test did not pass",
                        redaction_values=redactions,
                    )
                    if capability_checks
                    else None
                ),
                redaction_values=redactions,
            )
        if "," in secret:
            return _build_llm_channel_result(
                success=False,
                message="Hermes API key is invalid",
                error="Hermes Phase 3 only supports a single LLM_HERMES_API_KEY",
                stage=stage,
                error_code="invalid_config",
                retryable=False,
                details={
                    "issue_key": "LLM_HERMES_API_KEY",
                    "issue_code": "multiple_api_keys",
                    "reason": "multiple_api_keys",
                },
                resolved_protocol=None,
                models=models if stage == "model_discovery" else None,
                latency_ms=None,
                capability_results=(
                    _build_skipped_capability_results(
                        capability_checks,
                        "base_test_failed",
                        "Skipped because the base channel test did not pass",
                        redaction_values=redactions,
                    )
                    if capability_checks
                    else None
                ),
                redaction_values=redactions,
            )
        return None

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
        """Discover available models from an OpenAI-compatible `/models` endpoint."""
        channel_name = name.strip() or "channel"
        resolved_secret, secret_error, redaction_values = self._resolve_hermes_saved_secret(
            channel_name=channel_name,
            protocol=protocol,
            base_url=base_url,
            submitted_api_key=api_key,
            use_saved_secret=use_saved_secret,
            stage="model_discovery",
        )
        if resolved_secret is None:
            return secret_error
        api_key = resolved_secret
        redaction_values.update(_build_redaction_values(api_key))
        if is_reserved_hermes_name(channel_name):
            secret_error = self._validate_hermes_submitted_secret(
                api_key=api_key,
                use_saved_secret=use_saved_secret,
                stage="model_discovery",
                models=[],
                redaction_values=redaction_values,
            )
            if secret_error is not None:
                return secret_error
            try:
                base_url = canonicalize_hermes_base_url(base_url)
            except ValueError as exc:
                return _build_llm_channel_result(
                    success=False,
                    message="Hermes Base URL is invalid",
                    error=str(exc),
                    stage="model_discovery",
                    error_code="invalid_config",
                    retryable=False,
                    details={
                        "issue_key": "discover_channel_BASE_URL",
                        "issue_code": "invalid_hermes_url",
                        "reason": "invalid_hermes_url",
                    },
                    resolved_protocol=None,
                    models=[],
                    latency_ms=None,
                    redaction_values=redaction_values,
                )
        existing_models = [str(m).strip() for m in models if str(m).strip()]
        validation_issues, resolved_protocol = _validate_llm_channel_connection(
            channel_name=channel_name,
            protocol_value=protocol,
            base_url_value=base_url,
            api_key_value=api_key,
            model_values=existing_models,
            field_prefix="discover_channel",
            require_base_url=True,
        )
        if not resolved_protocol and existing_models:
            resolved_protocol = resolve_llm_channel_protocol(
                protocol,
                base_url=base_url,
                models=existing_models,
                channel_name=channel_name,
            )
        errors = [issue for issue in validation_issues if issue["severity"] == "error"]
        if errors:
            return _build_llm_channel_result(
                success=False,
                message="LLM channel configuration is invalid",
                error=errors[0]["message"],
                stage="model_discovery",
                error_code="invalid_config",
                retryable=False,
                details={
                    "issue_key": errors[0]["key"],
                    "issue_code": errors[0]["code"],
                    "reason": errors[0]["code"],
                },
                resolved_protocol=resolved_protocol or None,
                models=[],
                latency_ms=None,
                redaction_values=redaction_values,
            )

        if resolved_protocol not in {"openai", "deepseek"}:
            return _build_llm_channel_result(
                success=False,
                message="Model discovery is not supported for this protocol",
                error=(
                    f"LLM channel '{channel_name}' protocol '{resolved_protocol}' "
                    "does not support /models discovery yet"
                ),
                stage="model_discovery",
                error_code="unsupported_protocol",
                retryable=False,
                details={"protocol": resolved_protocol or None},
                resolved_protocol=resolved_protocol or None,
                models=[],
                latency_ms=None,
                redaction_values=redaction_values,
            )

        api_keys = [segment.strip() for segment in api_key.split(",") if segment.strip()]
        selected_api_key = api_keys[0] if api_keys else ""
        redaction_values.update(_build_redaction_values(selected_api_key))
        request_headers = {"Accept": "application/json"}
        if selected_api_key:
            request_headers["Authorization"] = f"Bearer {selected_api_key}"

        try:
            models_url = _build_llm_models_url(base_url)
        except ValueError as exc:
            return _build_llm_channel_result(
                success=False,
                message="LLM channel configuration is invalid",
                error=str(exc),
                stage="model_discovery",
                error_code="invalid_config",
                retryable=False,
                details={
                    "issue_key": "discover_channel_BASE_URL",
                    "issue_code": "invalid_url",
                    "reason": "invalid_url",
                },
                resolved_protocol=resolved_protocol or None,
                models=[],
                latency_ms=None,
                redaction_values=redaction_values,
            )

        try:
            started_at = time.perf_counter()
            response = self._probe_port_provider().fetch_models_snapshot(
                url=models_url,
                headers=request_headers,
                timeout_seconds=max(5.0, float(timeout_seconds)),
                trust_env=not is_reserved_hermes_name(channel_name),
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
        except requests.RequestException as exc:
            logger.warning(
                "LLM channel model discovery failed for %s: %s",
                channel_name,
                _sanitize_llm_error_text(exc, redaction_values=redaction_values),
            )
            diagnostic = _classify_llm_exception(exc)
            return _build_llm_channel_result(
                success=False,
                message=diagnostic.message,
                error=str(exc),
                stage="model_discovery",
                error_code=diagnostic.error_code,
                retryable=diagnostic.retryable,
                details=_merge_llm_diagnostic_details({"endpoint": models_url}, diagnostic),
                resolved_protocol=resolved_protocol or None,
                models=[],
                latency_ms=None,
                redaction_values=redaction_values,
            )

        if 300 <= response.status_code < 400:
            return _build_llm_channel_result(
                success=False,
                message="Model discovery request was redirected",
                error="Redirect responses are not allowed for model discovery",
                stage="model_discovery",
                error_code="network_error",
                retryable=False,
                details={"endpoint": models_url, "http_status": response.status_code},
                resolved_protocol=resolved_protocol or None,
                models=[],
                latency_ms=latency_ms,
                redaction_values=redaction_values,
            )

        if not response.ok:
            error_text = _extract_llm_discovery_error(response)
            diagnostic = _classify_llm_http_error(
                status_code=response.status_code,
                error_text=error_text,
            )
            return _build_llm_channel_result(
                success=False,
                message=diagnostic.message,
                error=error_text,
                stage="model_discovery",
                error_code=diagnostic.error_code,
                retryable=diagnostic.retryable,
                details=_merge_llm_diagnostic_details(
                    {"endpoint": models_url, "http_status": response.status_code},
                    diagnostic,
                ),
                resolved_protocol=resolved_protocol or None,
                models=[],
                latency_ms=latency_ms,
                redaction_values=redaction_values,
            )

        try:
            payload = response.json()
        except ValueError:
            return _build_llm_channel_result(
                success=False,
                message="Model discovery returned invalid JSON",
                error="The /models endpoint did not return valid JSON",
                stage="response_parse",
                error_code="format_error",
                retryable=False,
                details={"endpoint": models_url, "http_status": response.status_code, "reason": "non_json"},
                resolved_protocol=resolved_protocol or None,
                models=[],
                latency_ms=latency_ms,
                redaction_values=redaction_values,
            )

        models = _extract_discovered_llm_models(payload)
        if not models:
            return _build_llm_channel_result(
                success=False,
                message="Model discovery returned no models",
                error="The /models endpoint did not return any model IDs",
                stage="response_parse",
                error_code="empty_response",
                retryable=False,
                details={"endpoint": models_url, "http_status": response.status_code, "reason": "empty_models"},
                resolved_protocol=resolved_protocol or None,
                models=[],
                latency_ms=latency_ms,
                redaction_values=redaction_values,
            )

        return _build_llm_channel_result(
            success=True,
            message="LLM channel model discovery succeeded",
            error=None,
            stage="model_discovery",
            error_code=None,
            retryable=False,
            details={"endpoint": models_url, "model_count": len(models)},
            resolved_protocol=resolved_protocol or None,
            models=models,
            latency_ms=latency_ms,
            redaction_values=redaction_values,
        )

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
        """Run a minimal completion call against one channel definition."""
        requested_capabilities = self._normalize_llm_capability_checks(capability_checks)
        raw_models = [str(model).strip() for model in models if str(model).strip()]
        channel_name = name.strip() or "channel"
        resolved_secret, secret_error, redaction_values = self._resolve_hermes_saved_secret(
            channel_name=channel_name,
            protocol=protocol,
            base_url=base_url,
            submitted_api_key=api_key,
            use_saved_secret=use_saved_secret,
            stage="chat_completion",
        )
        if resolved_secret is None:
            result = secret_error
            if requested_capabilities and "capability_results" not in result:
                result["capability_results"] = _build_skipped_capability_results(
                    requested_capabilities,
                    "base_test_failed",
                    "Skipped because the base channel test did not pass",
                    redaction_values=redaction_values,
                )
            return result
        api_key = resolved_secret
        redaction_values.update(_build_redaction_values(api_key))
        if is_reserved_hermes_name(channel_name):
            secret_error = self._validate_hermes_submitted_secret(
                api_key=api_key,
                use_saved_secret=use_saved_secret,
                stage="chat_completion",
                capability_checks=requested_capabilities,
                redaction_values=redaction_values,
            )
            if secret_error is not None:
                return secret_error
            try:
                base_url = canonicalize_hermes_base_url(base_url)
            except ValueError as exc:
                return _build_llm_channel_result(
                    success=False,
                    message="Hermes Base URL is invalid",
                    error=str(exc),
                    stage="chat_completion",
                    error_code="invalid_config",
                    retryable=False,
                    details={
                        "issue_key": "test_channel_BASE_URL",
                        "issue_code": "invalid_hermes_url",
                        "reason": "invalid_hermes_url",
                    },
                    resolved_protocol=None,
                    resolved_model=None,
                    latency_ms=None,
                    capability_results=_build_skipped_capability_results(
                        requested_capabilities,
                        "base_test_failed",
                        "Skipped because the base channel test did not pass",
                        redaction_values=redaction_values,
                    ),
                    redaction_values=redaction_values,
                )
        validation_issues = _validate_llm_channel_definition(
            channel_name=channel_name,
            protocol_value=protocol,
            base_url_value=base_url,
            api_key_value=api_key,
            model_values=raw_models,
            enabled=enabled,
            field_prefix="test_channel",
            require_complete=True,
        )
        errors = [issue for issue in validation_issues if issue["severity"] == "error"]
        if errors:
            return _build_llm_channel_result(
                success=False,
                message="LLM channel configuration is invalid",
                error=errors[0]["message"],
                stage="chat_completion",
                error_code="invalid_config",
                retryable=False,
                details={
                    "issue_key": errors[0]["key"],
                    "issue_code": errors[0]["code"],
                    "reason": errors[0]["code"],
                },
                resolved_protocol=None,
                resolved_model=None,
                latency_ms=None,
                capability_results=_build_skipped_capability_results(
                    requested_capabilities,
                    "base_test_failed",
                    "Skipped because the base channel test did not pass",
                    redaction_values=redaction_values,
                ),
                redaction_values=redaction_values,
            )

        resolved_protocol = resolve_llm_channel_protocol(
            protocol, base_url=base_url, models=raw_models, channel_name=name
        )
        resolved_models = [normalize_llm_channel_model(model, resolved_protocol, base_url) for model in raw_models]
        resolved_model = resolved_models[0]
        if is_reserved_hermes_name(channel_name):
            resolved_model = canonicalize_hermes_model_ref(raw_models[0]).wire_model
        api_keys = [segment.strip() for segment in api_key.split(",") if segment.strip()]
        selected_api_key = api_keys[0] if api_keys else ""
        redaction_values.update(_build_redaction_values(selected_api_key))

        call_kwargs: Dict[str, Any] = {
            "model": resolved_model,
            "messages": [{"role": "user", "content": "Reply with OK"}],
            "max_tokens": 256,  # Increased to allow MiniMax-M3 thinking process + response
            "timeout": max(5.0, float(timeout_seconds)),
        }
        if selected_api_key:
            call_kwargs["api_key"] = selected_api_key
        if base_url.strip():
            call_kwargs["api_base"] = base_url.strip()
        call_kwargs = self._generation_runtime_provider().apply_params(
            call_kwargs,
            resolved_model,
            self._get_runtime_llm_temperature(),
        )

        probe_port = self._probe_port_provider()
        try:
            # Register fallback pricing for OpenAI-compatible models to prevent cost calculation errors
            config_model_list = None
            if getattr(self, "_config", None) is not None:
                config_model_list = getattr(self._config, "llm_model_list", None)
            probe_port.register_fallback_pricing(resolved_model, config_model_list)

            started_at = time.perf_counter()
            if is_reserved_hermes_name(channel_name):
                with probe_port.open_no_proxy_client(
                    api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=max(5.0, float(timeout_seconds)),
                ) as client:
                    hermes_call_kwargs = dict(call_kwargs)
                    hermes_call_kwargs["stream"] = False
                    hermes_call_kwargs["client"] = client
                    hermes_call_kwargs.pop("api_key", None)
                    hermes_call_kwargs.pop("api_base", None)
                    response = probe_port.completion_with_recovery(
                        model=resolved_model,
                        call_kwargs=hermes_call_kwargs,
                        log_label="[Hermes channel test]",
                    )
            else:
                response = probe_port.completion_with_recovery(
                    model=resolved_model,
                    call_kwargs=call_kwargs,
                    log_label="[LLM channel test]",
                )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            content, parse_error_code, parse_error, parse_reason = _extract_llm_completion_content(response)
            if parse_error_code:
                message = (
                    "LLM channel returned an empty response"
                    if parse_error_code == "empty_response"
                    else "LLM channel returned an unexpected response format"
                )
                return _build_llm_channel_result(
                    success=False,
                    message=message,
                    error=parse_error,
                    stage="response_parse",
                    error_code=parse_error_code,
                    retryable=False,
                    details={"response_error": parse_error, "reason": parse_reason},
                    resolved_protocol=resolved_protocol or None,
                    resolved_model=resolved_model,
                    latency_ms=latency_ms,
                    capability_results=_build_skipped_capability_results(
                        requested_capabilities,
                        "base_test_failed",
                        "Skipped because the base channel test did not pass",
                        redaction_values=redaction_values,
                    ),
                    redaction_values=redaction_values,
                )

            capability_results: Dict[str, Any] = {}
            if requested_capabilities and is_reserved_hermes_name(channel_name):
                capability_results = self._run_hermes_capability_checks(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                    capability_checks=requested_capabilities,
                    redaction_values=redaction_values,
                )
            elif requested_capabilities:
                capability_results = self._run_llm_capability_checks(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                    capability_checks=requested_capabilities,
                )
            return _build_llm_channel_result(
                success=True,
                message="LLM channel test succeeded",
                error=None,
                stage="chat_completion",
                error_code=None,
                retryable=False,
                details={"response_preview": content[:80]},
                resolved_protocol=resolved_protocol or None,
                resolved_model=resolved_model,
                latency_ms=latency_ms,
                capability_results=capability_results,
                redaction_values=redaction_values,
            )
        except Exception as exc:
            logger.warning(
                "LLM channel test failed for %s: %s",
                channel_name,
                _sanitize_llm_error_text(exc, redaction_values=redaction_values),
            )
            diagnostic = _classify_llm_exception(exc)
            return _build_llm_channel_result(
                success=False,
                message=diagnostic.message,
                error=str(exc),
                stage="chat_completion",
                error_code=diagnostic.error_code,
                retryable=diagnostic.retryable,
                details=_merge_llm_diagnostic_details({"model": resolved_model}, diagnostic),
                resolved_protocol=resolved_protocol or None,
                resolved_model=resolved_model,
                latency_ms=None,
                redaction_values=redaction_values,
                capability_results=_build_skipped_capability_results(
                    requested_capabilities,
                    "base_test_failed",
                    "Skipped because the base channel test did not pass",
                    redaction_values=redaction_values,
                ),
            )

    def _normalize_llm_capability_checks(self, capability_checks: Sequence[str]) -> List[str]:
        requested = {str(check).strip().lower() for check in capability_checks if str(check).strip()}
        return [check for check in self._LLM_CAPABILITY_ORDER if check in requested]

    def _run_hermes_capability_checks(
        self,
        *,
        resolved_model: str,
        selected_api_key: str,
        base_url: str,
        timeout_seconds: float,
        capability_checks: Sequence[str],
        redaction_values: Optional[Set[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        probe_port = self._probe_port_provider()
        for capability in capability_checks:
            if capability != "json":
                results[capability] = _build_llm_capability_result(
                    capability=capability,
                    status="skipped",
                    message="Hermes Phase 3 does not probe this capability",
                    error_code="not_probed",
                    retryable=False,
                    details={"reason": "not_probed"},
                    redaction_values=redaction_values,
                )
                continue
            try:
                started_at = time.perf_counter()
                with probe_port.open_no_proxy_client(
                    api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=max(5.0, float(timeout_seconds)),
                ) as client:
                    call_kwargs = self._build_llm_capability_completion_kwargs(
                        resolved_model=resolved_model,
                        selected_api_key=selected_api_key,
                        base_url=base_url,
                        timeout_seconds=timeout_seconds,
                        messages=[{"role": "user", "content": 'Return exactly this JSON object: {"status":"ok"}'}],
                        max_tokens=64,
                        extra={"response_format": {"type": "json_object"}, "client": client},
                    )
                    call_kwargs.pop("api_key", None)
                    call_kwargs.pop("api_base", None)
                    response = probe_port.litellm_completion(**call_kwargs)
                    content, parse_error_code, parse_error, parse_reason = _extract_llm_completion_content(response)
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                if parse_error_code:
                    results[capability] = _build_llm_capability_result(
                        capability="json",
                        status="failed",
                        message="JSON capability check returned no parseable content",
                        error_code=parse_error_code,
                        retryable=False,
                        latency_ms=latency_ms,
                        details={"reason": parse_reason, "response_error": parse_error},
                        redaction_values=redaction_values,
                    )
                    continue
                try:
                    payload = json.loads(content)
                except ValueError:
                    payload = None
                if not isinstance(payload, dict) or payload.get("status") != "ok":
                    results[capability] = _build_llm_capability_result(
                        capability="json",
                        status="failed",
                        message="JSON capability check returned non-JSON content",
                        error_code="format_error",
                        retryable=False,
                        latency_ms=latency_ms,
                        details={"reason": "non_json", "response_preview": content[:80]},
                        redaction_values=redaction_values,
                    )
                    continue
                results[capability] = _build_llm_capability_result(
                    capability="json",
                    status="passed",
                    message="JSON output capability check passed",
                    latency_ms=latency_ms,
                    details={"reason": "json_valid"},
                    redaction_values=redaction_values,
                )
            except Exception as exc:
                diagnostic = _classify_llm_capability_exception(exc, "json")
                results[capability] = _build_llm_capability_result_from_diagnostic(
                    "json",
                    diagnostic,
                    _sanitize_llm_error_text(exc, redaction_values=redaction_values),
                    redaction_values=redaction_values,
                )
        return results

    def _run_llm_capability_checks(
        self,
        *,
        resolved_model: str,
        selected_api_key: str,
        base_url: str,
        timeout_seconds: float,
        capability_checks: Sequence[str],
    ) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        for capability in capability_checks:
            if capability == "json":
                results[capability] = self._run_json_capability_check(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                )
            elif capability == "tools":
                results[capability] = self._run_tools_capability_check(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                )
            elif capability == "stream":
                results[capability] = self._run_stream_capability_check(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                )
            elif capability == "vision":
                results[capability] = self._run_vision_capability_check(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                )
        return results

    def _run_json_capability_check(
        self,
        *,
        resolved_model: str,
        selected_api_key: str,
        base_url: str,
        timeout_seconds: float,
    ) -> Dict[str, Any]:
        try:
            started_at = time.perf_counter()
            response = self._probe_port_provider().litellm_completion(
                **self._build_llm_capability_completion_kwargs(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                    messages=[{"role": "user", "content": 'Return exactly this JSON object: {"status":"ok"}'}],
                    max_tokens=64,
                    extra={"response_format": {"type": "json_object"}},
                )
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            content, parse_error_code, parse_error, parse_reason = _extract_llm_completion_content(response)
            if parse_error_code:
                return _build_llm_capability_result(
                    capability="json",
                    status="failed",
                    message="JSON capability check returned no parseable content",
                    error_code=parse_error_code,
                    retryable=False,
                    latency_ms=latency_ms,
                    details={"reason": parse_reason, "response_error": parse_error},
                )
            try:
                payload = json.loads(content)
            except ValueError:
                return _build_llm_capability_result(
                    capability="json",
                    status="failed",
                    message="JSON capability check returned non-JSON content",
                    error_code="format_error",
                    retryable=False,
                    latency_ms=latency_ms,
                    details={"reason": "non_json", "response_preview": content[:80]},
                )
            if not isinstance(payload, dict) or payload.get("status") != "ok":
                return _build_llm_capability_result(
                    capability="json",
                    status="failed",
                    message="JSON capability check returned unexpected JSON",
                    error_code="format_error",
                    retryable=False,
                    latency_ms=latency_ms,
                    details={"reason": "non_json", "response_preview": content[:80]},
                )
            return _build_llm_capability_result(
                capability="json",
                status="passed",
                message="JSON output capability check passed",
                latency_ms=latency_ms,
                details={"reason": "json_valid"},
            )
        except Exception as exc:
            diagnostic = _classify_llm_capability_exception(exc, "json")
            return _build_llm_capability_result_from_diagnostic("json", diagnostic, str(exc))

    def _run_tools_capability_check(
        self,
        *,
        resolved_model: str,
        selected_api_key: str,
        base_url: str,
        timeout_seconds: float,
    ) -> Dict[str, Any]:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "hrs_probe_echo",
                    "description": "Return the provided text.",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                },
            }
        ]
        try:
            started_at = time.perf_counter()
            response = self._probe_port_provider().litellm_completion(
                **self._build_llm_capability_completion_kwargs(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                    messages=[{"role": "user", "content": "Call the hrs_probe_echo tool with text set to ok."}],
                    max_tokens=64,
                    extra={
                        "tools": tools,
                        "tool_choice": {"type": "function", "function": {"name": "hrs_probe_echo"}},
                    },
                )
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            tool_names = _extract_llm_tool_call_names(response)
            if "hrs_probe_echo" not in tool_names:
                return _build_llm_capability_result(
                    capability="tools",
                    status="failed",
                    message="Tool calling capability check did not return the probe tool call",
                    error_code="capability_unsupported",
                    retryable=False,
                    latency_ms=latency_ms,
                    details={"reason": "tool_calls_missing", "tool_calls": tool_names},
                )
            return _build_llm_capability_result(
                capability="tools",
                status="passed",
                message="Tool calling capability check passed",
                latency_ms=latency_ms,
                details={"reason": "tool_call_returned"},
            )
        except Exception as exc:
            diagnostic = _classify_llm_capability_exception(exc, "tools")
            return _build_llm_capability_result_from_diagnostic("tools", diagnostic, str(exc))

    def _run_stream_capability_check(
        self,
        *,
        resolved_model: str,
        selected_api_key: str,
        base_url: str,
        timeout_seconds: float,
    ) -> Dict[str, Any]:
        stream = None
        started_at = time.perf_counter()
        try:
            stream = self._probe_port_provider().litellm_completion(
                **self._build_llm_capability_completion_kwargs(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                    messages=[{"role": "user", "content": "Reply with OK"}],
                    max_tokens=32,
                    extra={"stream": True},
                )
            )
            for index, chunk in enumerate(stream):
                content = _extract_llm_stream_chunk_content(chunk)
                if content:
                    latency_ms = int((time.perf_counter() - started_at) * 1000)
                    return _build_llm_capability_result(
                        capability="stream",
                        status="passed",
                        message="Streaming capability check passed",
                        latency_ms=latency_ms,
                        details={"reason": "stream_chunk_received"},
                    )
                if index + 1 >= self._LLM_STREAM_CHUNK_LIMIT:
                    break
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            return _build_llm_capability_result(
                capability="stream",
                status="failed",
                message="Streaming capability check returned no content chunks",
                error_code="empty_response",
                retryable=False,
                latency_ms=latency_ms,
                details={"reason": "stream_no_content"},
            )
        except Exception as exc:
            diagnostic = _classify_llm_capability_exception(exc, "stream")
            return _build_llm_capability_result_from_diagnostic("stream", diagnostic, str(exc))
        finally:
            close_stream = getattr(stream, "close", None)
            if callable(close_stream):
                try:
                    close_stream()
                except Exception as exc:
                    logger.debug("Failed to close LLM stream capability probe: %s", exc)

    def _run_vision_capability_check(
        self,
        *,
        resolved_model: str,
        selected_api_key: str,
        base_url: str,
        timeout_seconds: float,
    ) -> Dict[str, Any]:
        try:
            started_at = time.perf_counter()
            response = self._probe_port_provider().litellm_completion(
                **self._build_llm_capability_completion_kwargs(
                    resolved_model=resolved_model,
                    selected_api_key=selected_api_key,
                    base_url=base_url,
                    timeout_seconds=timeout_seconds,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Reply with OK if this image is visible."},
                                {"type": "image_url", "image_url": {"url": self._LLM_CAPABILITY_PROBE_IMAGE}},
                            ],
                        }
                    ],
                    max_tokens=32,
                )
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            content, parse_error_code, parse_error, parse_reason = _extract_llm_completion_content(response)
            if parse_error_code:
                return _build_llm_capability_result(
                    capability="vision",
                    status="failed",
                    message="Vision capability check returned no parseable content",
                    error_code=parse_error_code,
                    retryable=False,
                    latency_ms=latency_ms,
                    details={"reason": parse_reason, "response_error": parse_error},
                )
            return _build_llm_capability_result(
                capability="vision",
                status="passed",
                message="Vision capability check passed",
                latency_ms=latency_ms,
                details={"reason": "vision_response_received", "response_preview": content[:80]},
            )
        except Exception as exc:
            diagnostic = _classify_llm_capability_exception(exc, "vision")
            return _build_llm_capability_result_from_diagnostic("vision", diagnostic, str(exc))

    def _build_llm_capability_completion_kwargs(
        self,
        *,
        resolved_model: str,
        selected_api_key: str,
        base_url: str,
        timeout_seconds: float,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            timeout = float(timeout_seconds)
        except (TypeError, ValueError):
            timeout = 10.0
        call_kwargs: Dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "timeout": min(max(5.0, timeout), 10.0),
        }
        if selected_api_key:
            call_kwargs["api_key"] = selected_api_key
        if base_url.strip():
            call_kwargs["api_base"] = base_url.strip()
        if extra:
            call_kwargs.update(extra)
        call_kwargs = self._generation_runtime_provider().apply_params(
            call_kwargs,
            resolved_model,
            0.0,
        )
        return call_kwargs

    def _get_runtime_llm_temperature(self) -> float:
        """Return the current configured LLM temperature for ad-hoc channel tests."""
        return self._probe_port_provider().runtime_llm_temperature()
