# -*- coding: utf-8 -*-
"""
@file: rate_limit.py
@description: data_provider 公共限流护栏，提供按名称复用的并发信号量。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from contextlib import contextmanager
from threading import BoundedSemaphore, RLock
from typing import Dict, Iterator


class RateLimitRegistry:
    """管理具名并发配额的注册表。"""

    def __init__(self) -> None:
        """初始化信号量映射。"""
        self._semaphores: Dict[str, BoundedSemaphore] = {}
        self._lock = RLock()

    def get(self, name: str, concurrency: int) -> BoundedSemaphore:
        """按名称获取并发信号量。"""
        with self._lock:
            semaphore = self._semaphores.get(name)
            if semaphore is None:
                semaphore = BoundedSemaphore(max(int(concurrency), 1))
                self._semaphores[name] = semaphore
            return semaphore

    @contextmanager
    def guard(self, name: str, concurrency: int = 4) -> Iterator[None]:
        """在 with 语句中为指定名称施加并发限制。"""
        semaphore = self.get(name, concurrency)
        semaphore.acquire()
        try:
            yield
        finally:
            semaphore.release()


_REGISTRY = RateLimitRegistry()


@contextmanager
def rate_limit_guard(name: str, concurrency: int = 4) -> Iterator[None]:
    """使用共享注册表为调用方施加并发护栏。"""
    with _REGISTRY.guard(name, concurrency):
        yield


__all__ = ["RateLimitRegistry", "rate_limit_guard"]
