# -*- coding: utf-8 -*-
"""通知诊断用例（应用层）。

分层说明：本包当前持有通知渠道配置只读诊断与格式化逻辑（notification_diagnostics），
以及告警用例的日线取数端口（DailyBarFetcherPort）。后续 alert_service / alert_worker
搬入时在此扩展 re-export，届时一并收束 src.config 过渡设计债。
"""

from __future__ import annotations

from src.application.alert.ports import DailyBarFetcherPort
from src.application.alert.notification_diagnostics import (  # noqa: F401
    CHANNEL_SPECS,
    KEY_SPECS,
    NotificationChannelSpec,
    NotificationDiagnosticIssue,
    NotificationDiagnosticResult,
    NotificationKeySpec,
    P0_ACTIONS_ENV_KEYS,
    P3_ROUTE_ENV_KEYS,
    P4_NOISE_ACTIONS_ENV_KEYS,
    P6_CHANNEL_ACTIONS_ENV_KEYS,
    format_notification_diagnostics,
    run_notification_diagnostics,
)

__all__ = [
    "DailyBarFetcherPort",
    "CHANNEL_SPECS",
    "KEY_SPECS",
    "NotificationChannelSpec",
    "NotificationDiagnosticIssue",
    "NotificationDiagnosticResult",
    "NotificationKeySpec",
    "P0_ACTIONS_ENV_KEYS",
    "P3_ROUTE_ENV_KEYS",
    "P4_NOISE_ACTIONS_ENV_KEYS",
    "P6_CHANNEL_ACTIONS_ENV_KEYS",
    "format_notification_diagnostics",
    "run_notification_diagnostics",
]
