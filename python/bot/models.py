# -*- coding: utf-8 -*-
"""
===================================
机器人出站响应模型
===================================

定义命令处理器返回、由平台适配器转换为平台格式的响应模型。
入站消息模型 ``BotMessage`` / ``ChatType`` / ``Platform`` 已下沉到
``src.domain.notification.bot_message``：它被应用编排与通知实现共同消费，不能由驱动层
提供，否则会形成 ``src → bot`` 的反向依赖。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class BotResponse:
    """
    统一的机器人响应模型
    
    命令处理器返回此模型，由平台适配器转换为平台特定格式。
    
    Attributes:
        text: 回复文本
        markdown: 是否为 Markdown 格式
        at_user: 是否 @发送者
        reply_to_message: 是否回复原消息
        extra: 额外数据（平台特定）
    """
    text: str
    markdown: bool = False
    at_user: bool = True
    reply_to_message: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def text_response(cls, text: str, at_user: bool = True) -> 'BotResponse':
        """创建纯文本响应"""
        return cls(text=text, markdown=False, at_user=at_user)
    
    @classmethod
    def markdown_response(cls, text: str, at_user: bool = True) -> 'BotResponse':
        """创建 Markdown 响应"""
        return cls(text=text, markdown=True, at_user=at_user)
    
    @classmethod
    def error_response(cls, message: str) -> 'BotResponse':
        """创建错误响应"""
        return cls(text=f"❌ 错误：{message}", markdown=False, at_user=True)


@dataclass
class WebhookResponse:
    """
    Webhook 响应模型
    
    平台适配器返回此模型，包含 HTTP 响应内容。
    
    Attributes:
        status_code: HTTP 状态码
        body: 响应体（字典，将被 JSON 序列化）
        headers: 额外的响应头
    """
    status_code: int = 200
    body: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def success(cls, body: Optional[Dict] = None) -> 'WebhookResponse':
        """创建成功响应"""
        return cls(status_code=200, body=body or {})
    
    @classmethod
    def challenge(cls, challenge: str) -> 'WebhookResponse':
        """创建验证响应（用于平台 URL 验证）"""
        return cls(status_code=200, body={"challenge": challenge})
    
    @classmethod
    def error(cls, message: str, status_code: int = 400) -> 'WebhookResponse':
        """创建错误响应"""
        return cls(status_code=status_code, body={"error": message})
