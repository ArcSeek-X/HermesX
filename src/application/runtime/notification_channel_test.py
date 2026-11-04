"""Notification test configuration, dispatch and result sanitization.

The caller supplies the merged configuration and lazy dispatch dependency.
"""

from __future__ import annotations
import re
import time
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse, urlunparse
import requests
from src.config import Config, parse_env_bool, parse_env_int
from src.domain.notification.contracts import FEISHU_APP_BOT_ENV_GROUP, FEISHU_WEBHOOK_ENV_GROUP
from src.domain.notification.endpoints import resolve_gotify_message_endpoint, resolve_ntfy_endpoint
from src.application.runtime.llm_config_validation import _split_csv
from src.application.runtime.system_config_ports import NotificationDispatchPort
from typing import Callable
from src.application.runtime.config_probe_diagnostics import _sanitize_llm_error_text

logger = logging.getLogger("src.application.runtime.system_config_service")

_NOTIFICATION_TEST_CHANNELS: Tuple[str, ...] = (
    "wechat",
    "dingtalk",
    "feishu",
    "telegram",
    "email",
    "pushover",
    "ntfy",
    "gotify",
    "pushplus",
    "serverchan3",
    "custom",
    "discord",
    "slack",
    "astrbot",
)

_NOTIFICATION_TEST_KEY_MAP: Dict[str, Tuple[str, str]] = {
    "WECHAT_WEBHOOK_URL": ("wechat_webhook_url", "string"),
    "WECHAT_MSG_TYPE": ("wechat_msg_type", "string"),
    "WECHAT_MAX_BYTES": ("wechat_max_bytes", "int"),
    "FEISHU_WEBHOOK_URL": ("feishu_webhook_url", "string"),
    "FEISHU_WEBHOOK_SECRET": ("feishu_webhook_secret", "string"),
    "FEISHU_WEBHOOK_KEYWORD": ("feishu_webhook_keyword", "string"),
    "FEISHU_MAX_BYTES": ("feishu_max_bytes", "int"),
    "FEISHU_SEND_AS_FILE": ("feishu_send_as_file", "bool"),
    "DINGTALK_WEBHOOK_URL": ("dingtalk_webhook_url", "string"),
    "DINGTALK_SECRET": ("dingtalk_secret", "string"),
    "FEISHU_APP_ID": ("feishu_app_id", "string"),
    "FEISHU_APP_SECRET": ("feishu_app_secret", "string"),
    "FEISHU_CHAT_ID": ("feishu_chat_id", "string"),
    "FEISHU_RECEIVE_ID_TYPE": ("feishu_receive_id_type", "string"),
    "FEISHU_DOMAIN": ("feishu_domain", "string"),
    "TELEGRAM_BOT_TOKEN": ("telegram_bot_token", "string"),
    "TELEGRAM_CHAT_ID": ("telegram_chat_id", "string"),
    "TELEGRAM_MESSAGE_THREAD_ID": ("telegram_message_thread_id", "string"),
    "EMAIL_SENDER": ("email_sender", "string"),
    "EMAIL_SENDER_NAME": ("email_sender_name", "string"),
    "EMAIL_PASSWORD": ("email_password", "string"),
    "EMAIL_RECEIVERS": ("email_receivers", "csv"),
    "PUSHOVER_USER_KEY": ("pushover_user_key", "string"),
    "PUSHOVER_API_TOKEN": ("pushover_api_token", "string"),
    "NTFY_URL": ("ntfy_url", "string"),
    "NTFY_TOKEN": ("ntfy_token", "string"),
    "GOTIFY_URL": ("gotify_url", "string"),
    "GOTIFY_TOKEN": ("gotify_token", "string"),
    "PUSHPLUS_TOKEN": ("pushplus_token", "string"),
    "PUSHPLUS_TOPIC": ("pushplus_topic", "string"),
    "SERVERCHAN3_SENDKEY": ("serverchan3_sendkey", "string"),
    "CUSTOM_WEBHOOK_URLS": ("custom_webhook_urls", "csv"),
    "CUSTOM_WEBHOOK_BEARER_TOKEN": ("custom_webhook_bearer_token", "string"),
    "CUSTOM_WEBHOOK_BODY_TEMPLATE": ("custom_webhook_body_template", "string"),
    "WEBHOOK_VERIFY_SSL": ("webhook_verify_ssl", "bool"),
    "DISCORD_WEBHOOK_URL": ("discord_webhook_url", "string"),
    "DISCORD_BOT_TOKEN": ("discord_bot_token", "string"),
    "DISCORD_MAIN_CHANNEL_ID": ("discord_main_channel_id", "string"),
    "DISCORD_CHANNEL_ID": ("discord_main_channel_id", "string"),
    "DISCORD_MAX_WORDS": ("discord_max_words", "int"),
    "SLACK_WEBHOOK_URL": ("slack_webhook_url", "string"),
    "SLACK_BOT_TOKEN": ("slack_bot_token", "string"),
    "SLACK_CHANNEL_ID": ("slack_channel_id", "string"),
    "ASTRBOT_URL": ("astrbot_url", "string"),
    "ASTRBOT_TOKEN": ("astrbot_token", "string"),
}

