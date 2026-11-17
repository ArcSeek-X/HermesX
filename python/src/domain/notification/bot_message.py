# -*- coding: utf-8 -*-
"""
===================================
入站消息值对象（跨层共享契约）
===================================

``BotMessage`` / ``ChatType`` / ``Platform`` 描述「谁在哪个会话里说了什么」，
被三类代码共同消费：

- 驱动层：``bot/platforms/*`` 把各平台回调归一成该对象；
- 应用编排：``src/application/analysis/pipeline.py``、``src/services/task_service.py``
  透传来源消息，并从中取 requester 上下文；
- 通知实现：``src/application/notification/notification.py`` 按来源消息决定回复目标。

它们因此不能留在 ``bot/models.py``：那会让编排层反向依赖驱动层。放在
``src/schemas/`` 是沿用本仓既有的「跨层数据契约」落点，与 ``bot/models.py``
里的 ``BotResponse`` / ``WebhookResponse``（仅驱动层出站响应）区分开。
本对象仍是传输信封，不是业务规则，因此不进 ``src/domain/``。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


class ChatType(str, Enum):
    """会话类型"""
    GROUP = "group"      # 群聊
    PRIVATE = "private"  # 私聊
    UNKNOWN = "unknown"  # 未知


class Platform(str, Enum):
    """平台类型"""
    FEISHU = "feishu"        # 飞书
    DINGTALK = "dingtalk"    # 钉钉
    WECOM = "wecom"          # 企业微信
    TELEGRAM = "telegram"    # Telegram
    UNKNOWN = "unknown"      # 未知


@dataclass
class BotMessage:
    """
    统一的机器人消息模型

    将各平台的消息格式统一为此模型，便于命令处理器处理。

    Attributes:
        platform: 平台标识
        message_id: 消息 ID（平台原始 ID）
        user_id: 发送者 ID
        user_name: 发送者名称
        chat_id: 会话 ID（群聊 ID 或私聊 ID）
        chat_type: 会话类型
        content: 消息文本内容（已去除 @机器人 部分）
        raw_content: 原始消息内容
        mentioned: 是否 @了机器人
        mentions: @的用户列表
        timestamp: 消息时间戳
        raw_data: 原始请求数据（平台特定，用于调试）
    """
    platform: str
    message_id: str
    user_id: str
    user_name: str
    chat_id: str
    chat_type: ChatType
    content: str
    raw_content: str = ""
    mentioned: bool = False
    mentions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def get_command_and_args(self, prefix: str = "/") -> tuple:
        """
        解析命令和参数

        Args:
            prefix: 命令前缀，默认 "/"

        Returns:
            (command, args) 元组，如 ("analyze", ["600519"])
            如果不是命令，返回 (None, [])
        """
        text = self.content.strip()

        # 检查是否以命令前缀开头
        if not text.startswith(prefix):
            # 尝试匹配中文命令（无前缀）
            chinese_commands = {
                '分析': 'analyze',
                '大盘': 'market',
                '批量': 'batch',
                '帮助': 'help',
                '状态': 'status',
            }
            for cn_cmd, en_cmd in chinese_commands.items():
                if text.startswith(cn_cmd):
                    args = text[len(cn_cmd):].strip().split()
                    return en_cmd, args
            return None, []

        # 去除前缀
        text = text[len(prefix):]

        # 分割命令和参数
        parts = text.split()
        if not parts:
            return None, []

        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        return command, args

    def is_command(self, prefix: str = "/") -> bool:
        """检查消息是否是命令"""
        cmd, _ = self.get_command_and_args(prefix)
        return cmd is not None
