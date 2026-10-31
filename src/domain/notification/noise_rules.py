# -*- coding: utf-8 -*-
"""Notification severity / quiet-hours business rules (pure).

本模块是通知降噪**规则语义**的唯一真源：等级词表、等级默认派生、免打扰时段
解析与校验、时区校验、时刻是否落在免打扰区间。全部为纯函数与常量，无 IO、
无进程状态，因此可被 ``src/config``（配置校验）与 ``src/application``
（降噪门控）同向依赖。

进程内的 dedup / cooldown 状态机仍留在
``src/application/notification/noise.py``（P4 降噪门控是用例编排而非领域规则）。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Tuple

try:  # pragma: no cover - Python <3.9 fallback is not expected in CI.
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore

NOTIFICATION_SEVERITIES: Tuple[str, ...] = ("info", "warning", "error", "critical")
NOTIFICATION_SEVERITY_RANK = {severity: index for index, severity in enumerate(NOTIFICATION_SEVERITIES)}
DEFAULT_NOTIFICATION_SEVERITY_BY_ROUTE = {
    "report": "info",
    "alert": "warning",
    "system_error": "error",
}
P4_NOISE_ENV_KEYS: Tuple[str, ...] = (
    "NOTIFICATION_DEDUP_TTL_SECONDS",
    "NOTIFICATION_COOLDOWN_SECONDS",
    "NOTIFICATION_QUIET_HOURS",
    "NOTIFICATION_TIMEZONE",
    "NOTIFICATION_MIN_SEVERITY",
    "NOTIFICATION_DAILY_DIGEST_ENABLED",
)

_QUIET_HOURS_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$")


def is_supported_notification_severity(value: object) -> bool:
    """Return whether *value* is a supported severity string."""
    return str(value or "").strip().lower() in NOTIFICATION_SEVERITY_RANK


def normalize_notification_severity(route_type: Optional[str], severity: Optional[str] = None) -> str:
    """Normalize explicit severity, or derive a default from route type."""
    explicit = str(severity or "").strip().lower()
    if explicit in NOTIFICATION_SEVERITY_RANK:
        return explicit

    route = str(route_type or "").strip().lower()
    return DEFAULT_NOTIFICATION_SEVERITY_BY_ROUTE.get(route, "info")


def parse_notification_quiet_hours(value: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse ``HH:MM-HH:MM`` into start/end minute-of-day values."""
    raw = str(value or "").strip()
    if not raw:
        return None

    match = _QUIET_HOURS_RE.match(raw)
    if not match:
        raise ValueError("NOTIFICATION_QUIET_HOURS must be in HH:MM-HH:MM format")

    start_hour, start_minute, end_hour, end_minute = [int(group) for group in match.groups()]
    return start_hour * 60 + start_minute, end_hour * 60 + end_minute


def validate_notification_timezone(value: Optional[str]) -> None:
    """Validate an optional IANA timezone name."""
    raw = str(value or "").strip()
    if not raw:
        return
    if ZoneInfo is None:
        raise ValueError("zoneinfo is unavailable")
    try:
        ZoneInfo(raw)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {raw}") from exc


def is_time_in_quiet_hours(now: datetime, quiet_hours: Tuple[int, int]) -> bool:
    """Return whether *now* falls inside a quiet-hours interval."""
    start_minute, end_minute = quiet_hours
    minute_of_day = now.hour * 60 + now.minute

    if start_minute == end_minute:
        return False
    if start_minute < end_minute:
        return start_minute <= minute_of_day < end_minute
    return minute_of_day >= start_minute or minute_of_day < end_minute