_NOTIFICATION_REQUIRED_KEY_GROUPS: Dict[str, Tuple[Tuple[str, ...], ...]] = {
    "wechat": (("WECHAT_WEBHOOK_URL",),),
    "dingtalk": (("DINGTALK_WEBHOOK_URL",),),
    "feishu": (FEISHU_WEBHOOK_ENV_GROUP, FEISHU_APP_BOT_ENV_GROUP),
    "telegram": (("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"),),
    "email": (("EMAIL_SENDER", "EMAIL_PASSWORD"),),
    "pushover": (("PUSHOVER_USER_KEY", "PUSHOVER_API_TOKEN"),),
    "ntfy": (("NTFY_URL",),),
    "gotify": (("GOTIFY_URL", "GOTIFY_TOKEN"),),
    "pushplus": (("PUSHPLUS_TOKEN",),),
    "serverchan3": (("SERVERCHAN3_SENDKEY",),),
    "custom": (("CUSTOM_WEBHOOK_URLS",),),
    "discord": (
        ("DISCORD_WEBHOOK_URL",),
        ("DISCORD_BOT_TOKEN", "DISCORD_MAIN_CHANNEL_ID"),
        ("DISCORD_BOT_TOKEN", "DISCORD_CHANNEL_ID"),
    ),
    "slack": (("SLACK_WEBHOOK_URL",), ("SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID")),
    "astrbot": (("ASTRBOT_URL",),),
}

_NOTIFICATION_TEST_TARGET_KEYS: Dict[str, Tuple[str, ...]] = {
    "wechat": ("WECHAT_WEBHOOK_URL",),
    "dingtalk": ("DINGTALK_WEBHOOK_URL",),
    "feishu": FEISHU_WEBHOOK_ENV_GROUP + FEISHU_APP_BOT_ENV_GROUP,
    "telegram": ("TELEGRAM_BOT_TOKEN",),
    "email": ("EMAIL_RECEIVERS", "EMAIL_SENDER"),
    "pushover": ("PUSHOVER_USER_KEY",),
    "ntfy": ("NTFY_URL",),
    "gotify": ("GOTIFY_URL",),
    "pushplus": ("PUSHPLUS_TOPIC",),
    "serverchan3": ("SERVERCHAN3_SENDKEY",),
    "custom": ("CUSTOM_WEBHOOK_URLS",),
    "discord": ("DISCORD_WEBHOOK_URL", "DISCORD_MAIN_CHANNEL_ID", "DISCORD_CHANNEL_ID"),
    "slack": ("SLACK_WEBHOOK_URL", "SLACK_CHANNEL_ID"),
    "astrbot": ("ASTRBOT_URL",),
}


