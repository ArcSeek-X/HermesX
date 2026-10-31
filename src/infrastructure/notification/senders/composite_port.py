"""通知发送端口的内置组合适配器（R2-B3）。

``NotificationService`` 去继承后不再 ``is-a`` 任何 Sender；本适配器**组合** 14 个 Sender
实例，把 ``src/application/notification/ports.py::NotificationSendPort`` 的每个方法转发到
对应 Sender 的真实实现，行为与旧的 14 重继承版本逐字等价。

为什么落在 ``src/infrastructure/notification/senders/`` 而不是 application 层：
- 端口协议 ``NotificationSendPort`` 属于 application（用例契约）；具体适配器知道各 Sender、
  并需转调若干 Sender 的 ``_send_*`` 私有实现。``scripts/check_architecture.py`` 对
  ``src/application/`` 开启 ``forbid_private_members``，跨对象访问私有方法会命中守卫；
  且 application 禁入 ``src.infrastructure``。因此具体适配器与 Sender 同侧（本包，R2-B5
  已随 Sender 从顶层 ``src/notification_sender/`` 物理下沉到 ``src/infrastructure/notification/``）。
- application 不直接 import 本适配器：默认端口经 ``src/bootstrap/notification.py`` 的 seam
  在进程入口注册（``set_notification_send_port_factory``），application 只依赖端口协议。

设计要点：
- 采用 ``*args / **kwargs`` 透传，不重写各 Sender 的签名细节，避免签名漂移破坏调用兼容
  （``src/application/analysis/pipeline.py``、测试 autospec、按关键字传参的调用点均保持原样可用）。
- D-02 落法 A（R2-B5 细化为 seam 注入）：``NotificationService`` 未显式注入端口时，默认经
  ``build_default_send_port(config)`` 回退到本适配器（工厂由入口注册），而非 fail-fast，
  以保住全仓零参 ``NotificationService()`` 构造；测试进程在 ``tests/conftest.py`` 会话级注册，
  与生产入口（main.py / app_lifespan）等价。

注：``send_dingtalk_chunked`` 的真实实现位于包内共享模块 ``dingtalk_post.send_dingtalk_markdown_chunked``
（R2-Q9 归属下沉：从 ``CustomWebhookSender._send_dingtalk_chunked`` 抽为中立共享函数），
此处注入 custom webhook 的 post 原语转调，不再伸手调用 sender 私有方法。
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import Config
from src.infrastructure.notification.senders.astrbot_sender import AstrbotSender
from src.infrastructure.notification.senders.custom_webhook_sender import CustomWebhookSender
from src.infrastructure.notification.senders.dingtalk_post import send_dingtalk_markdown_chunked
from src.infrastructure.notification.senders.dingtalk_sender import DingtalkSender
from src.infrastructure.notification.senders.discord_sender import DiscordSender
from src.infrastructure.notification.senders.email_sender import EmailSender
from src.infrastructure.notification.senders.feishu_sender import FeishuSender
from src.infrastructure.notification.senders.gotify_sender import GotifySender
from src.infrastructure.notification.senders.ntfy_sender import NtfySender
from src.infrastructure.notification.senders.pushover_sender import PushoverSender
from src.infrastructure.notification.senders.pushplus_sender import PushplusSender
from src.infrastructure.notification.senders.serverchan3_sender import Serverchan3Sender
from src.infrastructure.notification.senders.slack_sender import SlackSender
from src.infrastructure.notification.senders.telegram_sender import TelegramSender
from src.infrastructure.notification.senders.wechat_sender import WechatSender

logger = logging.getLogger(__name__)


class InProcessNotificationSendPort:
    """组合 14 个 Sender 的默认发送端口实现。"""

    def __init__(self, config: Config) -> None:
        self._wechat = WechatSender(config)
        self._dingtalk = DingtalkSender(config)
        self._feishu = FeishuSender(config)
        self._telegram = TelegramSender(config)
        self._email = EmailSender(config)
        self._pushover = PushoverSender(config)
        self._ntfy = NtfySender(config)
        self._gotify = GotifySender(config)
        self._pushplus = PushplusSender(config)
        self._serverchan3 = Serverchan3Sender(config)
        self._custom = CustomWebhookSender(config)
        self._discord = DiscordSender(config)
        self._slack = SlackSender(config)
        self._astrbot = AstrbotSender(config)

    # —— 静态渠道派发 ——
    def send_wechat(self, *args: Any, **kwargs: Any) -> bool:
        return self._wechat.send_to_wechat(*args, **kwargs)

    def send_dingtalk(self, *args: Any, **kwargs: Any) -> bool:
        return self._dingtalk.send_to_dingtalk(*args, **kwargs)

    def send_feishu(self, *args: Any, **kwargs: Any) -> bool:
        return self._feishu.send_to_feishu(*args, **kwargs)

    def send_telegram(self, *args: Any, **kwargs: Any) -> bool:
        return self._telegram.send_to_telegram(*args, **kwargs)

    def send_email(self, *args: Any, **kwargs: Any) -> bool:
        return self._email.send_to_email(*args, **kwargs)

    def send_pushover(self, *args: Any, **kwargs: Any) -> bool:
        return self._pushover.send_to_pushover(*args, **kwargs)

    def send_ntfy(self, *args: Any, **kwargs: Any) -> bool:
        return self._ntfy.send_to_ntfy(*args, **kwargs)

    def send_gotify(self, *args: Any, **kwargs: Any) -> bool:
        return self._gotify.send_to_gotify(*args, **kwargs)

    def send_pushplus(self, *args: Any, **kwargs: Any) -> bool:
        return self._pushplus.send_to_pushplus(*args, **kwargs)

    def send_serverchan3(self, *args: Any, **kwargs: Any) -> bool:
        return self._serverchan3.send_to_serverchan3(*args, **kwargs)

    def send_custom(self, *args: Any, **kwargs: Any) -> bool:
        return self._custom.send_to_custom(*args, **kwargs)

    def send_discord(self, *args: Any, **kwargs: Any) -> bool:
        return self._discord.send_to_discord(*args, **kwargs)

    def send_slack(self, *args: Any, **kwargs: Any) -> bool:
        return self._slack.send_to_slack(*args, **kwargs)

    def send_astrbot(self, *args: Any, **kwargs: Any) -> bool:
        return self._astrbot.send_to_astrbot(*args, **kwargs)

    # —— 图片 / 文件变体 ——
    def send_wechat_image(self, *args: Any, **kwargs: Any) -> bool:
        return self._wechat._send_wechat_image(*args, **kwargs)

    def send_telegram_photo(self, *args: Any, **kwargs: Any) -> bool:
        return self._telegram._send_telegram_photo(*args, **kwargs)

    def send_email_with_inline_image(self, *args: Any, **kwargs: Any) -> bool:
        return self._email._send_email_with_inline_image(*args, **kwargs)

    def send_custom_webhook_image(self, *args: Any, **kwargs: Any) -> bool:
        return self._custom._send_custom_webhook_image(*args, **kwargs)

    def send_slack_image(self, *args: Any, **kwargs: Any) -> bool:
        return self._slack._send_slack_image(*args, **kwargs)

    def send_feishu_file(self, *args: Any, **kwargs: Any) -> bool:
        return self._feishu.send_feishu_file(*args, **kwargs)

    def send_dingtalk_chunked(self, url: str, content: str, max_bytes: int = 20000) -> bool:
        return send_dingtalk_markdown_chunked(
            url, content, max_bytes, poster=self._custom._post_custom_webhook
        )

    # —— 飞书 Stream 会话回执（R2-B5：从 application 逐字搬入，sender 构造/分块不外泄）——
    def send_stream_reply(self, chat_id: str, content: str) -> bool:
        """通过飞书 Stream 模式回复到指定会话。

        实现与旧的 ``NotificationService._send_feishu_stream_reply`` 逐字等价：建
        ``FeishuReplyClient``、按 ``feishu_max_bytes`` 判定、超长走本地按段落/分隔的
        分块发送。application 层搬包后不再直接 import sender，改经端口调用本方法。
        """
        try:
            from src.infrastructure.notification.senders.feishu_reply_client import (
                FeishuReplyClient,
                FEISHU_SDK_AVAILABLE,
            )
            if not FEISHU_SDK_AVAILABLE:
                logger.warning("飞书 SDK 不可用，无法发送 Stream 回复")
                return False

            from src.config import get_config
            config = get_config()

            app_id = getattr(config, 'feishu_app_id', None)
            app_secret = getattr(config, 'feishu_app_secret', None)

            if not app_id or not app_secret:
                logger.warning("飞书 APP_ID 或 APP_SECRET 未配置")
                return False

            # 创建回复客户端
            reply_client = FeishuReplyClient(app_id, app_secret)

            # 飞书文本消息有长度限制，需要分批发送
            max_bytes = getattr(config, 'feishu_max_bytes', 20000)
            content_bytes = len(content.encode('utf-8'))

            if content_bytes > max_bytes:
                return self._send_feishu_stream_chunked(reply_client, chat_id, content, max_bytes)

            return reply_client.send_to_chat(chat_id, content)

        except ImportError as e:
            logger.error(f"导入飞书 Stream 模块失败: {e}")
            return False
        except Exception as e:
            logger.error(f"飞书 Stream 回复异常: {e}")
            return False

    def _send_feishu_stream_chunked(
        self,
        reply_client,
        chat_id: str,
        content: str,
        max_bytes: int
    ) -> bool:
        """分批发送长消息到飞书（Stream 模式），按段落/分隔线/行切分。"""
        import time

        def get_bytes(s: str) -> int:
            return len(s.encode('utf-8'))

        # 按段落或分隔线分割
        if "\n---\n" in content:
            sections = content.split("\n---\n")
            separator = "\n---\n"
        elif "\n### " in content:
            parts = content.split("\n### ")
            sections = [parts[0]] + [f"### {p}" for p in parts[1:]]
            separator = "\n"
        else:
            # 按行分割
            sections = content.split("\n")
            separator = "\n"

        chunks = []
        current_chunk = []
        current_bytes = 0
        separator_bytes = get_bytes(separator)

        for section in sections:
            section_bytes = get_bytes(section) + separator_bytes

            if current_bytes + section_bytes > max_bytes:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                current_chunk = [section]
                current_bytes = section_bytes
            else:
                current_chunk.append(section)
                current_bytes += section_bytes

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        # 发送每个分块
        success = True
        for i, chunk in enumerate(chunks):
            if i > 0:
                time.sleep(0.5)  # 避免请求过快

            if not reply_client.send_to_chat(chat_id, chunk):
                success = False
                logger.error(f"飞书 Stream 分块 {i+1}/{len(chunks)} 发送失败")

        return success

    # —— 邮件收件人解析 ——
    def all_email_receivers(self) -> Any:
        return self._email.get_all_email_receivers()

    def receivers_for_stocks(self, *args: Any, **kwargs: Any) -> Any:
        return self._email.get_receivers_for_stocks(*args, **kwargs)
