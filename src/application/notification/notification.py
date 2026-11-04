# -*- coding: utf-8 -*-
"""
===================================
A股自选股智能分析系统 - 通知层
===================================

职责：
1. 汇总分析结果生成日报
2. 支持 Markdown 格式输出
3. 多渠道推送（自动识别）：
   - 企业微信 Webhook
   - 飞书 Webhook
   - Telegram Bot
   - 邮件 SMTP
   - Pushover（手机/桌面推送）
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from enum import Enum

from src.config import Config, get_config
from src.domain.shared.enums import ReportType
from src.application.market.phase_summary import format_public_market_status_line, format_public_phase_pack_excerpt
from src.domain.notification.routing import (
    get_notification_route_config,
    split_notification_route_channels,
)
from src.domain.notification.contracts import is_feishu_static_configured
from src.application.notification.noise import (
    NotificationNoiseDecision,
    evaluate_notification_noise,
    record_notification_noise,
    release_notification_noise,
)
from src.domain.shared.report_language import (
    get_localized_stock_name,
    get_report_labels,
    get_signal_level,
    get_chip_unavailable_reason,
    is_chip_structure_unavailable,
    localize_chip_health,
    localize_conflict_severity,
    localize_consensus_level,
    localize_strategy_signal,
    localize_strategy_synthesis_summary,
    localize_trend_prediction,
    normalize_report_language,
    normalize_strategy_synthesis_payload,
    strategy_invalid_opinion_count,
)
from src.domain.decision.action import (
    display_action_fields_for_result,
    display_decision_type_for_result,
    display_operation_advice_for_result,
)
from src.domain.notification.bot_message import BotMessage
from src.utils.sanitize import sanitize_diagnostic_text
from src.utils.data_processing import (
    signal_attribution_has_content,
    signal_attribution_weight_items,
    normalize_model_used,
)
from src.domain.notification.rendering import (
    append_phase_decision_block as _append_phase_decision_block_impl,
    append_strategy_synthesis_block as _append_strategy_synthesis_block,
    clean_sniper_value as _clean_sniper_value_impl,
    escape_markdown_name as _escape_markdown_name,
    format_amount_cn as _format_amount_cn_impl,
    format_net_shares as _format_net_shares_impl,
    format_per_share as _format_per_share_impl,
    format_percent as _format_percent_impl,
    format_text as _format_text_impl,
    phase_decision_has_content as _phase_decision_has_content_impl,
    phase_decision_list as _phase_decision_list_impl,
    safe_float as _safe_float,
    source_display_name as _source_display_name_impl,
)
from src.domain.notification.limits import WECHAT_IMAGE_MAX_BYTES
from src.application.notification.ports import (
    ImageRenderPort,
    NotificationSendPort,
    build_default_image_render_port,
    build_default_send_port,
)
from src.domain.notification.endpoints import (
    resolve_gotify_message_endpoint,
    resolve_ntfy_endpoint,
)

from src.application.reporting.analysis_report_renderer import AnalysisReportRenderer

logger = logging.getLogger(__name__)


# W5.6：数值/文本格式化、狙击点归一、阶段决策与策略综合区块、数据源显示名
# 等纯渲染助手已下沉 src.domain.notification.rendering；本文件只保留发送编排。

if TYPE_CHECKING:
    from src.application.analysis.analyzer import AnalysisResult


class NotificationChannel(Enum):
    """通知渠道类型"""
    WECHAT = "wechat"      # 企业微信
    DINGTALK = "dingtalk"
    FEISHU = "feishu"      # 飞书
    TELEGRAM = "telegram"  # Telegram
    EMAIL = "email"        # 邮件
    PUSHOVER = "pushover"  # Pushover（手机/桌面推送）
    NTFY = "ntfy"          # ntfy
    GOTIFY = "gotify"      # Gotify
    PUSHPLUS = "pushplus"  # PushPlus（国内推送服务）
    SERVERCHAN3 = "serverchan3"  # Server酱3（手机APP推送服务）
    CUSTOM = "custom"      # 自定义 Webhook
    DISCORD = "discord"    # Discord 机器人 (Bot)
    SLACK = "slack"        # Slack
    ASTRBOT = "astrbot"
    UNKNOWN = "unknown"    # 未知


@dataclass
class ChannelAttemptResult:
    """One static notification channel send attempt."""

    channel: str
    success: bool
    error_code: Optional[str] = None
    retryable: bool = False
    latency_ms: Optional[int] = None
    diagnostics: Optional[str] = None


@dataclass
class NotificationDispatchResult:
    """Structured result for notification dispatch diagnostics."""

    dispatched: bool
    success: bool
    status: str
    channel_results: List[ChannelAttemptResult] = field(default_factory=list)
    message: Optional[str] = None


class ChannelDetector:
    """
    渠道检测器 - 简化版

    根据配置直接判断渠道类型（不再需要 URL 解析）
    """

    @staticmethod
    def get_channel_name(channel: NotificationChannel) -> str:
        """获取渠道中文名称"""
        names = {
            NotificationChannel.WECHAT: "企业微信",
            NotificationChannel.FEISHU: "飞书",
            NotificationChannel.DINGTALK: "钉钉",
            NotificationChannel.TELEGRAM: "Telegram",
            NotificationChannel.EMAIL: "邮件",
            NotificationChannel.PUSHOVER: "Pushover",
            NotificationChannel.NTFY: "ntfy",
            NotificationChannel.GOTIFY: "Gotify",
            NotificationChannel.PUSHPLUS: "PushPlus",
            NotificationChannel.SERVERCHAN3: "Server酱3",
            NotificationChannel.CUSTOM: "自定义Webhook",
            NotificationChannel.DISCORD: "Discord机器人",
            NotificationChannel.SLACK: "Slack",
            NotificationChannel.ASTRBOT: "ASTRBOT机器人",
            NotificationChannel.UNKNOWN: "未知渠道",
        }
        return names.get(channel, "未知渠道")


class NotificationService:
    """
    通知服务

    职责：
    1. 生成 Markdown 格式的分析日报
    2. 向所有已配置的渠道推送消息（多渠道并发）
    3. 支持本地保存日报

    支持的渠道：
    - 企业微信 Webhook
    - 飞书 Webhook
    - Telegram Bot
    - 邮件 SMTP
    - Pushover（手机/桌面推送）

    注意：所有已配置的渠道都会收到推送

    R2-B3：不再继承 14 个 Sender，发送能力经 ``NotificationSendPort`` 组合注入
    （默认 ``InProcessNotificationSendPort``，D-02 落法 A）；对外方法面通过同名
    thin forwarder 保持不变。
    """

    def __init__(
        self,
        source_message: Optional[BotMessage] = None,
        send_port: Optional[NotificationSendPort] = None,
        image_render_port: Optional[ImageRenderPort] = None,
    ):
        """
        初始化通知服务

        检测所有已配置的渠道，推送时会向所有渠道发送
        """
        config = get_config()
        self._config = config
        self._source_message = source_message
        self._context_channels: List[str] = []

        # Markdown 转图片（Issue #289）
        self._markdown_to_image_channels = set(
            getattr(config, 'markdown_to_image_channels', []) or []
        )
        self._markdown_to_image_max_chars = getattr(
            config, 'markdown_to_image_max_chars', 15000
        )

        # 仅分析结果摘要（Issue #262）：true 时只推送汇总，不含个股详情
        self._report_summary_only = getattr(config, 'report_summary_only', False)
        self._report_show_llm_model = getattr(config, 'report_show_llm_model', True)
        self._history_compare_cache: Dict[Tuple[int, str, Tuple[Tuple[str, str], ...]], Dict[str, List[Dict[str, Any]]]] = {}

        # 初始化发送端口（R2-B3）：未显式注入时回退为经 bootstrap seam 注册的内置
        # 组合适配器（D-02 选项 A 的搬包后实现形态：application 不直接 import infra，
        # 改由 configure_notification_send_port() 在入口注册工厂）。未注册时优雅降级为
        # None，仅在实际发送时要求装配（与 SA2 configure_search “未注册降级为空”同型）。
        self._send_port: Optional[NotificationSendPort] = (
            send_port if send_port is not None else build_default_send_port(config)
        )
        # 初始化图片渲染端口（R3-S11）：未显式注入时回退为经 bootstrap seam 注册的
        # md2img 适配器（实现已下沉 src.infrastructure.reporting.img_render）。未注册时
        # 保持 None，发送侧按“转图不可用”回退为文本，不阻断主流程。
        self._image_render_port: Optional[ImageRenderPort] = (
            image_render_port
            if image_render_port is not None
            else build_default_image_render_port()
        )
        # 以下两个属性旧由 EmailSender / FeishuSender 的 __init__ 写入，去继承后直接从
        # config 取（与 sender 内原始取值逐字一致）。
        self._stock_email_groups = getattr(config, 'stock_email_groups', None) or []
        self._feishu_send_as_file = getattr(config, 'feishu_send_as_file', False)

        # 检测所有已配置的渠道
        self._available_channels = self._detect_all_channels()
        if self._extract_dingtalk_session_webhook() is not None:
            self._context_channels.append("钉钉会话")
        if self._extract_feishu_reply_info() is not None:
            self._context_channels.append("飞书会话")

        if not self._available_channels and not self._context_channels:
            logger.warning("未配置有效的通知渠道，将不发送推送通知")
        else:
            channel_names = [ChannelDetector.get_channel_name(ch) for ch in self._available_channels]
            channel_names.extend(self._context_channels)
            logger.info(f"已配置 {len(channel_names)} 个通知渠道：{', '.join(channel_names)}")

    # —— R2-B3 thin forwarders ——
    # 去继承后保留与旧 14 重继承版完全同名的方法面（含私有 _send_* 变体），
    # 以保住 src/application/analysis/pipeline.py、scripts/check_env.py 及 60 处 patch.object 的调用/替换锚点。
    # 统一 *args/**kwargs 透传，不重写签名，保证任意调用形状与 autospec 兼容。
    def send_to_wechat(self, *args: Any, **kwargs: Any) -> bool:
        """向企业微信推送消息。"""
        return self._send_port.send_wechat(*args, **kwargs)

    def send_to_dingtalk(self, *args: Any, **kwargs: Any) -> bool:
        """向钉钉推送消息。"""
        return self._send_port.send_dingtalk(*args, **kwargs)

    def send_to_feishu(self, *args: Any, **kwargs: Any) -> bool:
        """向飞书推送消息。"""
        return self._send_port.send_feishu(*args, **kwargs)

    def send_to_telegram(self, *args: Any, **kwargs: Any) -> bool:
        """向 Telegram 推送消息。"""
        return self._send_port.send_telegram(*args, **kwargs)

    def send_to_email(self, *args: Any, **kwargs: Any) -> bool:
        """向邮件渠道推送消息。"""
        return self._send_port.send_email(*args, **kwargs)

    def send_to_pushover(self, *args: Any, **kwargs: Any) -> bool:
        """向 Pushover 推送消息。"""
        return self._send_port.send_pushover(*args, **kwargs)

    def send_to_ntfy(self, *args: Any, **kwargs: Any) -> bool:
        """向 ntfy 推送消息。"""
        return self._send_port.send_ntfy(*args, **kwargs)

    def send_to_gotify(self, *args: Any, **kwargs: Any) -> bool:
        """向 Gotify 推送消息。"""
        return self._send_port.send_gotify(*args, **kwargs)

    def send_to_pushplus(self, *args: Any, **kwargs: Any) -> bool:
        """向 PushPlus 推送消息。"""
        return self._send_port.send_pushplus(*args, **kwargs)

    def send_to_serverchan3(self, *args: Any, **kwargs: Any) -> bool:
        """向 Server酱³ 推送消息。"""
        return self._send_port.send_serverchan3(*args, **kwargs)

    def send_to_custom(self, *args: Any, **kwargs: Any) -> bool:
        """向自定义渠道推送消息。"""
        return self._send_port.send_custom(*args, **kwargs)

    def send_to_discord(self, *args: Any, **kwargs: Any) -> bool:
        """向 Discord 推送消息。"""
        return self._send_port.send_discord(*args, **kwargs)

    def send_to_slack(self, *args: Any, **kwargs: Any) -> bool:
        """向 Slack 推送消息。"""
        return self._send_port.send_slack(*args, **kwargs)

    def send_to_astrbot(self, *args: Any, **kwargs: Any) -> bool:
        """向 AstrBot 推送消息。"""
        return self._send_port.send_astrbot(*args, **kwargs)

    def send_feishu_file(self, *args: Any, **kwargs: Any) -> bool:
        """向飞书发送文件。"""
        return self._send_port.send_feishu_file(*args, **kwargs)

    def get_all_email_receivers(self) -> Any:
        """返回全部邮件收件人。"""
        return self._send_port.all_email_receivers()

    def get_receivers_for_stocks(self, *args: Any, **kwargs: Any) -> Any:
        """返回指定股票对应的邮件收件人。"""
        return self._send_port.receivers_for_stocks(*args, **kwargs)

    def _send_wechat_image(self, *args: Any, **kwargs: Any) -> bool:
        """向企业微信发送图片。"""
        return self._send_port.send_wechat_image(*args, **kwargs)

    def _send_telegram_photo(self, *args: Any, **kwargs: Any) -> bool:
        """向 Telegram 发送图片。"""
        return self._send_port.send_telegram_photo(*args, **kwargs)

    def _send_email_with_inline_image(self, *args: Any, **kwargs: Any) -> bool:
        """发送内嵌图片的邮件。"""
        return self._send_port.send_email_with_inline_image(*args, **kwargs)

    def _send_custom_webhook_image(self, *args: Any, **kwargs: Any) -> bool:
        """通过自定义 Webhook 发送图片。"""
        return self._send_port.send_custom_webhook_image(*args, **kwargs)

    def _send_slack_image(self, *args: Any, **kwargs: Any) -> bool:
        """向 Slack 发送图片。"""
        return self._send_port.send_slack_image(*args, **kwargs)

    def _send_dingtalk_chunked(self, *args: Any, **kwargs: Any) -> bool:
        """分片发送钉钉消息。"""
        return self._send_port.send_dingtalk_chunked(*args, **kwargs)

    def _normalize_report_type(self, report_type: Any) -> ReportType:
        """Normalize string/enum input into ReportType."""
        if isinstance(report_type, ReportType):
            return report_type
        return ReportType.from_str(report_type)

    def _get_report_language(self, payload: Optional[Any] = None) -> str:
        """返回当前报告语言。"""
        return self._report_renderer().get_report_language(payload=payload)

    def _get_labels(self, payload: Optional[Any] = None) -> Dict[str, str]:
        """返回当前语言的报告标签。"""
        return get_report_labels(self._get_report_language(payload))

    def _get_display_name(self, result: AnalysisResult, language: Optional[str] = None) -> str:
        """返回股票展示名称。"""
        return self._report_renderer().get_display_name(result=result, language=language)

    def _get_history_compare_context(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """获取历史对比上下文。"""
        return self._report_renderer().get_history_compare_context(results=results)

    def generate_aggregate_report(
        self,
        results: List[AnalysisResult],
        report_type: Any,
        report_date: Optional[str] = None,
    ) -> str:
        """Generate the aggregate report content used by merge/save/push paths."""
        normalized_type = self._normalize_report_type(report_type)
        if normalized_type == ReportType.BRIEF:
            return self.generate_brief_report(results, report_date=report_date)
        return self.generate_dashboard_report(results, report_date=report_date)

    def _collect_models_used(self, results: List[AnalysisResult]) -> List[str]:
        """汇总报告使用的模型。"""
        return self._report_renderer().collect_models_used(results=results)

    def _public_phase_pack_excerpt(self, result: AnalysisResult, report_language: str) -> str:
        """返回对外阶段上下文包摘要。"""
        return self._report_renderer().public_phase_pack_excerpt(result=result, report_language=report_language)

    def _public_market_status_line(self, results: List[AnalysisResult], report_language: str) -> str:
        """返回对外大盘状态描述行。"""
        return self._report_renderer().public_market_status_line(results=results, report_language=report_language)

    def _append_market_status_line(
        self,
        lines: List[str],
        results: List[AnalysisResult],
        report_language: str,
    ) -> None:
        """追加大盘状态描述行。"""
        return self._report_renderer().append_market_status_line(lines=lines, results=results, report_language=report_language)

    def _should_show_llm_model(self) -> bool:
        """判断是否展示 LLM 模型。"""
        return self._report_renderer().should_show_llm_model()

    @staticmethod
    def detect_configured_channels(config: Config) -> List[NotificationChannel]:
        """
        Detect statically configured notification channels from Config.

        This intentionally mirrors sender availability without instantiating
        sender objects, so diagnostics and runtime use the same channel truth.
        Runtime-only context channels are handled by instance methods.
        """
        channels = []

        if getattr(config, "wechat_webhook_url", None):
            channels.append(NotificationChannel.WECHAT)
        if getattr(config, "dingtalk_webhook_url", None):
            channels.append(NotificationChannel.DINGTALK)

        if is_feishu_static_configured(config):
            channels.append(NotificationChannel.FEISHU)

        if (
            getattr(config, "telegram_bot_token", None)
            and getattr(config, "telegram_chat_id", None)
        ):
            channels.append(NotificationChannel.TELEGRAM)

        if getattr(config, "email_sender", None) and getattr(config, "email_password", None):
            channels.append(NotificationChannel.EMAIL)

        if (
            getattr(config, "pushover_user_key", None)
            and getattr(config, "pushover_api_token", None)
        ):
            channels.append(NotificationChannel.PUSHOVER)

        ntfy_server_url, ntfy_topic = resolve_ntfy_endpoint(getattr(config, "ntfy_url", None))
        if ntfy_server_url and ntfy_topic:
            channels.append(NotificationChannel.NTFY)

        gotify_endpoint = resolve_gotify_message_endpoint(getattr(config, "gotify_url", None))
        if gotify_endpoint and (getattr(config, "gotify_token", None) or "").strip():
            channels.append(NotificationChannel.GOTIFY)

        if getattr(config, "pushplus_token", None):
            channels.append(NotificationChannel.PUSHPLUS)

        if getattr(config, "serverchan3_sendkey", None):
            channels.append(NotificationChannel.SERVERCHAN3)

        if getattr(config, "custom_webhook_urls", None):
            channels.append(NotificationChannel.CUSTOM)

        if (
            getattr(config, "discord_webhook_url", None)
            or (
                getattr(config, "discord_bot_token", None)
                and getattr(config, "discord_main_channel_id", None)
            )
        ):
            channels.append(NotificationChannel.DISCORD)

        if (
            getattr(config, "slack_webhook_url", None)
            or (
                getattr(config, "slack_bot_token", None)
                and getattr(config, "slack_channel_id", None)
            )
        ):
            channels.append(NotificationChannel.SLACK)

        if getattr(config, "astrbot_url", None):
            channels.append(NotificationChannel.ASTRBOT)

        return channels

    def _detect_all_channels(self) -> List[NotificationChannel]:
        """
        检测所有已配置的渠道

        Returns:
            已配置的渠道列表
        """
        return self.detect_configured_channels(self._config)

    def is_available(self) -> bool:
        """检查通知服务是否可用（至少有一个渠道或上下文渠道）"""
        return len(self._available_channels) > 0 or self._has_context_channel()

    def get_available_channels(self) -> List[NotificationChannel]:
        """获取所有已配置的渠道"""
        return self._available_channels

    def get_channels_for_route(
        self,
        route_type: Optional[str],
        channels: Optional[List[NotificationChannel]] = None,
    ) -> List[NotificationChannel]:
        """Return channels allowed for a route type.

        ``route_type=None`` keeps the legacy behavior and returns all supplied
        static channels. Empty route config also keeps all supplied channels.
        Non-empty route config that matches no enabled channel returns an empty
        list.
        """
        target_channels = list(channels if channels is not None else self._available_channels)
        if route_type is None:
            return target_channels

        route_config = get_notification_route_config(route_type)
        if route_config is None:
            logger.warning("未知通知路由类型 %s，沿用全部已配置渠道", route_type)
            return target_channels

        configured_route_channels = getattr(self._config, route_config["config_attr"], []) or []
        if not configured_route_channels:
            return target_channels

        valid_channels, invalid_channels = split_notification_route_channels(configured_route_channels)
        if invalid_channels:
            logger.warning(
                "%s 包含未知通知渠道，将忽略: %s",
                route_config["env_key"],
                ", ".join(invalid_channels),
            )

        allowed = set(valid_channels)
        return [channel for channel in target_channels if channel.value in allowed]

    def get_channel_names(self) -> str:
        """获取所有已配置渠道的名称"""
        names = [ChannelDetector.get_channel_name(ch) for ch in self._available_channels]
        if self._has_context_channel():
            names.append("钉钉会话")
        return ', '.join(names)

    def evaluate_noise_control(
        self,
        content: str,
        *,
        route_type: Optional[str] = None,
        severity: Optional[str] = None,
        dedup_key: Optional[str] = None,
        cooldown_key: Optional[str] = None,
    ) -> NotificationNoiseDecision:
        """Evaluate static-channel notification noise controls."""
        return evaluate_notification_noise(
            self._config,
            content=content,
            route_type=route_type,
            severity=severity,
            dedup_key=dedup_key,
            cooldown_key=cooldown_key,
        )

    @staticmethod
    def record_noise_control(decision: NotificationNoiseDecision) -> None:
        """Record static-channel notification noise state after a successful send."""
        record_notification_noise(decision)

    @staticmethod
    def release_noise_control(decision: NotificationNoiseDecision) -> None:
        """Release static-channel in-flight noise reservation after send failure."""
        release_notification_noise(decision)

    # ===== Context channel =====
    def _has_context_channel(self) -> bool:
        """判断是否存在基于消息上下文的临时渠道（如钉钉会话、飞书会话）"""
        return (
            self._extract_dingtalk_session_webhook() is not None
            or self._extract_feishu_reply_info() is not None
            or self._extract_telegram_context_chat_id() is not None
        )

    def _source_platform(self) -> str:
        """Return normalized platform from the source bot message."""
        platform = getattr(self._source_message, "platform", "")
        if hasattr(platform, "value"):
            platform = platform.value
        return str(platform or "").lower()

    def _extract_telegram_context_chat_id(self) -> Optional[str]:
        """从来源消息中提取 Telegram 上下文 chat_id（用于异步回复）。"""
        if not isinstance(self._source_message, BotMessage):
            return None
        if self._source_platform() != "telegram":
            return None
        raw_data = getattr(self._source_message, "raw_data", {}) or {}
        for candidate in (
            getattr(self._source_message, "chat_id", ""),
            raw_data.get("chat_id"),
            raw_data.get("message", {}).get("chat", {}).get("id") if isinstance(raw_data.get("message"), dict) else None,
        ):
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
            if candidate is not None and not isinstance(candidate, str):
                candidate_text = str(candidate).strip()
                if candidate_text:
                    return candidate_text
        return None

    def should_broadcast_static_channels(self) -> bool:
        """Whether static notification channels should receive this dispatch."""
        return not self._has_context_channel()

    def _extract_dingtalk_session_webhook(self) -> Optional[str]:
        """从来源消息中提取钉钉会话 Webhook（用于 Stream 模式回复）"""
        if not isinstance(self._source_message, BotMessage):
            return None
        raw_data = getattr(self._source_message, "raw_data", {}) or {}
        if not isinstance(raw_data, dict):
            return None
        session_webhook = (
            raw_data.get("_session_webhook")
            or raw_data.get("sessionWebhook")
            or raw_data.get("session_webhook")
            or raw_data.get("session_webhook_url")
        )
        if not session_webhook and isinstance(raw_data.get("headers"), dict):
            session_webhook = raw_data["headers"].get("sessionWebhook")
        return session_webhook

    def _extract_feishu_reply_info(self) -> Optional[Dict[str, str]]:
        """
        从来源消息中提取飞书回复信息（用于 Stream 模式回复）

        Returns:
            包含 chat_id 的字典，或 None
        """
        if not isinstance(self._source_message, BotMessage):
            return None
        if getattr(self._source_message, "platform", "") != "feishu":
            return None
        chat_id = getattr(self._source_message, "chat_id", "")
        if not chat_id:
            return None
        return {"chat_id": chat_id}

    def send_to_context(self, content: str) -> bool:
        """
        向基于消息上下文的渠道发送消息（例如钉钉 Stream 会话）

        Args:
            content: Markdown 格式内容
        """
        return self._send_via_source_context(content)

    def _send_via_source_context(self, content: str) -> bool:
        """
        使用消息上下文（如钉钉/飞书会话）发送一份报告

        主要用于从机器人 Stream 模式触发的任务，确保结果能回到触发的会话。
        """
        success = False

        # 尝试钉钉会话
        session_webhook = self._extract_dingtalk_session_webhook()
        if session_webhook:
            try:
                if self._send_dingtalk_chunked(session_webhook, content, max_bytes=20000):
                    logger.info("已通过钉钉会话（Stream）推送报告")
                    success = True
                else:
                    logger.error("钉钉会话（Stream）推送失败")
            except Exception as e:
                logger.error(f"钉钉会话（Stream）推送异常: {e}")

        # 尝试飞书会话
        feishu_info = self._extract_feishu_reply_info()
        if feishu_info:
            try:
                if self._send_feishu_stream_reply(feishu_info["chat_id"], content):
                    logger.info("已通过飞书会话（Stream）推送报告")
                    success = True
                else:
                    logger.error("飞书会话（Stream）推送失败")
            except Exception as e:
                logger.error(f"飞书会话（Stream）推送异常: {e}")

        # 尝试 Telegram 会话上下文（按来源 chat_id 回执）
        telegram_chat_id = self._extract_telegram_context_chat_id()
        if telegram_chat_id:
            try:
                if self.send_to_telegram(content, chat_id=telegram_chat_id):
                    logger.info("已通过 Telegram 上下文会话推送报告")
                    success = True
                else:
                    logger.error("Telegram 上下文会话推送失败")
            except Exception as e:
                logger.error(f"Telegram 上下文会话推送异常: {e}")

        return success

    def _send_feishu_stream_reply(self, chat_id: str, content: str) -> bool:
        """
        通过飞书 Stream 模式发送消息到指定会话

        Args:
            chat_id: 飞书会话 ID
            content: 消息内容

        Returns:
            是否发送成功
        """
        # R2-B5：建 FeishuReplyClient + 分块 + 发送的具体实现下沉到组合适配器（infra），
        # application 只经端口调用，不再直接 import sender。保留本方法名与签名
        #（tests 以 patch.object 锚定此方法）。
        if self._send_port is None:
            logger.warning(
                "发送端口未装配，无法通过飞书 Stream 回复"
                "（需先 configure_notification_send_port）"
            )
            return False
        return self._send_port.send_stream_reply(chat_id, content)

    def _report_renderer(self) -> AnalysisReportRenderer:
        """返回报告渲染器实例。"""
        return AnalysisReportRenderer(
            config=getattr(self, "_config", None),
            show_llm_model=getattr(self, "_report_show_llm_model", True),
            summary_only=getattr(self, "_report_summary_only", False),
            history_compare_cache=getattr(self, "_history_compare_cache", {}),
            runtime_config_provider=get_config,
        )

    def generate_daily_report(
        self,
        results: List[AnalysisResult],
        report_date: Optional[str] = None
    ) -> str:
        """生成每日汇总报告。"""
        return self._report_renderer().generate_daily_report(results=results, report_date=report_date)

    _escape_md = staticmethod(AnalysisReportRenderer.escape_md)

    _clean_sniper_value = staticmethod(AnalysisReportRenderer.clean_sniper_value)

    @staticmethod
    def _phase_decision_list(value: Any) -> List[str]:
        """提取阶段决策列表。"""
        return _phase_decision_list_impl(value)

    @classmethod
    def _phase_decision_has_content(cls, phase_decision: Dict[str, Any]) -> bool:
        """判断阶段决策是否有内容。"""
        return _phase_decision_has_content_impl(phase_decision)

    def _append_phase_decision_block(
        self,
        report_lines: List[str],
        dashboard: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        """追加阶段决策段落。"""
        return self._report_renderer().append_phase_decision_block(report_lines=report_lines, dashboard=dashboard, labels=labels)

    def _get_display_operation_advice(
        self,
        result: AnalysisResult,
        report_language: Optional[str] = None,
    ) -> str:
        """返回展示用操作建议。"""
        return self._report_renderer().get_display_operation_advice(result=result, report_language=report_language)

    def _count_display_decisions(
        self,
        results: List[AnalysisResult],
        report_language: Optional[str] = None,
    ) -> Tuple[int, int, int]:
        """统计展示决策条目数。"""
        return self._report_renderer().count_display_decisions(results=results, report_language=report_language)

    def _get_signal_level(self, result: AnalysisResult) -> tuple:
        """返回信号级别。"""
        return self._report_renderer().get_signal_level(result=result)

    def generate_dashboard_report(
        self,
        results: List[AnalysisResult],
        report_date: Optional[str] = None
    ) -> str:
        """生成仪表盘报告。"""
        return self._report_renderer().generate_dashboard_report(results=results, report_date=report_date)

    def generate_wechat_dashboard(self, results: List[AnalysisResult]) -> str:
        """生成企业微信仪表盘内容。"""
        return self._report_renderer().generate_wechat_dashboard(results=results)

    def generate_wechat_summary(self, results: List[AnalysisResult]) -> str:
        """生成企业微信摘要内容。"""
        return self._report_renderer().generate_wechat_summary(results=results)

    def generate_brief_report(
        self,
        results: List[AnalysisResult],
        report_date: Optional[str] = None,
    ) -> str:
        """生成简报。"""
        return self._report_renderer().generate_brief_report(results=results, report_date=report_date)

    def generate_single_stock_report(self, result: AnalysisResult) -> str:
        """生成单只股票报告。"""
        return self._report_renderer().generate_single_stock_report(result=result)

    def _get_source_display_name(self, source: Any, language: Optional[str]) -> str:
        """返回数据来源展示名称。"""
        return self._report_renderer().get_source_display_name(source=source, language=language)

    def _append_market_snapshot(self, lines: List[str], result: AnalysisResult) -> None:
        """追加大盘快照段落。"""
        return self._report_renderer().append_market_snapshot(lines=lines, result=result)

    _format_amount_cn = staticmethod(AnalysisReportRenderer.format_amount_cn)

    _format_percent = staticmethod(AnalysisReportRenderer.format_percent)

    _format_per_share = staticmethod(AnalysisReportRenderer.format_per_share)

    _format_text = staticmethod(AnalysisReportRenderer.format_text)

    def _get_fundamental_blocks(self, result: AnalysisResult) -> Dict[str, Any]:
        """获取基本面信息块。"""
        return self._report_renderer().get_fundamental_blocks(result=result)

    def _append_fundamental_blocks(self, lines: List[str], result: AnalysisResult) -> None:
        """追加基本面信息块。"""
        return self._report_renderer().append_fundamental_blocks(lines=lines, result=result)

    def _append_financial_summary(
        self,
        lines: List[str],
        blocks: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        """追加财务摘要段落。"""
        return self._report_renderer().append_financial_summary(lines=lines, blocks=blocks, labels=labels)

    def _append_shareholder_return(
        self,
        lines: List[str],
        blocks: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        """追加股东回报段落。"""
        return self._report_renderer().append_shareholder_return(lines=lines, blocks=blocks, labels=labels)

    _format_net_shares = staticmethod(AnalysisReportRenderer.format_net_shares)

    def _append_institutional_flow(
        self,
        lines: List[str],
        blocks: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        """追加机构资金流向段落。"""
        return self._report_renderer().append_institutional_flow(lines=lines, blocks=blocks, labels=labels)

    def _append_related_boards(
        self,
        lines: List[str],
        blocks: Dict[str, Any],
        labels: Dict[str, str],
    ) -> None:
        """追加关联板块段落。"""
        return self._report_renderer().append_related_boards(lines=lines, blocks=blocks, labels=labels)

    # —— 公开图像路由面（R3-S15a）——
    # pipeline 等应用层用例不再直接访问 ``_markdown_to_image_*`` / ``_send_*_image``
    # 等私有成员；以下方法只做薄转发，私有名保留（60 处 ``patch.object`` 锚点不变）。
    def image_enabled_channels(self) -> set[str]:
        """返回配置为 Markdown 转图片的渠道值集合（副本，避免外部修改内部状态）。"""
        return set(self._markdown_to_image_channels)

    def image_max_chars(self) -> int:
        """返回 Markdown 转图片的字符上限。"""
        return int(self._markdown_to_image_max_chars)

    def should_use_image_for_channel(
        self, channel: NotificationChannel, image_bytes: Optional[bytes]
    ) -> bool:
        """判断该渠道本次是否应发送图片（内部仍走原私有判定）。"""
        return self._should_use_image_for_channel(channel, image_bytes)

    def send_channel_image(
        self,
        channel: NotificationChannel,
        image_bytes: bytes,
        *,
        fallback_content: Optional[str] = None,
        receivers: Optional[List[str]] = None,
    ) -> bool:
        """按渠道分发图片发送；不支持图片的渠道返回 False。"""
        if channel == NotificationChannel.WECHAT:
            return self._send_wechat_image(image_bytes)
        if channel == NotificationChannel.TELEGRAM:
            return self._send_telegram_photo(image_bytes)
        if channel == NotificationChannel.EMAIL:
            if receivers is None:
                return self._send_email_with_inline_image(image_bytes)
            return self._send_email_with_inline_image(image_bytes, receivers=receivers)
        if channel == NotificationChannel.CUSTOM:
            return self._send_custom_webhook_image(
                image_bytes, fallback_content=fallback_content
            )
        if channel == NotificationChannel.SLACK:
            return self._send_slack_image(
                image_bytes, fallback_content=fallback_content
            )
        logger.warning("渠道 %s 不支持图片发送", channel)
        return False

    def slack_image_target(self) -> Optional[Tuple[str, str]]:
        """返回 Slack 图片发送所需的 (bot_token, channel_id)；未配置返回 None。"""
        token = getattr(self._config, "slack_bot_token", None)
        channel_id = getattr(self._config, "slack_channel_id", None)
        if token and channel_id:
            return str(token), str(channel_id)
        return None

    def _should_use_image_for_channel(
        self, channel: NotificationChannel, image_bytes: Optional[bytes]
    ) -> bool:
        """
        Decide whether to send as image for the given channel (Issue #289).

        Fallback rules (send as Markdown text instead of image):
        - image_bytes is None: conversion failed / imgkit not installed / content over max_chars
        - WeChat: image exceeds ~2MB limit
        """
        if channel.value not in self._markdown_to_image_channels or image_bytes is None:
            return False
        if channel == NotificationChannel.WECHAT and len(image_bytes) > WECHAT_IMAGE_MAX_BYTES:
            logger.warning(
                "企业微信图片超限 (%d bytes)，回退为 Markdown 文本发送",
                len(image_bytes),
            )
            return False
        return True

    @staticmethod
    def _sanitize_notification_diagnostics(text: Any) -> str:
        """清洗通知诊断信息。"""
        return sanitize_diagnostic_text(text)

    def _send_to_static_channel(
        self,
        channel: NotificationChannel,
        content: str,
        *,
        image_bytes: Optional[bytes],
        email_stock_codes: Optional[List[str]],
        email_send_to_all: bool,
        route_type: Optional[str] = None,
    ) -> bool:
        """向静态配置渠道发送消息。"""
        use_image = self._should_use_image_for_channel(channel, image_bytes)
        if channel == NotificationChannel.WECHAT:
            if use_image:
                return self._send_wechat_image(image_bytes)
            return self.send_to_wechat(content)
        if channel == NotificationChannel.FEISHU:
            if getattr(self, "_feishu_send_as_file", False) and route_type == "report":
                date_str = datetime.now().strftime('%Y%m%d')
                filepath = self.save_report_to_file(
                    content, filename=f"report_{date_str}.md"
                )
                return self.send_feishu_file(filepath)
            return self.send_to_feishu(content)
        if channel == NotificationChannel.DINGTALK:
            return self.send_to_dingtalk(content)
        if channel == NotificationChannel.TELEGRAM:
            if use_image:
                return self._send_telegram_photo(image_bytes)
            return self.send_to_telegram(content)
        if channel == NotificationChannel.EMAIL:
            receivers = None
            if email_send_to_all and self._stock_email_groups:
                receivers = self.get_all_email_receivers()
            elif email_stock_codes and self._stock_email_groups:
                receivers = self.get_receivers_for_stocks(email_stock_codes)
            if use_image:
                return self._send_email_with_inline_image(image_bytes, receivers=receivers)
            return self.send_to_email(content, receivers=receivers)
        if channel == NotificationChannel.PUSHOVER:
            return self.send_to_pushover(content)
        if channel == NotificationChannel.NTFY:
            return self.send_to_ntfy(content)
        if channel == NotificationChannel.GOTIFY:
            return self.send_to_gotify(content)
        if channel == NotificationChannel.PUSHPLUS:
            return self.send_to_pushplus(content)
        if channel == NotificationChannel.SERVERCHAN3:
            return self.send_to_serverchan3(content)
        if channel == NotificationChannel.CUSTOM:
            if use_image:
                return self._send_custom_webhook_image(image_bytes, fallback_content=content)
            return self.send_to_custom(content)
        if channel == NotificationChannel.DISCORD:
            return self.send_to_discord(content)
        if channel == NotificationChannel.SLACK:
            if use_image:
                return self._send_slack_image(image_bytes, fallback_content=content)
            return self.send_to_slack(content)
        if channel == NotificationChannel.ASTRBOT:
            return self.send_to_astrbot(content)
        logger.warning(f"不支持的通知渠道: {channel}")
        return False

    def send_with_results(
        self,
        content: str,
        email_stock_codes: Optional[List[str]] = None,
        email_send_to_all: bool = False,
        route_type: Optional[str] = None,
        severity: Optional[str] = None,
        dedup_key: Optional[str] = None,
        cooldown_key: Optional[str] = None,
    ) -> NotificationDispatchResult:
        """
        Send a notification and return per-channel diagnostics.

        ``send()`` keeps the historical bool API and delegates here.

        Fallback rules (Markdown-to-image, Issue #289):
        - When image_bytes is None (conversion failed / imgkit not installed /
          content over max_chars): all channels configured for image will send
          as Markdown text instead.
        - When WeChat image exceeds ~2MB: that channel falls back to Markdown text.

        Args:
            content: 消息内容（Markdown 格式）
            email_stock_codes: 股票代码列表（可选，用于邮件渠道路由到对应分组邮箱，Issue #268）
            email_send_to_all: 邮件是否发往所有配置邮箱（用于大盘复盘等无股票归属的内容）
            route_type: 通知路由类型；None 保持旧行为，report/alert/system_error 按配置过滤静态渠道
            severity: 通知严重级别；未设置时按路由类型推断
            dedup_key: 可选稳定去重 key；未设置时使用内容 hash
            cooldown_key: 可选冷却 key；未设置时使用路由/级别默认 key

        Returns:
            Structured dispatch diagnostics.
        """
        context_success = self.send_to_context(content)
        if not self.should_broadcast_static_channels():
            if context_success:
                logger.info("已通过上下文会话完成推送，跳过静态通知渠道")
                return NotificationDispatchResult(
                    dispatched=True,
                    success=True,
                    status="sent",
                    channel_results=[ChannelAttemptResult(channel="__context__", success=True)],
                )
            logger.warning("交互式上下文推送失败，已跳过静态通知渠道")
            return NotificationDispatchResult(
                dispatched=True,
                success=False,
                status="all_failed",
                channel_results=[
                    ChannelAttemptResult(
                        channel="__context__",
                        success=False,
                        error_code="send_failed",
                        retryable=True,
                    )
                ],
                message="interactive context delivery failed; static channels skipped",
            )

        if not self._available_channels:
            if context_success:
                logger.info("已通过消息上下文渠道完成推送（无其他通知渠道）")
                return NotificationDispatchResult(
                    dispatched=True,
                    success=True,
                    status="sent",
                    channel_results=[ChannelAttemptResult(channel="__context__", success=True)],
                )
            logger.warning("通知服务不可用，跳过推送")
            return NotificationDispatchResult(
                dispatched=False,
                success=False,
                status="no_channel",
                message="notification service unavailable",
            )

        target_channels = self.get_channels_for_route(route_type)
        if not target_channels:
            if context_success:
                logger.info("已通过消息上下文渠道完成推送（路由后无其他通知渠道）")
                return NotificationDispatchResult(
                    dispatched=True,
                    success=True,
                    status="sent",
                    channel_results=[ChannelAttemptResult(channel="__context__", success=True)],
                )
            logger.warning("通知路由 %s 未命中任何已配置渠道，跳过静态通知渠道", route_type)
            return NotificationDispatchResult(
                dispatched=False,
                success=False,
                status="no_channel",
                message=f"notification route {route_type} has no configured channel",
            )

        noise_decision = self.evaluate_noise_control(
            content,
            route_type=route_type,
            severity=severity,
            dedup_key=dedup_key,
            cooldown_key=cooldown_key,
        )
        if not noise_decision.should_send:
            logger.info(noise_decision.message)
            status = "sent" if context_success else "noise_suppressed"
            results = [ChannelAttemptResult(channel="__context__", success=True)] if context_success else []
            return NotificationDispatchResult(
                dispatched=bool(context_success),
                success=bool(context_success),
                status=status,
                channel_results=results,
                message=noise_decision.message,
            )

        # Markdown to image (Issue #289): convert once if any channel needs it.
        # Per-channel decision via _should_use_image_for_channel (see send() docstring for fallback rules).
        image_bytes = None
        channels_needing_image = {
            ch for ch in target_channels
            if ch.value in self._markdown_to_image_channels
            and ch not in {NotificationChannel.NTFY, NotificationChannel.GOTIFY}
        }
        if channels_needing_image:
            if self._image_render_port is not None:
                image_bytes = self._image_render_port.markdown_to_image(
                    content, max_chars=self._markdown_to_image_max_chars
                )
            if image_bytes:
                logger.info("Markdown 已转换为图片，将向 %s 发送图片",
                            [ch.value for ch in channels_needing_image])
            elif channels_needing_image:
                try:
                    from src.config import get_config
                    engine = getattr(get_config(), "md2img_engine", "wkhtmltoimage")
                except Exception:
                    engine = "wkhtmltoimage"
                hint = (
                    "npm i -g markdown-to-file" if engine == "markdown-to-file"
                    else "wkhtmltopdf (apt install wkhtmltopdf / brew install wkhtmltopdf)"
                )
                logger.warning(
                    "Markdown 转图片失败，将回退为文本发送。请检查 MARKDOWN_TO_IMAGE_CHANNELS 配置并安装 %s",
                    hint,
                )

        channel_names = ', '.join(ChannelDetector.get_channel_name(ch) for ch in target_channels)
        logger.info(f"正在向 {len(target_channels)} 个渠道发送通知：{channel_names}")

        success_count = 0
        fail_count = 0
        channel_results: List[ChannelAttemptResult] = []

        for channel in target_channels:
            channel_name = ChannelDetector.get_channel_name(channel)
            started_at = time.monotonic()
            try:
                result = self._send_to_static_channel(
                    channel,
                    content,
                    image_bytes=image_bytes,
                    email_stock_codes=email_stock_codes,
                    email_send_to_all=email_send_to_all,
                    route_type=route_type,
                )
                latency_ms = int((time.monotonic() - started_at) * 1000)

                if result:
                    success_count += 1
                else:
                    fail_count += 1
                channel_results.append(
                    ChannelAttemptResult(
                        channel=channel.value,
                        success=bool(result),
                        error_code=None if result else "send_failed",
                        retryable=not bool(result),
                        latency_ms=latency_ms,
                    )
                )

            except Exception as e:
                logger.error(f"{channel_name} 发送失败: {e}")
                fail_count += 1
                channel_results.append(
                    ChannelAttemptResult(
                        channel=channel.value,
                        success=False,
                        error_code="exception",
                        retryable=True,
                        latency_ms=int((time.monotonic() - started_at) * 1000),
                        diagnostics=self._sanitize_notification_diagnostics(str(e)),
                    )
                )

        logger.info(f"通知发送完成：成功 {success_count} 个，失败 {fail_count} 个")
        if success_count > 0:
            self.record_noise_control(noise_decision)
        else:
            self.release_noise_control(noise_decision)
        success = success_count > 0 or context_success
        if success_count > 0 and fail_count > 0:
            status = "partial_failed"
        elif success_count > 0 or context_success:
            status = "sent"
        else:
            status = "all_failed"
        if context_success:
            channel_results.insert(0, ChannelAttemptResult(channel="__context__", success=True))
        return NotificationDispatchResult(
            dispatched=True,
            success=success,
            status=status,
            channel_results=channel_results,
        )

    def send(
        self,
        content: str,
        email_stock_codes: Optional[List[str]] = None,
        email_send_to_all: bool = False,
        route_type: Optional[str] = None,
        severity: Optional[str] = None,
        dedup_key: Optional[str] = None,
        cooldown_key: Optional[str] = None,
    ) -> bool:
        """
        统一发送接口 - 向所有已配置的渠道发送。

        Returns:
            是否至少有一个渠道发送成功
        """
        result = self.send_with_results(
            content,
            email_stock_codes=email_stock_codes,
            email_send_to_all=email_send_to_all,
            route_type=route_type,
            severity=severity,
            dedup_key=dedup_key,
            cooldown_key=cooldown_key,
        )
        return bool(result.success)

    def save_report_to_file(
        self,
        content: str,
        filename: Optional[str] = None
    ) -> str:
        """
        保存日报到本地文件

        Args:
            content: 日报内容
            filename: 文件名（可选，默认按日期生成）

        Returns:
            保存的文件路径
        """
        from pathlib import Path

        if filename is None:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"report_{date_str}.md"

        # 确保 reports 目录存在（使用项目根目录下的 reports）
        # src/application/notification/ 下上溯 3 级到仓库根（搬包时随文件深度同步调整，
        # 与 application/reporting/report_renderer.py 的 REPO_ROOT 惯例一致）。
        reports_dir = Path(__file__).resolve().parents[3] / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)

        filepath = reports_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"日报已保存到: {filepath}")
        return str(filepath)

    def save_and_send_feishu_file(
        self,
        content: str,
        filename: Optional[str] = None,
    ) -> bool:
        """
        Save report content to a local markdown file and upload it to Feishu.

        This is a convenience wrapper around :meth:`save_report_to_file` +
        :meth:`send_feishu_file`.

        Args:
            content: Report content (Markdown).
            filename: Optional file name; auto-generated from date when omitted.

        Returns:
            Whether the Feishu file upload succeeded.
        """
        filepath = self.save_report_to_file(content, filename=filename)
        logger.info("将上传文件到飞书: %s", filepath)
        return self.send_feishu_file(filepath)


class NotificationBuilder:
    """
    通知消息构建器

    提供便捷的消息构建方法
    """

    @staticmethod
    def build_simple_alert(
        title: str,
        content: str,
        alert_type: str = "info"
    ) -> str:
        """
        构建简单的提醒消息

        Args:
            title: 标题
            content: 内容
            alert_type: 类型（info, warning, error, success）
        """
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }
        emoji = emoji_map.get(alert_type, "📢")

        return f"{emoji} **{title}**\n\n{content}"

    @staticmethod
    def build_stock_summary(results: List[AnalysisResult]) -> str:
        """
        构建股票摘要（简短版）

        适用于快速通知
        """
        report_language = normalize_report_language(
            next((getattr(result, "report_language", None) for result in results if getattr(result, "report_language", None)), None)
        )
        labels = get_report_labels(report_language)
        lines = [f"📊 **{labels['summary_heading']}**", ""]

        for r in sorted(results, key=lambda x: x.sentiment_score, reverse=True):
            display_action = display_action_fields_for_result(
                r,
                report_language=report_language,
            )["action"]
            signal_action = {
                "buy": "buy",
                "add": "buy",
                "hold": "hold",
                "reduce": "reduce",
                "sell": "sell",
                "watch": "watch",
                "avoid": "hold",
                "alert": "sell",
            }.get(display_action)
            display_advice = display_operation_advice_for_result(
                r,
                report_language=report_language,
            )
            signal_text, emoji, _ = get_signal_level(
                signal_action or display_advice,
                r.sentiment_score,
                report_language,
            )
            name = get_localized_stock_name(r.name, r.code, report_language)
            lines.append(
                f"{emoji} {name}({r.code}): {display_advice} | "
                f"{labels['score_label']} {r.sentiment_score}"
            )

        return "\n".join(lines)


# 便捷函数
def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    return NotificationService()


def send_daily_report(results: List[AnalysisResult]) -> bool:
    """
    发送每日报告的快捷方式

    自动识别渠道并推送
    """
    service = get_notification_service()

    # 生成报告
    report = service.generate_daily_report(results)

    # 保存到本地
    service.save_report_to_file(report)

    # 推送到配置的渠道（自动识别）
    return service.send(report)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    from src.application.analysis.analyzer import AnalysisResult

    # 模拟分析结果
    test_results = [
        AnalysisResult(
            code='600519',
            name='贵州茅台',
            sentiment_score=75,
            trend_prediction='看多',
            analysis_summary='技术面强势，消息面利好',
            operation_advice='买入',
            technical_analysis='放量突破 MA20，MACD 金叉',
            news_summary='公司发布分红公告，业绩超预期',
        ),
        AnalysisResult(
            code='000001',
            name='平安银行',
            sentiment_score=45,
            trend_prediction='震荡',
            analysis_summary='横盘整理，等待方向',
            operation_advice='持有',
            technical_analysis='均线粘合，成交量萎缩',
            news_summary='近期无重大消息',
        ),
        AnalysisResult(
            code='300750',
            name='宁德时代',
            sentiment_score=35,
            trend_prediction='看空',
            analysis_summary='技术面走弱，注意风险',
            operation_advice='卖出',
            technical_analysis='跌破 MA10 支撑，量能不足',
            news_summary='行业竞争加剧，毛利率承压',
        ),
    ]

    service = NotificationService()

    # 显示检测到的渠道
    print("=== 通知渠道检测 ===")
    print(f"当前渠道: {service.get_channel_names()}")
    print(f"渠道列表: {service.get_available_channels()}")
    print(f"服务可用: {service.is_available()}")

    # 生成日报
    print("\n=== 生成日报测试 ===")
    report = service.generate_daily_report(test_results)
    print(report)

    # 保存到文件
    print("\n=== 保存日报 ===")
    filepath = service.save_report_to_file(report)
    print(f"保存成功: {filepath}")

    # 推送测试
    if service.is_available():
        print(f"\n=== 推送测试（{service.get_channel_names()}）===")
        success = service.send(report)
        print(f"推送结果: {'成功' if success else '失败'}")
    else:
        print("\n通知渠道未配置，跳过推送测试")
