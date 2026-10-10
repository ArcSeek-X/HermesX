# -*- coding: utf-8 -*-
"""
@file: health.py
@description: data_provider 公共健康探针，实现 source 级失败计数与冷却判断。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
import time
from typing import Dict, Optional


@dataclass
class SourceHealthState:
    """单个数据源的健康状态快照。"""

    source_id: str
    failure_count: int = 0
    last_error: str = ""
    cooldown_until: float = 0.0

    def is_available(self) -> bool:
        """判断当前数据源是否已脱离冷却期。"""
        return time.time() >= self.cooldown_until


class HealthProbeRegistry:
    """按 source_id 维护健康状态的注册表。"""

    def __init__(self) -> None:
        """初始化状态存储。"""
        self._states: Dict[str, SourceHealthState] = {}
        self._lock = RLock()

    def get_state(self, source_id: str) -> SourceHealthState:
        """读取某个数据源的健康状态，不存在时按默认值初始化。"""
        with self._lock:
            state = self._states.get(source_id)
            if state is None:
                state = SourceHealthState(source_id=source_id)
                self._states[source_id] = state
            return state

    def can_try(self, source_id: str) -> bool:
        """判断某个数据源当前是否允许再次尝试。"""
        return self.get_state(source_id).is_available()

    def mark_success(self, source_id: str) -> None:
        """记录一次成功调用，并清理失败状态。"""
        with self._lock:
            self._states[source_id] = SourceHealthState(source_id=source_id)

    def mark_failure(self, source_id: str, message: str, cooldown_seconds: int = 10) -> None:
        """记录一次失败调用，并在达到阈值后进入冷却期。"""
        with self._lock:
            state = self._states.get(source_id) or SourceHealthState(source_id=source_id)
            state.failure_count += 1
            state.last_error = message
            if state.failure_count >= 2:
                state.cooldown_until = time.time() + max(int(cooldown_seconds), 1)
            self._states[source_id] = state


_REGISTRY: Optional[HealthProbeRegistry] = None
_REGISTRY_LOCK = RLock()


def get_health_probe_registry() -> HealthProbeRegistry:
    """返回进程内共享的健康探针注册表。"""
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY

    with _REGISTRY_LOCK:
        if _REGISTRY is None:
            _REGISTRY = HealthProbeRegistry()
    return _REGISTRY


__all__ = ["HealthProbeRegistry", "SourceHealthState", "get_health_probe_registry"]
