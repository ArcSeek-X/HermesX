# -*- coding: utf-8 -*-
"""通知渠道 endpoint 解析纯规则。

落位：``src/domain/notification/``（R2-B2 次子步，仅依赖 stdlib
``urllib.parse`` + ``typing``，零 IO / 零外层引用）。

这两个函数原先定义在 ``src/infrastructure/notification/senders/gotify_sender.py`` /
``ntfy_sender.py`` 内，由各 Sender 自身与三个 ``src/application/`` 消费者引用
（``alert/notification_diagnostics.py``、``runtime/system_config_service.py``、
``notification/notification.py``）。一旦 sender 物理搬入
``src/infrastructure/notification/``（R2-B5），那几条边会变成 application →
infrastructure 禁入违规，因此先把纯规则下沉 domain，消费方一律直连本模块。
sender 侧保留 re-export 过渡，仅用于兼容 ``src/infrastructure/notification/senders/__init__.py``
的包聚合面与外部按 sender 模块路径导入的调用方，待 R2-B5 一并收敛。
"""

from __future__ import annotations

from typing import Optional, Tuple
from urllib.parse import unquote, urlparse, urlunparse


def resolve_gotify_message_endpoint(gotify_url: Optional[str]) -> Optional[str]:
    """Resolve GOTIFY_URL server base into the fixed /message endpoint."""
    raw_url = (gotify_url or "").strip().rstrip("/")
    if not raw_url:
        return None

    parsed = urlparse(raw_url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.query or parsed.fragment:
        return None

    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if path_segments and path_segments[-1].lower() == "message":
        return None

    base_url = urlunparse(
        parsed._replace(
            path="/" + "/".join(path_segments) if path_segments else "",
            params="",
            query="",
            fragment="",
        )
    ).rstrip("/")
    return f"{base_url}/message"


def resolve_ntfy_endpoint(ntfy_url: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Split NTFY_URL into server root and topic from the final path segment."""
    raw_url = (ntfy_url or "").strip().rstrip("/")
    if not raw_url:
        return None, None

    parsed = urlparse(raw_url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None, None

    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if not path_segments:
        return None, None

    topic = unquote(path_segments[-1]).strip()
    if not topic:
        return None, None

    root_path = "/".join(path_segments[:-1])
    server_url = urlunparse(
        parsed._replace(
            path=f"/{root_path}" if root_path else "",
            params="",
            query="",
            fragment="",
        )
    ).rstrip("/")

    return server_url, topic
