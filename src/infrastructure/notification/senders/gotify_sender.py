# -*- coding: utf-8 -*-
"""Gotify notification sender."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import requests

from src.config import Config

# resolve_gotify_message_endpoint 已于 R2-B2 次子步下沉
# src/domain/notification/endpoints.py（纯 urlparse 规则）；此处 re-export
# 保留旧导入面，仅兼容 sender 模块自身、包聚合与外部按该路径导入的调用方。
from src.domain.notification.endpoints import resolve_gotify_message_endpoint


logger = logging.getLogger(__name__)


class GotifySender:
    """Send Markdown text notifications through Gotify's message API."""

    def __init__(self, config: Config):
        self._gotify_url = getattr(config, "gotify_url", None)
        self._gotify_token = getattr(config, "gotify_token", None)
        self._webhook_verify_ssl = getattr(config, "webhook_verify_ssl", True)

    def _is_gotify_configured(self) -> bool:
        return bool((self._gotify_url or "").strip() and (self._gotify_token or "").strip())

    def _resolve_gotify_endpoint(self) -> Optional[str]:
        return resolve_gotify_message_endpoint(self._gotify_url)

    def send_to_gotify(
        self,
        content: str,
        title: Optional[str] = None,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """Publish a notification to Gotify using JSON and header auth."""
        if not self._is_gotify_configured():
            logger.warning("Gotify 配置不完整，跳过推送")
            return False

        endpoint = self._resolve_gotify_endpoint()
        if not endpoint:
            logger.error("GOTIFY_URL 必须是 Gotify server base URL，不包含 /message")
            return False

        if title is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
            title = f"📈 股票分析报告 - {date_str}"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "HermesX",
            "X-Gotify-Key": str(self._gotify_token).strip(),
        }
        payload = {
            "title": title,
            "message": content,
            "extras": {
                "client::display": {
                    "contentType": "text/markdown",
                },
            },
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=timeout_seconds or 10,
                verify=self._webhook_verify_ssl,
            )
            if 200 <= response.status_code < 300:
                logger.info("Gotify 消息发送成功")
                return True

            logger.error("Gotify 请求失败: HTTP %s", response.status_code)
            logger.debug("Gotify 响应内容: %s", response.text)
            return False
        except requests.exceptions.Timeout:
            logger.error("发送 Gotify 消息失败: 请求超时")
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("发送 Gotify 消息失败: 网络请求异常")
            logger.debug("Gotify 请求异常类型: %s", type(exc).__name__)
            return False
        except Exception as exc:
            logger.error("发送 Gotify 消息失败: 未知异常")
            logger.debug("Gotify 未知异常类型: %s", type(exc).__name__)
            return False
