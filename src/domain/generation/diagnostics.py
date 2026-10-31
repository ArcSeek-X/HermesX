# -*- coding: utf-8 -*-
"""诊断文本脱敏纯规则。

R2-A2 起本模块是脱敏规则的**唯一真源**。原 ``src/llm/local_cli_backend.py``
的同对象重导出已随 R2-A4 搬包进入 ``src/infrastructure/generation/local_cli_backend.py``。

必须整簇迁移：``redact_diagnostic_text`` 依赖 4 个私有辅助函数与 2 个模块常量；
``PREVIEW_LIMIT`` 同时被 ``local_cli_backend`` 用作 stdout/stderr 预览字节上限
（``limit_bytes=PREVIEW_LIMIT * 4``），因此只能反向 import 同一对象，不可复制常量值。

零 IO、零第三方依赖，符合 ``src/domain/`` 分层约束。
"""

from __future__ import annotations

import os
import re
from typing import Match, Optional
from urllib.parse import parse_qsl, urlsplit


PREVIEW_LIMIT = 800

_URL_PATTERN = re.compile(r"https?://[^\s,;)\]}]+", re.IGNORECASE)
_SENSITIVE_URL_KEY_PARTS = {
    "access_token",
    "api_key",
    "apikey",
    "auth_token",
    "authorization",
    "cookie",
    "password",
    "secret",
    "sendkey",
    "token",
    "webhook",
}


def redact_diagnostic_text(text: str, *, home: Optional[str] = None, limit: int = PREVIEW_LIMIT) -> str:
    """Redact sensitive diagnostics and return a bounded preview."""

    redacted = text or ""
    home_path = home or os.path.expanduser("~")
    if home_path:
        redacted = redacted.replace(home_path, "~")
    redacted = re.sub(r"([a-zA-Z][a-zA-Z0-9+.-]*://)[^/\s:@]+:[^@\s/]+@", r"\1<redacted>@", redacted)
    redacted = _URL_PATTERN.sub(_redact_sensitive_diagnostic_url, redacted)
    redacted = re.sub(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?[^\s]+", r"\1<redacted>", redacted)
    redacted = re.sub(r"(?i)(cookie\s*[:=]\s*)[^\n\r]+", r"\1<redacted>", redacted)
    redacted = re.sub(r"(?i)(session[_-]?secret\s*[:=]\s*)[^\s]+", r"\1<redacted>", redacted)
    redacted = re.sub(r"\b(sk-[A-Za-z0-9_-]{12,})\b", "<redacted-api-key>", redacted)
    redacted = re.sub(r"\b(AIza[A-Za-z0-9_-]{16,})\b", "<redacted-api-key>", redacted)
    redacted = re.sub(r"\b(gh[pousr]_[A-Za-z0-9_]{16,})\b", "<redacted-token>", redacted)
    # Conservative by design: local CLI diagnostics may contain opaque long-lived credentials.
    redacted = re.sub(r"\b([A-Za-z0-9_-]{32,})\b", "<redacted-token>", redacted)
    if len(redacted) > limit:
        return redacted[:limit] + "...<truncated>"
    return redacted


def _redact_sensitive_diagnostic_url(match: Match[str]) -> str:
    url = match.group(0)
    return "<redacted-url>" if _is_sensitive_diagnostic_url(url) else url


def _is_sensitive_diagnostic_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return True
    if parsed.username or parsed.password:
        return True
    if _is_webhook_diagnostic_url(parsed.hostname or "", parsed.path):
        return True
    return (
        _has_sensitive_url_params(parsed.query)
        or _has_sensitive_url_params(parsed.fragment)
    )


def _is_webhook_diagnostic_url(hostname: str, path: str) -> bool:
    hostname = str(hostname or "").lower().strip(".")
    normalized_path = f"/{path.lstrip('/').lower()}"
    path_segments = {segment for segment in normalized_path.split("/") if segment}

    if hostname == "hooks.slack.com" and normalized_path.startswith("/services/"):
        return True
    if hostname == "oapi.dingtalk.com" and normalized_path.startswith("/robot/send"):
        return True
    if hostname in {"discord.com", "discordapp.com"} and "/api/webhooks/" in normalized_path:
        return True
    if hostname == "open.feishu.cn" and "/open-apis/bot/" in normalized_path and "/hook/" in normalized_path:
        return True
    if hostname == "qyapi.weixin.qq.com" and normalized_path.startswith("/cgi-bin/webhook/send"):
        return True
    if hostname.startswith("hooks."):
        return True
    return bool({"hook", "webhook", "webhooks"} & path_segments)


def _has_sensitive_url_params(params_text: str) -> bool:
    if not params_text:
        return False
    try:
        params = parse_qsl(params_text, keep_blank_values=True)
    except ValueError:
        return True
    for key, value in params:
        key_text = str(key or "").strip().lower().replace("-", "_")
        if key_text in _SENSITIVE_URL_KEY_PARTS or any(part in key_text for part in _SENSITIVE_URL_KEY_PARTS):
            return True
        if re.search(r"\b(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{16,}|[A-Za-z0-9_-]{32,})\b", str(value or "")):
            return True
    return False