class NotificationChannelTester:
    """Run an isolated, non-persisting notification test through the dispatch port."""

    _NOTIFICATION_TEST_CHANNELS = _NOTIFICATION_TEST_CHANNELS
    _NOTIFICATION_TEST_KEY_MAP = _NOTIFICATION_TEST_KEY_MAP
    _NOTIFICATION_REQUIRED_KEY_GROUPS = _NOTIFICATION_REQUIRED_KEY_GROUPS
    _NOTIFICATION_TEST_TARGET_KEYS = _NOTIFICATION_TEST_TARGET_KEYS

    def __init__(self, dispatch_port_provider: Callable[[], NotificationDispatchPort]):
        """构造通知渠道测试服务：装配分发端口提供者。"""
        self._dispatch_port_provider = dispatch_port_provider

    def test_notification_channel(
        self,
        *,
        channel: str,
        effective_map: Dict[str, str],
        title: str = "HRS 通知测试",
        content: str = "这是一条来自 HRS Web 设置页的通知测试消息。",
        timeout_seconds: float = 20.0,
    ) -> Dict[str, Any]:
        """Send one real notification test without persisting submitted values."""
        normalized_channel = (channel or "").strip().lower()
        if normalized_channel not in self._NOTIFICATION_TEST_CHANNELS:
            raise ValueError(f"Unsupported notification channel: {channel}")

        missing = self._get_missing_notification_test_keys(normalized_channel, effective_map)
        if missing:
            return self._build_notification_test_result(
                success=False,
                message=f"通知渠道配置不完整，缺少: {', '.join(missing)}",
                error_code="config_missing",
                stage="config_validation",
                retryable=False,
                latency_ms=None,
                attempts=[],
            )
        invalid_message = self._get_invalid_notification_test_config_message(
            normalized_channel,
            effective_map,
        )
        if invalid_message:
            return self._build_notification_test_result(
                success=False,
                message=invalid_message,
                error_code="config_invalid",
                stage="config_validation",
                retryable=False,
                latency_ms=None,
                attempts=[],
            )

        config = self._build_notification_test_config(effective_map)
        try:
            return self._dispatch_notification_test(
                channel=normalized_channel,
                config=config,
                effective_map=effective_map,
                title=title.strip(),
                content=content.strip(),
                timeout_seconds=float(timeout_seconds),
            )
        except Exception as exc:
            logger.warning("Notification channel test failed for %s: %s", normalized_channel, exc)
            error_code, retryable = self._classify_notification_exception(exc)
            return self._build_notification_test_result(
                success=False,
                message=f"通知测试异常: {exc}",
                error_code=error_code,
                stage="notification_send",
                retryable=retryable,
                latency_ms=None,
                attempts=[
                    {
                        "channel": normalized_channel,
                        "success": False,
                        "message": str(exc),
                        "target": self._resolve_notification_test_target(normalized_channel, effective_map),
                        "error_code": error_code,
                        "stage": "notification_send",
                        "retryable": retryable,
                        "latency_ms": None,
                    }
                ],
            )

    def _get_missing_notification_test_keys(
        self,
        channel: str,
        effective_map: Dict[str, str],
    ) -> List[str]:
        """Return missing keys for a channel, honoring alternative key groups."""
        groups = self._NOTIFICATION_REQUIRED_KEY_GROUPS.get(channel, ())
        if not groups:
            return []

        missing_by_group: List[List[str]] = []
        for group in groups:
            missing = [key for key in group if not (effective_map.get(key) or "").strip()]
            if not missing:
                return []
            missing_by_group.append(missing)

        if not missing_by_group:
            return []
        ranked_groups = []
        for group, missing in zip(groups, missing_by_group):
            present_count = len(group) - len(missing)
            ranked_groups.append((len(missing), -present_count, missing))
        ranked_groups.sort(key=lambda item: (item[0], item[1]))
        return ranked_groups[0][2]

    @staticmethod
    def _get_invalid_notification_test_config_message(
        channel: str,
        effective_map: Dict[str, str],
    ) -> Optional[str]:
        """返回通知测试配置不合法时的提示文案。"""
        if channel == "ntfy":
            ntfy_url = (effective_map.get("NTFY_URL") or "").strip()
            if not ntfy_url:
                return None
            ntfy_server_url, ntfy_topic = resolve_ntfy_endpoint(ntfy_url)
            if ntfy_server_url and ntfy_topic:
                return None
            return "NTFY_URL 必须包含 topic path，例如 https://ntfy.sh/my-topic。"
        if channel == "gotify":
            gotify_url = (effective_map.get("GOTIFY_URL") or "").strip()
            if not gotify_url:
                return None
            if resolve_gotify_message_endpoint(gotify_url):
                return None
            return "GOTIFY_URL 必须是 Gotify server base URL，不包含 /message。"
        return None

    def _build_notification_test_config(self, effective_map: Dict[str, str]) -> Config:
        """Build an isolated Config instance for notification testing."""
        kwargs: Dict[str, Any] = {"stock_list": []}
        for key, (attr, value_type) in self._NOTIFICATION_TEST_KEY_MAP.items():
            if key not in effective_map:
                continue
            if key == "DISCORD_CHANNEL_ID" and (effective_map.get("DISCORD_MAIN_CHANNEL_ID") or "").strip():
                continue
            raw_value = effective_map.get(key, "")
            kwargs[attr] = self._parse_notification_test_value(key, raw_value, value_type)
        return Config(**kwargs)

    def _parse_notification_test_value(self, key: str, value: str, value_type: str) -> Any:
        """按声明类型解析通知测试配置值。"""
        if value_type == "csv":
            return _split_csv(value)
        if value_type == "bool":
            return parse_env_bool(value, default=True)
        if value_type == "int":
            defaults = {
                "WECHAT_MAX_BYTES": 4000,
                "FEISHU_MAX_BYTES": 20000,
                "DISCORD_MAX_WORDS": 2000,
            }
            return parse_env_int(value, defaults.get(key, 0), field_name=key, minimum=1)
        stripped = (value or "").strip()
        return stripped or None

    def _dispatch_notification_test(
        self,
        *,
        channel: str,
        config: Config,
        effective_map: Dict[str, str],
        title: str,
        content: str,
        timeout_seconds: float,
    ) -> Dict[str, Any]:
        """向指定渠道发起一次通知测试发送。"""
        dispatch_port = self._dispatch_port_provider()

        started_at = time.perf_counter()
        target = self._resolve_notification_test_target(channel, effective_map)
        titled_content = self._build_notification_test_content(title, content)

        if channel == "custom":
            attempts = dispatch_port.test_custom_webhooks(
                config=config,
                content=titled_content,
                timeout_seconds=timeout_seconds,
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            success_count = sum(1 for attempt in attempts if bool(attempt.get("success")))
            total_count = len(attempts)
            success = success_count > 0
            if success_count == total_count and total_count > 0:
                message = f"自定义 Webhook 通知测试成功（{success_count}/{total_count}）"
            elif success_count > 0:
                message = f"自定义 Webhook 通知测试部分成功（{success_count}/{total_count}）"
            else:
                message = f"自定义 Webhook 通知测试失败（{success_count}/{total_count}）"
            return self._build_notification_test_result(
                success=success,
                message=message,
                error_code=None if success else "send_failed",
                stage="notification_send",
                retryable=any(bool(attempt.get("retryable")) for attempt in attempts),
                latency_ms=latency_ms,
                attempts=attempts,
            )

        ok = bool(
            dispatch_port.send_channel_test(
                channel=channel,
                config=config,
                titled_content=titled_content,
                title=title,
                content=content,
                timeout_seconds=timeout_seconds,
            )
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        attempt = {
            "channel": channel,
            "success": ok,
            "message": "通知测试发送成功" if ok else "通知测试发送失败",
            "target": target,
            "error_code": None if ok else "send_failed",
            "stage": "notification_send",
            "retryable": False,
            "latency_ms": latency_ms,
        }
        return self._build_notification_test_result(
            success=ok,
            message=f"{channel} 通知测试成功" if ok else f"{channel} 通知测试失败",
            error_code=None if ok else "send_failed",
            stage="notification_send",
            retryable=False,
            latency_ms=latency_ms,
            attempts=[attempt],
        )

    @staticmethod
    def _build_notification_test_content(title: str, content: str) -> str:
        """构造通知测试的标题与正文内容。"""
        title = title.strip()
        content = content.strip()
        return f"{title}\n\n{content}" if title else content

    def _resolve_notification_test_target(self, channel: str, effective_map: Dict[str, str]) -> str:
        """解析指定渠道的测试接收目标。"""
        for key in self._NOTIFICATION_TEST_TARGET_KEYS.get(channel, ()):
            raw_value = (effective_map.get(key) or "").strip()
            if not raw_value:
                continue
            if key == "CUSTOM_WEBHOOK_URLS":
                first_url = _split_csv(raw_value)[0] if _split_csv(raw_value) else ""
                return self._mask_notification_target(first_url, source_key=key)
            return self._mask_notification_target(raw_value, source_key=key)
        return channel

    @classmethod
    def _build_notification_test_result(
        cls,
        *,
        success: bool,
        message: str,
        error_code: Optional[str],
        stage: Optional[str],
        retryable: bool,
        latency_ms: Optional[int],
        attempts: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """构造通知测试的结构化结果。"""
        sanitized_attempts = [cls._sanitize_notification_attempt(attempt) for attempt in attempts]
        return {
            "success": success,
            "message": cls._sanitize_notification_text(message),
            "error_code": error_code,
            "stage": stage,
            "retryable": retryable,
            "latency_ms": latency_ms,
            "attempts": sanitized_attempts,
        }

    @classmethod
    def _sanitize_notification_attempt(cls, attempt: Dict[str, Any]) -> Dict[str, Any]:
        """清洗单次发送尝试记录中的敏感字段。"""
        sanitized = dict(attempt)
        if "message" in sanitized:
            sanitized["message"] = cls._sanitize_notification_text(sanitized["message"])
        if "target" in sanitized:
            sanitized["target"] = cls._mask_notification_target(str(sanitized.get("target") or ""))
        return sanitized

    @classmethod
    def _sanitize_notification_text(cls, text: Any) -> str:
        """清洗通知文本中的敏感信息。"""
        sanitized = _sanitize_llm_error_text(text)
        if not sanitized:
            return ""
        sanitized = re.sub(r"(?i)(bearer\s+)[a-z0-9._\-:]+", r"\1[REDACTED]", sanitized)
        sanitized = re.sub(r"(?i)(token|secret|password|sendkey)([=:]\s*)[^\s,;&]+", r"\1\2[REDACTED]", sanitized)
        sanitized = re.sub(
            r"https?://[^\s]+",
            lambda match: cls._mask_notification_target(match.group(0)),
            sanitized,
        )
        return sanitized[:300]

    @staticmethod
    def _mask_notification_target(target: str, *, source_key: Optional[str] = None) -> str:
        """对通知目标做脱敏处理。"""
        value = (target or "").strip()
        if not value:
            return ""
        source_key_upper = (source_key or "").upper()
        sensitive_source = any(
            marker in source_key_upper for marker in ("TOKEN", "PASSWORD", "SECRET", "SENDKEY", "USER_KEY", "API_KEY")
        )
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            if sensitive_source:
                return "***"
            if len(value) > 10:
                return f"{value[:3]}***{value[-2:]}"
            return value

        safe_netloc = parsed.netloc.rsplit("@", 1)[-1]
        safe_segments: List[str] = []
        path_segments = parsed.path.split("/")
        last_non_empty_index = next(
            (index for index in range(len(path_segments) - 1, -1, -1) if path_segments[index]),
            -1,
        )
        for index, segment in enumerate(path_segments):
            if not segment:
                safe_segments.append(segment)
                continue
            lower = segment.lower()
            looks_secret = (
                (source_key_upper == "NTFY_URL" and index == last_non_empty_index)
                or len(segment) >= 16
                or lower.startswith("bot")
                or "token" in lower
                or "sendkey" in lower
                or "secret" in lower
                or re.search(r"[a-zA-Z].*\d|\d.*[a-zA-Z]", segment) is not None
                and len(segment) >= 10
            )
            if looks_secret:
                safe_segments.append("***")
            else:
                safe_segments.append(segment)

        query = ""
        if parsed.query:
            query = "&".join(
                f"{part.split('=', 1)[0]}=***" if "=" in part else "***" for part in parsed.query.split("&") if part
            )
        return urlunparse((parsed.scheme, safe_netloc, "/".join(safe_segments), "", query, ""))

    @staticmethod
    def _classify_notification_exception(exc: Exception) -> Tuple[str, bool]:
        """将通知异常归类为错误码与是否可重试。"""
        if isinstance(exc, requests.exceptions.Timeout):
            return "timeout", True
        if isinstance(exc, requests.exceptions.ConnectionError):
            return "network_error", True
        if isinstance(exc, requests.exceptions.RequestException):
            return "network_error", True
        return "unexpected_error", False
