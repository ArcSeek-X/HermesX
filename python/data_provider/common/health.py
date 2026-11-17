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
from typing import Any, Dict, Optional
import logging


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


# 旧实时/筹码熔断器保持原独立状态机，不与能力健康探针注册表合并。
logger = logging.getLogger("data_provider.realtime_types")


class CircuitBreaker:
    """
    熔断器 - 管理数据源的熔断/冷却状态

    策略：
    - 连续失败 N 次后进入熔断状态
    - 熔断期间跳过该数据源
    - 冷却时间后自动恢复半开状态
    - 半开状态下单次成功则完全恢复，失败则继续熔断

    状态机：
    CLOSED（正常） --失败N次--> OPEN（熔断）--冷却时间到--> HALF_OPEN（半开）
    HALF_OPEN --成功--> CLOSED
    HALF_OPEN --失败--> OPEN
    """

    # 状态常量
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态（不可用）
    HALF_OPEN = "half_open"  # 半开状态（试探性请求）

    def __init__(
        self,
        failure_threshold: int = 3,       # 连续失败次数阈值
        cooldown_seconds: float = 300.0,  # 冷却时间（秒），默认5分钟
        half_open_max_calls: int = 1      # 半开状态最大尝试次数
    ):
        """构造实时行情数据结构实例。"""
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_calls = half_open_max_calls

        # 各数据源状态 {source_name: {state, failures, last_failure_time, half_open_calls}}
        self._states: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

    def _get_state_locked(self, source: str) -> Dict[str, Any]:
        """获取或初始化数据源状态（调用方需持有锁）。"""
        if source not in self._states:
            self._states[source] = {
                'state': self.CLOSED,
                'failures': 0,
                'last_failure_time': 0.0,
                'half_open_calls': 0
            }
        return self._states[source]

    def is_available(self, source: str) -> bool:
        """
        检查数据源是否可用

        返回 True 表示可以尝试请求
        返回 False 表示应跳过该数据源
        """
        with self._lock:
            state = self._get_state_locked(source)
            current_time = time.time()

            if state['state'] == self.CLOSED:
                return True

            if state['state'] == self.OPEN:
                # 检查冷却时间
                time_since_failure = current_time - state['last_failure_time']
                if time_since_failure >= self.cooldown_seconds:
                    # 冷却完成，进入半开状态（不预占名额，由 HALF_OPEN 分支统一管理）
                    state['state'] = self.HALF_OPEN
                    state['half_open_calls'] = 0
                    state['last_failure_time'] = current_time
                    logger.info(f"[熔断器] {source} 冷却完成，进入半开状态")
                    # Fall through to HALF_OPEN check below
                else:
                    remaining = self.cooldown_seconds - time_since_failure
                    logger.debug(f"[熔断器] {source} 处于熔断状态，剩余冷却时间: {remaining:.0f}s")
                    return False

            if state['state'] == self.HALF_OPEN:
                if state['half_open_calls'] < self.half_open_max_calls:
                    state['half_open_calls'] += 1
                    return True
                # 所有探测名额已用完；若冷却时间再次到期仍未收到
                # record_success/record_failure 回调，重置名额允许重新探测，
                # 避免永久卡在 HALF_OPEN。
                time_since_failure = current_time - state['last_failure_time']
                if time_since_failure >= self.cooldown_seconds:
                    state['half_open_calls'] = 1
                    state['last_failure_time'] = current_time
                    logger.info(f"[熔断器] {source} 半开状态探测超时，重新探测")
                    return True
                return False

            return True

    def record_inconclusive(self, source: str) -> None:
        """记录不确定的探测结果（如返回 None）。

        仅影响 HALF_OPEN 状态：将其转回 OPEN 以便冷却后重新探测。
        CLOSED 状态下为空操作，不影响失败计数。
        """
        with self._lock:
            state = self._get_state_locked(source)
            if state['state'] == self.HALF_OPEN:
                state['state'] = self.OPEN
                state['half_open_calls'] = 0
                state['last_failure_time'] = time.time()
                logger.info(f"[熔断器] {source} 半开探测结果不确定，重新进入冷却")

    def record_success(self, source: str) -> None:
        """记录成功请求"""
        with self._lock:
            state = self._get_state_locked(source)

            if state['state'] == self.HALF_OPEN:
                # 半开状态下成功，完全恢复
                logger.info(f"[熔断器] {source} 半开状态请求成功，恢复正常")

            # 重置状态
            state['state'] = self.CLOSED
            state['failures'] = 0
            state['half_open_calls'] = 0

    def record_failure(self, source: str, error: Optional[str] = None) -> None:
        """记录失败请求"""
        with self._lock:
            state = self._get_state_locked(source)
            current_time = time.time()

            state['failures'] += 1
            state['last_failure_time'] = current_time

            if state['state'] == self.HALF_OPEN:
                # 半开状态下失败，继续熔断
                state['state'] = self.OPEN
                state['half_open_calls'] = 0
                logger.warning(f"[熔断器] {source} 半开状态请求失败，继续熔断 {self.cooldown_seconds}s")
            elif state['failures'] >= self.failure_threshold:
                # 达到阈值，进入熔断
                state['state'] = self.OPEN
                logger.warning(f"[熔断器] {source} 连续失败 {state['failures']} 次，进入熔断状态 "
                              f"(冷却 {self.cooldown_seconds}s)")
                if error:
                    logger.warning(f"[熔断器] 最后错误: {error}")

    def get_status(self) -> Dict[str, str]:
        """获取所有数据源状态"""
        with self._lock:
            return {source: info['state'] for source, info in self._states.items()}

    def reset(self, source: Optional[str] = None) -> None:
        """重置熔断器状态"""
        with self._lock:
            if source:
                if source in self._states:
                    del self._states[source]
            else:
                self._states.clear()


# 全局熔断器实例（实时行情专用）
_realtime_circuit_breaker = CircuitBreaker(
    failure_threshold=3,      # 连续失败3次熔断
    cooldown_seconds=300.0,   # 冷却5分钟
    half_open_max_calls=1
)

# 筹码接口熔断器（更保守的策略，因为该接口更不稳定）
_chip_circuit_breaker = CircuitBreaker(
    failure_threshold=2,      # 连续失败2次熔断
    cooldown_seconds=600.0,   # 冷却10分钟
    half_open_max_calls=1
)


def get_realtime_circuit_breaker() -> CircuitBreaker:
    """获取实时行情熔断器"""
    return _realtime_circuit_breaker


def get_chip_circuit_breaker() -> CircuitBreaker:
    """获取筹码接口熔断器"""
    return _chip_circuit_breaker


__all__ += ["CircuitBreaker", "get_realtime_circuit_breaker", "get_chip_circuit_breaker"]
