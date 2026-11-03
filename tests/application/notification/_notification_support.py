# -*- coding: utf-8 -*-
"""
===================================
A股自选股智能分析系统 - 通知服务单元测试
===================================

职责：
1. 验证通知服务的配置检测逻辑
2. 验证通知服务的渠道检测逻辑
3. 验证通知服务的消息发送逻辑

TODO: 
1. 添加发送渠道以外的测试，如：
    - 生成日报
2. 添加 send_to_context 的测试
"""
import sys
import unittest
from unittest import mock
from typing import Optional

# Keep this test runnable when optional LLM/runtime deps are not installed.
for optional_module in ("litellm", "json_repair"):
    try:
        __import__(optional_module)
    except ModuleNotFoundError:
        sys.modules[optional_module] = mock.MagicMock()

from src.config import Config
from src.application.notification.notification import NotificationBuilder, NotificationChannel, NotificationService
from src.application.notification.noise import reset_notification_noise_state
from src.application.analysis.analyzer import AnalysisResult
from src.domain.notification.bot_message import BotMessage, ChatType
import requests


def _make_config(**overrides) -> Config:
    """Create a Config instance overriding only notification-related fields."""
    return Config(stock_list=[], **overrides)


def _make_response(status_code: int, json: Optional[dict] = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    if json:
        response.json = lambda: json
    return response


def _attach_decision_signal_summary(result: AnalysisResult) -> AnalysisResult:
    result.decision_signal_summary = {
        "action": "sell",
        "action_label": "卖出",
        "horizon": "1d",
        "reason": "技术面走弱",
    }
    return result


def _make_feishu_message() -> BotMessage:
    return BotMessage(
        platform="feishu",
        message_id="msg-1",
        user_id="user-1",
        user_name="tester",
        chat_id="chat-1",
        chat_type=ChatType.GROUP,
        content="/a 600519",
    )


def _make_dingtalk_message() -> BotMessage:
    return BotMessage(
        platform="dingtalk",
        message_id="msg-2",
        user_id="user-2",
        user_name="tester",
        chat_id="dingtalk-chat",
        chat_type=ChatType.GROUP,
        content="/a 600519",
        raw_data={
            "sessionWebhook": "https://oapi.dingtalk.com/robot/sendBySession?session=abc123",
        },
    )


def _make_telegram_message() -> BotMessage:
    return BotMessage(
        platform="telegram",
        message_id="msg-3",
        user_id="user-3",
        user_name="tester",
        chat_id="100200300",
        chat_type=ChatType.PRIVATE,
        content="/a 600519",
        raw_data={"chat_id": "100200300"},
    )


class _TestNotificationServiceSendToMethodsFixture:
    """测试通知发送服务

    测试设计：

    测试按照渠道的字母顺序排列，在合适位置添加新的测试方法。
    如果采用长消息分批发送，必须单独测试分批发送的逻辑，
        e.g. test_send_to_discord_via_notification_service_with_bot_requires_chunking

    1. 添加模拟配置：
    使用 mock.patch 装饰器来模拟 get_config 函数，
    使用 _make_config 函数添加配置，并返回 Config 实例。

    2. 检查配置是否正确：
    使用 assertIn 检查 NotificationChannel.xxxx 是否在
    `NotificationService.get_available_channels()` 返回值中。

    3. 模拟请求响应：
    使用 mock.patch 装饰器来模拟 requests.post 函数，
    使用 _make_response 函数模拟请求响应，并返回 Response 实例。
    若使用其他函数模拟请求响应，则使用 mock.patch 装饰器来模拟该函数。

    4. 使用 assertTrue 检查 send 的返回值。

    5. 使用 assert_called_once 检查请求函数是否被调用一次。
    测试分批发送时，使用 assertAlmostEqual(mock_post.call_count, ...) 检查请求函数被调用次数

    """
    def setUp(self):
        reset_notification_noise_state()


class _TestNotificationServiceReportGenerationFixture:
    """报告生成与选路相关测试。"""
    def _make_fundamental_context(self) -> dict:
        return {
            "earnings": {
                "status": "ok",
                "data": {
                    "financial_report": {
                        "report_date": "2024-09-30",
                        "revenue": 1_236_000_000_000.0,  # 1.236 万亿 -> 12360.00 亿元
                        "net_profit_parent": 60_800_000_000.0,
                        "operating_cash_flow": 72_500_000_000.0,
                        "roe": 22.45,
                    },
                    "dividend": {
                        "events": [
                            {
                                "event_date": "2024-06-26",
                                "ex_dividend_date": "2024-06-26",
                                "cash_dividend_per_share": 30.876,
                                "is_pre_tax": True,
                            }
                        ],
                        "ttm_event_count": 1,
                        "ttm_cash_dividend_per_share": 30.876,
                        "ttm_dividend_yield_pct": 1.85,
                    },
                },
            },
            "growth": {
                "status": "ok",
                "data": {
                    "revenue_yoy": 15.23,
                    "net_profit_yoy": 19.87,
                    "roe": 22.45,
                    "gross_margin": 91.55,
                },
            },
            "boards": {
                "status": "ok",
                "data": {
                    "top": [
                        {"name": "白酒", "change_pct": 3.42},
                        {"name": "食品饮料", "change_pct": 2.10},
                    ],
                    "bottom": [
                        {"name": "光伏设备", "change_pct": -2.65},
                    ],
                },
            },
            "concept_boards": {
                "status": "ok",
                "data": {
                    "top": [
                        {"name": "MSCI中国", "change_pct": 1.23},
                    ],
                    "bottom": [],
                },
            },
            "belong_boards": [
                {"name": "白酒", "code": "BK0596", "type": "行业"},
                {"name": "MSCI中国", "code": "BK0805", "type": "概念"},
            ],
        }

