# -*- coding: utf-8 -*-
"""URL / 主机名安全校验纯规则（§4.3 拆分 F2：自 ``system_config_service`` 逐字下沉）。

职责：scheme 白名单校验、libc 风格数值 IPv4 主机规范化、IDNA/UNICODE 主机归一、
SSRF 防护（云元数据地址/链路本地段拦截）、LLM base URL 合法性校验，以及
base URL → `/models` 端点的纯字符串推导。全部为无 IO 的确定性纯函数
（socket/idna/ipaddress 仅本地解析，不发起任何网络访问）。

由 ``src.application.runtime.system_config_service`` re-export 消费（tests 经模块全局
穿透 patch/直调的契约保持不变）；行为与拆分前逐字一致。
"""

from __future__ import annotations

from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse


def _is_valid_url(value: str, allowed_schemes: Tuple[str, ...]) -> bool:
    """Return True when *value* looks like a valid absolute URL."""
    parsed = urlparse(value)
    return parsed.scheme in allowed_schemes and bool(parsed.netloc)


def _canonical_ipv4_numeric_host(host: str) -> Optional[str]:
    """Return canonical IPv4 for libc-style numeric host aliases."""
    import socket

    candidate = (host or "").lower()
    if not candidate or ":" in candidate:
        return None

    try:
        return socket.inet_ntoa(socket.inet_aton(candidate))
    except (OSError, ValueError):
        return None


def _is_noncanonical_ipv4_numeric_host(host: str) -> bool:
    canonical = _canonical_ipv4_numeric_host(host)
    return canonical is not None and host.lower() != canonical


def _normalize_hostname_for_security(host: str) -> Optional[str]:
    """Return a normalized ASCII host for URL safety checks."""
    import unicodedata

    candidate = (host or "").strip().lower().rstrip(".")
    if not candidate:
        return None
    if ":" in candidate:
        return candidate
    try:
        normalized = unicodedata.normalize("NFKC", candidate)
        ascii_host = normalized.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError:
        return None
    return ascii_host or None


def _is_valid_llm_base_url(value: str, allowed_schemes: Tuple[str, ...] = ("http", "https")) -> bool:
    """Return True when an LLM base URL is safe to parse consistently."""
    if not value:
        return False
    if any(char == "\\" or char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        return False

    try:
        parsed = urlparse(value)
        host = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False

    if parsed.scheme not in allowed_schemes or not parsed.netloc or not host:
        return False
    if "@" in parsed.netloc or parsed.username is not None or parsed.password is not None:
        return False
    if _is_noncanonical_ipv4_numeric_host(host):
        return False

    return True


def _is_safe_base_url(value: str) -> bool:
    """Block link-local and cloud metadata addresses to prevent SSRF.

    Allows localhost / private-LAN addresses (e.g. Ollama on 192.168.x.x)
    but blocks 169.254.x.x (AWS/Azure/GCP/Alibaba instance-metadata service)
    and other known metadata hostnames.
    """
    import ipaddress

    try:
        parsed = urlparse(value)
        raw_host = parsed.hostname or ""
    except ValueError:
        return False
    if not raw_host:
        return True
    host = _normalize_hostname_for_security(raw_host)
    if not host:
        return False
    # Known cloud metadata hostnames
    _BLOCKED_HOSTS = frozenset({
        "169.254.169.254",
        "metadata.google.internal",
        "100.100.100.200",
    })
    if host in _BLOCKED_HOSTS:
        return False
    if _is_noncanonical_ipv4_numeric_host(host):
        return False
    # Numeric IPs: block link-local range (169.254.0.0/16), including IPv4-mapped IPv6.
    try:
        addr = ipaddress.ip_address(host)
        candidate_addrs = [addr]
        mapped_addr = getattr(addr, "ipv4_mapped", None)
        if mapped_addr is not None:
            candidate_addrs.append(mapped_addr)
        for candidate_addr in candidate_addrs:
            if str(candidate_addr) in _BLOCKED_HOSTS or candidate_addr.is_link_local:
                return False
    except ValueError:
        pass  # hostname, not an IP — already checked against blocklist above
    return True


def _build_llm_models_url(base_url: str) -> str:
    """Convert a channel base URL into a `/models` endpoint."""
    if not _is_valid_llm_base_url(base_url):
        raise ValueError("LLM channel base URL must be a valid absolute URL")
    if not _is_safe_base_url(base_url):
        raise ValueError("LLM channel base URL points to a restricted address")

    parsed = urlparse(base_url)
    normalized = (parsed.path or "").rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    if normalized.endswith("/models"):
        models_path = normalized or "/models"
    else:
        models_path = f"{normalized}/models" if normalized else "/models"
    models_url = urlunparse((parsed.scheme, parsed.netloc, models_path, "", "", ""))
    if not _is_valid_llm_base_url(models_url):
        raise ValueError("LLM channel models URL must be a valid absolute URL")
    if not _is_safe_base_url(models_url):
        raise ValueError("LLM channel models URL points to a restricted address")
    return models_url
