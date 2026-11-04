# -*- coding: utf-8 -*-
"""Shared agent-tool execution helpers.

This module is intentionally runtime-neutral.  It contains the existing
runner semantics that later Tool Surface / AgentBackend adapters can reuse
without importing the full ReAct loop.

共享的 Agent 工具执行辅助模块，刻意保持运行期中立。封装现有 runner 语义
（工具调用执行、股票代码作用域守卫、密钥/凭证脱敏、审计记录），供后续 Tool Surface /
AgentBackend 适配器复用，而无需引入完整 ReAct 循环。
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from src.application.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_SUMMARY_LIMIT = 500
_TOKEN_PATTERN = re.compile(
    r"(?i)\b(?:sk|pk|ghp|gho|github_pat|xox[baprs]?|bearer)[-_a-z0-9]{12,}\b"
)
_AUTH_PATTERN = re.compile(
    r"(?i)\b((?:proxy[-_]?authorization|authorization)\s*[:=]\s*)"
    r"[^\s,;\"']+(?:\s+[^\s,;\"']+)?"
)
_URL_CREDENTIAL_PATTERN = re.compile(r"([a-z][a-z0-9+.-]*://)([^/\s:@]+):([^/\s@]+)@", re.IGNORECASE)
_HEADER_SECRET_PATTERN = re.compile(r"(?i)\b(api[-_]?key|token|secret|cookie|set-cookie)\b\s*[:=]\s*[^\s,;]+")
_QUOTED_SECRET_FIELD_PATTERN = re.compile(
    r"(?i)([\"']?(?:authorization|proxy-authorization|api[-_]?key|x-api-key|token|access[-_]?token|"
    r"refresh[-_]?token|secret|client[-_]?secret|password|passwd|cookie|set-cookie)[\"']?\s*[:=]\s*)([\"']).*?(\2)"
)
_HOME_PATH_PATTERN = re.compile(r"(/Users/[^/\s]+|/home/[^/\s]+)(/[^\s,;]*)?")
_SECRET_KEY_NAMES = {
    "authorization",
    "proxy_authorization",
    "api_key",
    "apikey",
    "x_api_key",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "client_secret",
    "password",
    "passwd",
    "cookie",
    "set_cookie",
}
_SECRET_KEY_MARKERS = ("api_key", "apikey", "token", "secret", "password", "passwd", "cookie")


@dataclass
class ToolAccessContext:
    """Execution context for Tool Surface calls."""

    stock_scope: Any = None
    market: Optional[str] = None
    time_range: Optional[dict] = None
    data_sources: Optional[List[str]] = None
    backend: Optional[str] = None
    session_id: Optional[str] = None
    timeout_seconds: Optional[float] = None
    deadline: Optional[float] = None
    cancel_event: Optional[threading.Event] = None
    max_result_bytes: Optional[int] = None
    redact_result: bool = False
    audit_context: Dict[str, Any] = field(default_factory=dict)


class ToolExecutionCancelled(Exception):
    """Raised at a cooperative checkpoint after the caller cancels a tool."""


class ToolExecutionDeadlineExceeded(Exception):
    """Raised at a cooperative checkpoint after the tool deadline expires."""


_ACTIVE_TOOL_CONTEXT: contextvars.ContextVar[Optional[ToolAccessContext]] = contextvars.ContextVar(
    "active_tool_access_context",
    default=None,
)


def bind_tool_execution_context(context: ToolAccessContext) -> contextvars.Token:
    """Bind one Tool Surface execution context for runtime-neutral handlers."""
    return _ACTIVE_TOOL_CONTEXT.set(context)


def reset_tool_execution_context(token: contextvars.Token) -> None:
    """Restore the previous Tool Surface execution context."""
    _ACTIVE_TOOL_CONTEXT.reset(token)


def check_tool_execution() -> None:
    """Stop at a safe handler boundary when cancellation or deadline is reached."""
    context = _ACTIVE_TOOL_CONTEXT.get()
    if context is None:
        return
    if context.cancel_event is not None and context.cancel_event.is_set():
        raise ToolExecutionCancelled("Tool execution was cancelled")
    if context.deadline is not None and time.monotonic() >= context.deadline:
        raise ToolExecutionDeadlineExceeded("Tool execution deadline was exceeded")


def serialize_tool_result(result: Any) -> str:
    """Serialize a tool result to a JSON string consumable by an LLM."""
    if result is None:
        return json.dumps({"result": None})
    if isinstance(result, str):
        return result
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(result)
    if hasattr(result, "__dict__"):
        try:
            d = {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
            return json.dumps(d, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(result)
    return str(result)


def _normalize_tool_stock_code(value: Any) -> Any:
    """Canonicalize stock code arguments so equivalent HK variants share one cache key."""
    if not isinstance(value, str):
        return value

    text = value.strip().upper()
    if not text:
        return text

    if text.endswith(".HK"):
        base = text[:-3]
        if base.isdigit() and 1 <= len(base) <= 5:
            return f"HK{base.zfill(5)}"

    if text.startswith("HK"):
        base = text[2:]
        if base.isdigit() and 1 <= len(base) <= 5:
            return f"HK{base.zfill(5)}"

    if text.isdigit() and len(text) == 5:
        return f"HK{text}"

    try:
        from src.domain.market.stock_codes import canonical_stock_code, normalize_stock_code

        return canonical_stock_code(normalize_stock_code(text))
    except Exception:
        return text


def _build_tool_cache_key(tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
    """Build a stable cache key for tool calls with normalized stock-code arguments."""
    if not isinstance(arguments, dict):
        return None

    normalized_args: Dict[str, Any] = {}
    for key, value in arguments.items():
        if key == "stock_code":
            normalized_args[key] = _normalize_tool_stock_code(value)
        else:
            normalized_args[key] = value

    try:
        payload = json.dumps(normalized_args, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return None
    return f"{tool_name}:{payload}"


def _is_non_retriable_tool_result(result: Any) -> bool:
    """Return True when a tool result explicitly tells the agent not to retry."""
    return (
        isinstance(result, dict)
        and bool(result.get("error"))
        and result.get("retriable") is False
    )


def _is_stock_scoped_tool(tool_registry: ToolRegistry, tool_name: str) -> bool:
    """判断某工具是否为「股票作用域工具」：从注册表解析工具定义，若存在名为 stock_code 的参数即为真。"""
    tool_def = tool_registry.resolve(tool_name)
    if tool_def is None:
        return False
    return any(param.name == "stock_code" for param in tool_def.parameters)


def _normalize_guard_stock_code(value: Any) -> str:
    """守卫用的股票代码归一化：None 返回空串；整型浮点转整，借助 _normalize_tool_stock_code 统一格式，结果非字符串则转字符串。"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    raw = value if isinstance(value, str) else str(value)
    normalized = _normalize_tool_stock_code(raw)
    return normalized if isinstance(normalized, str) else str(normalized)


