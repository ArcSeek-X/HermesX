# -*- coding: utf-8 -*-
"""Decision profile domain helpers for persisted DecisionSignal identity.

SQL same-profile semantics are intentionally null-safe:

- ``profile is None`` means legacy/unknown profile and must be expressed as
  ``decision_profile IS NULL``.
- a non-null profile must be expressed as ``decision_profile = <profile>``.

Do not use bare ``None`` to mean "all profiles" in list filters. Use the
normalized filter object below so omitted/empty filters and ``unknown`` remain
distinct.

决策画像（decision_profile）领域辅助工具，用于持久化 DecisionSignal 的身份语义。
SQL 同画像语义刻意保持空安全：profile 为 None 表示遗留/未知画像（表达为 decision_profile IS NULL），
非 None 则表达为 decision_profile = <profile>。列表过滤不要用裸 None 表示「全部画像」，
而应使用下方归一化过滤器对象，使「省略/空」与「unknown」保持区分。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional


DecisionProfile = Literal["conservative", "balanced", "aggressive"]
DecisionProfileFilterKind = Literal["all", "unknown", "profile"]

VALID_DECISION_PROFILES: tuple[DecisionProfile, ...] = (
    "conservative",
    "balanced",
    "aggressive",
)
DECISION_PROFILE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class DecisionProfileFilter:
    """决策画像过滤器：区分 all / unknown / 指定 profile 三种语义，用于列表过滤时保持空值与 unknown 的差别。"""

    kind: DecisionProfileFilterKind
    profile: Optional[DecisionProfile] = None

    @property
    def is_all(self) -> bool:
        """是否为「全部画像」过滤（kind == 'all'）。"""
        return self.kind == "all"

    @property
    def is_unknown(self) -> bool:
        """是否为「未知画像」过滤（kind == 'unknown'）。"""
        return self.kind == "unknown"


DECISION_PROFILE_FILTER_ALL = DecisionProfileFilter("all")
DECISION_PROFILE_FILTER_UNKNOWN = DecisionProfileFilter("unknown")


def normalize_decision_profile(
    value: Any,
    *,
    field_name: str = "decision_profile",
) -> Optional[DecisionProfile]:
    """Return a normalized profile or raise for a non-empty invalid value."""

    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in VALID_DECISION_PROFILES:
        return text  # type: ignore[return-value]
    allowed = ", ".join(VALID_DECISION_PROFILES)
    raise ValueError(f"{field_name} must be one of: {allowed}")


def normalize_decision_profile_filter(value: Any) -> DecisionProfileFilter:
    """Normalize list-filter input while preserving all-vs-unknown semantics."""

    if value in (None, ""):
        return DECISION_PROFILE_FILTER_ALL
    text = str(value).strip().lower()
    if not text:
        return DECISION_PROFILE_FILTER_ALL
    if text == DECISION_PROFILE_UNKNOWN:
        return DECISION_PROFILE_FILTER_UNKNOWN
    profile = normalize_decision_profile(text, field_name="decision_profile")
    return DecisionProfileFilter("profile", profile)


def extract_legacy_decision_profile(metadata: Any) -> Optional[DecisionProfile]:
    """Extract a legal legacy profile from metadata; invalid values are ignored."""

    if not isinstance(metadata, dict):
        return None
    try:
        return normalize_decision_profile(metadata.get("decision_profile"))
    except ValueError:
        return None
