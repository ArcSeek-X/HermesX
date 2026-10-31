# -*- coding: utf-8 -*-
"""
===================================
飞书 App Bot 回复客户端
===================================

统一封装「向指定会话发送交互卡片」的飞书 SDK 客户端，被两类代码共同消费：

- 通知实现：``src/notification.py`` 把报告回执到消息来源会话；
- 机器人驱动：``bot/platforms/feishu_stream.py`` 回复用户命令。

客户端因此不能留在 ``bot/``：那会让通知实现反向依赖驱动层。放在
``src/infrastructure/notification/senders/`` 是因为同包已承担飞书 App Bot 发送能力，
后续通知适配整体下沉 ``src/infrastructure/notification/`` 时一并归位。

日志前缀沿用 ``[Feishu Stream]``，保持既有排障检索习惯。
"""

import json
import logging
import time
from typing import Callable, Optional

from src.config import get_config
from src.domain.shared.text_chunking import chunk_content_by_max_bytes
from src.infrastructure.reporting.markdown_render import format_feishu_markdown

logger = logging.getLogger(__name__)

# 尝试导入飞书 SDK
try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        ReplyMessageRequest,
        ReplyMessageRequestBody,
        CreateMessageRequest,
        CreateMessageRequestBody,
    )

    FEISHU_SDK_AVAILABLE = True
except ImportError:
    FEISHU_SDK_AVAILABLE = False
    logger.warning("[Feishu Stream] lark-oapi SDK 未安装，Stream 模式不可用")
    logger.warning("[Feishu Stream] 请运行: pip install lark-oapi")


class FeishuReplyClient:
    """
    飞书消息回复客户端

    使用飞书 API 发送回复消息。
    """

    def __init__(self, app_id: str, app_secret: str):
        """
        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
        """
        if not FEISHU_SDK_AVAILABLE:
            raise ImportError("lark-oapi SDK 未安装")

        self._client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.WARNING) \
            .build()

        # 获取配置的最大字节数
        config = get_config()
        self._max_bytes = getattr(config, 'feishu_max_bytes', 20000)

    def _send_interactive_card(self, content: str, message_id: Optional[str] = None,
                               chat_id: Optional[str] = None,
                               receive_id_type: str = "chat_id",
                               at_user: bool = False, user_id: Optional[str] = None) -> bool:
        """
        发送交互卡片消息（支持 Markdown 渲染）

        Args:
            content: Markdown 格式的内容
            message_id: 原消息 ID（回复时使用）
            chat_id: 会话 ID（主动发送时使用）
            receive_id_type: 接收者 ID 类型
            at_user: 是否 @用户
            user_id: 用户 open_id（at_user=True 时需要）

        Returns:
            是否发送成功
        """
        try:
            # 如果需要 @用户，在内容前添加 @ 标记
            final_content = content
            if at_user and user_id:
                final_content = f"<at user_id=\"{user_id}\"></at> {content}"

            # 构建交互卡片 payload
            card_data = {
                "config": {"wide_screen_mode": True},
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": final_content
                        }
                    }
                ]
            }

            content_json = json.dumps(card_data)

            if message_id:
                # 回复消息
                request = ReplyMessageRequest.builder() \
                    .message_id(message_id) \
                    .request_body(
                    ReplyMessageRequestBody.builder()
                    .content(content_json)
                    .msg_type("interactive")
                    .build()
                ) \
                    .build()
                response = self._client.im.v1.message.reply(request)
            else:
                # 主动发送消息
                request = CreateMessageRequest.builder() \
                    .receive_id_type(receive_id_type) \
                    .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .content(content_json)
                    .msg_type("interactive")
                    .build()
                ) \
                    .build()
                response = self._client.im.v1.message.create(request)

            if not response.success():
                logger.error(
                    f"[Feishu Stream] 发送交互卡片失败: code={response.code}, "
                    f"msg={response.msg}, log_id={response.get_log_id()}"
                )
                return False

            logger.debug("[Feishu Stream] 发送交互卡片成功")
            return True

        except Exception as e:
            logger.error(f"[Feishu Stream] 发送交互卡片异常: {e}")
            return False

    def reply_text(self, message_id: str, text: str, at_user: bool = False,
                   user_id: Optional[str] = None) -> bool:
        """
        回复文本消息（支持交互卡片和分段发送）

        Args:
            message_id: 原消息 ID
            text: 回复文本
            at_user: 是否 @用户
            user_id: 用户 open_id（at_user=True 时需要）

        Returns:
            是否发送成功
        """
        # 将文本转换为飞书 Markdown 格式
        formatted_text = format_feishu_markdown(text)

        # 检查是否需要分段发送
        content_bytes = len(formatted_text.encode('utf-8'))
        if content_bytes > self._max_bytes:
            logger.info(
                f"[Feishu Stream] 回复消息内容超长({content_bytes}字节)，将分批发送"
            )
            return self._send_to_chat_chunked(
                formatted_text,
                lambda chunk: self._send_interactive_card(
                    chunk,
                    message_id=message_id,
                    at_user=at_user,
                    user_id=user_id,
                ),
            )

        # 单条消息，使用交互卡片
        return self._send_interactive_card(
            formatted_text, message_id=message_id, at_user=at_user, user_id=user_id
        )

    def send_to_chat(self, chat_id: str, text: str,
                     receive_id_type: str = "chat_id") -> bool:
        """
        发送消息到指定会话（支持交互卡片和分段发送）

        Args:
            chat_id: 会话 ID
            text: 消息文本
            receive_id_type: 接收者 ID 类型，默认 chat_id

        Returns:
            是否发送成功
        """
        # 将文本转换为飞书 Markdown 格式
        formatted_text = format_feishu_markdown(text)

        # 检查是否需要分段发送
        content_bytes = len(formatted_text.encode('utf-8'))
        if content_bytes > self._max_bytes:
            logger.info(
                f"[Feishu Stream] 发送消息内容超长({content_bytes}字节)，将分批发送"
            )
            return self._send_to_chat_chunked(
                formatted_text,
                lambda chunk: self._send_interactive_card(
                    chunk,
                    chat_id=chat_id,
                    receive_id_type=receive_id_type,
                ),
            )

        # 单条消息，使用交互卡片
        return self._send_interactive_card(formatted_text, chat_id=chat_id, receive_id_type=receive_id_type)

    def _send_to_chat_chunked(self, content: str, send_func: Callable[[str], bool]) -> bool:
        """
        分批发送消息（支持交互卡片和分段发送）

        Args:
            content: 消息文本
            send_func: 发送单个分片的函数，返回是否发送成功

        Returns:
            是否全部发送成功
        """
        chunks = chunk_content_by_max_bytes(content, self._max_bytes, add_page_marker=True)
        success_count = 0
        for i, chunk in enumerate(chunks):
            if send_func(chunk):
                success_count += 1
            else:
                logger.error(f"[Feishu Stream] 发送消息失败: {chunk}")
            if i < len(chunks) - 1:
                time.sleep(1)
        return success_count == len(chunks)