def _iter_allowed_stock_codes(stock_scope: Any) -> Iterable[Any]:
    """从 stock_scope 取允许的股票代码集合（缺省为空集合）。"""
    return getattr(stock_scope, "allowed_stock_codes", set()) or set()


def _guard_tool_stock_scope(
    tool_registry: ToolRegistry,
    tool_name: str,
    arguments: Dict[str, Any],
    stock_scope: Any,
) -> Optional[Dict[str, Any]]:
    """股票作用域守卫：当工具受 stock_code 约束且请求代码不在期望/允许集合内时，返回 stock_scope_violation 错误（不可重试）；否则返回 None 放行。"""
    if stock_scope is None or not isinstance(arguments, dict):
        return None
    if not _is_stock_scoped_tool(tool_registry, tool_name):
        return None
    if "stock_code" not in arguments:
        return None

    requested = _normalize_guard_stock_code(arguments.get("stock_code"))
    expected = _normalize_guard_stock_code(getattr(stock_scope, "expected_stock_code", ""))
    allowed = {
        normalized
        for code in _iter_allowed_stock_codes(stock_scope)
        for normalized in [_normalize_guard_stock_code(code)]
        if normalized
    }
    if requested and (requested == expected or requested in allowed):
        return None

    return {
        "error": "stock_scope_violation",
        "expected_stock_code": expected,
        "requested_stock_code": requested,
        "allowed_stock_codes": sorted(allowed),
        "retriable": False,
    }


def _normalize_secret_key(key: Any) -> str:
    """将键名归一为小写、仅保留字母数字、以 _ 连接的字符串，用于密钥名比对。"""
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def _is_secret_key(key: Any) -> bool:
    """判断某键名是否为敏感密钥：归一后命中 _SECRET_KEY_NAMES 或包含任一 _SECRET_KEY_MARKERS 子串即为真。"""
    normalized = _normalize_secret_key(key)
    if not normalized:
        return False
    if normalized in _SECRET_KEY_NAMES:
        return True
    return any(marker in normalized for marker in _SECRET_KEY_MARKERS)


def _redact_structured_secrets(value: Any, *, _depth: int = 0) -> Any:
    """递归脱敏结构化数据：dict 中敏感键名置 [REDACTED]、其余递归；list/tuple 逐元素递归；超过递归深度上限返回占位符。"""
    if _depth > 12:
        return "<redacted_depth_limit>"
    if isinstance(value, dict):
        redacted: Dict[Any, Any] = {}
        for key, item in value.items():
            if _is_secret_key(key):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_structured_secrets(item, _depth=_depth + 1)
        return redacted
    if isinstance(value, list):
        return [_redact_structured_secrets(item, _depth=_depth + 1) for item in value]
    if isinstance(value, tuple):
        return [_redact_structured_secrets(item, _depth=_depth + 1) for item in value]
    return value


def _redact_json_string_if_possible(text: str) -> str:
    """若文本是 JSON 对象/数组，解析后递归脱敏再序列化返回；非 JSON 或解析失败则原样返回。"""
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return text
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return text
    try:
        return json.dumps(_redact_structured_secrets(parsed), ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return text


def redact_external_tool_result(result: Any) -> str:
    """Serialize and redact a ToolSurface result before external roundtrip."""
    if isinstance(result, (dict, list, tuple)):
        try:
            text = json.dumps(_redact_structured_secrets(result), ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = serialize_tool_result(result)
    elif isinstance(result, str):
        text = _redact_json_string_if_possible(result)
    else:
        text = serialize_tool_result(result)
    return redact_diagnostic_value(text, limit=max(len(text), 1))


def execute_runner_tool_call(
    *,
    tool_call: Any,
    tool_registry: ToolRegistry,
    stock_scope: Any = None,
    non_retriable_tool_results: Optional[Dict[str, str]] = None,
) -> tuple[Any, str, bool, float, bool, Optional[Dict[str, Any]]]:
    """Execute a single tool call using the legacy runner semantics."""
    t0 = time.time()
    cache_key = _build_tool_cache_key(tool_call.name, tool_call.arguments)
    guard_result = _guard_tool_stock_scope(tool_registry, tool_call.name, tool_call.arguments, stock_scope)
    if guard_result is not None:
        dur = round(time.time() - t0, 2)
        result_str = serialize_tool_result(guard_result)
        if cache_key and non_retriable_tool_results is not None:
            non_retriable_tool_results[cache_key] = result_str
        logger.warning(
            "Tool '%s' blocked by stock scope: requested=%s expected=%s allowed=%s",
            tool_call.name,
            guard_result.get("requested_stock_code"),
            guard_result.get("expected_stock_code"),
            guard_result.get("allowed_stock_codes"),
        )
        return tool_call, result_str, False, dur, False, guard_result

    if cache_key and non_retriable_tool_results is not None and cache_key in non_retriable_tool_results:
        dur = round(time.time() - t0, 2)
        logger.info(
            "Tool '%s' skipped via non-retriable cache for arguments=%s",
            tool_call.name,
            tool_call.arguments,
        )
        return tool_call, non_retriable_tool_results[cache_key], False, dur, True, None

    try:
        res = tool_registry.execute(tool_call.name, **tool_call.arguments)
        res_str = serialize_tool_result(res)
        ok = True
        if cache_key and non_retriable_tool_results is not None and _is_non_retriable_tool_result(res):
            non_retriable_tool_results[cache_key] = res_str
    except Exception as e:
        res_str = json.dumps({"error": str(e)})
        ok = False
        logger.warning("Tool '%s' failed: %s", tool_call.name, e)
    dur = round(time.time() - t0, 2)
    return tool_call, res_str, ok, dur, False, None


def redact_diagnostic_value(value: Any, *, limit: int = _SUMMARY_LIMIT) -> str:
    """Return a redacted and truncated diagnostic preview."""
    try:
        if isinstance(value, str):
            text = _redact_json_string_if_possible(value)
        else:
            text = json.dumps(_redact_structured_secrets(value), ensure_ascii=False, default=str)
    except Exception:
        try:
            text = str(value)
        except Exception:
            text = "<unserializable>"

    text = _AUTH_PATTERN.sub(r"\1[REDACTED]", text)
    text = _URL_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]@", text)
    text = _QUOTED_SECRET_FIELD_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]{m.group(3)}", text)
    text = _HEADER_SECRET_PATTERN.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = _TOKEN_PATTERN.sub("[REDACTED_TOKEN]", text)
    text = _HOME_PATH_PATTERN.sub(lambda m: f"{m.group(1).rsplit('/', 1)[0] if '/' in m.group(1) else m.group(1)}/[REDACTED_PATH]", text)
    if len(text) > limit:
        return f"{text[:limit]}...<truncated {len(text) - limit} chars>"
    return text


def build_tool_audit(
    *,
    tool_name: str,
    arguments: Any,
    result: Any = None,
    error_code: Optional[str] = None,
    duration: float = 0.0,
    context: Optional[ToolAccessContext] = None,
) -> Dict[str, Any]:
    """Build a redacted Tool Surface audit record."""
    ctx = context or ToolAccessContext()
    payload = {
        "tool_name": tool_name,
        "arguments_summary": redact_diagnostic_value(arguments),
        "duration": round(duration, 4),
        "result_summary": redact_diagnostic_value(result),
        "error_code": error_code,
        "backend": ctx.backend,
        "session_id": ctx.session_id,
    }
    if ctx.audit_context:
        payload["audit_context"] = redact_diagnostic_value(ctx.audit_context)
    return payload
