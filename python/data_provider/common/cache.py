# -*- coding: utf-8 -*-
"""
@file: cache.py
@description: data_provider 公共 TTL 缓存实现，供各功能包的 Manager 与 source 复用。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from threading import RLock
import time
from typing import Any, Dict, Optional, Tuple


_MISS = object()


class SharedTtlCache:
    """线程安全的轻量 TTL 缓存。"""

    def __init__(self) -> None:
        """初始化缓存容器与锁。"""
        self._items: Dict[str, Tuple[float, Any]] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any:
        """按 key 读取缓存，未命中或过期时返回内部哨兵值。"""
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return _MISS

            expires_at, value = item
            if expires_at < time.time():
                self._items.pop(key, None)
                return _MISS
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """写入缓存，并为 key 设置过期时间。"""
        with self._lock:
            ttl = max(int(ttl_seconds), 1)
            self._items[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        """主动删除某个缓存键。"""
        with self._lock:
            self._items.pop(key, None)

    def clear(self) -> None:
        """清空全部缓存项。"""
        with self._lock:
            self._items.clear()


_SHARED_CACHE: Optional[SharedTtlCache] = None
_SHARED_CACHE_LOCK = RLock()


def get_shared_ttl_cache() -> SharedTtlCache:
    """返回进程内共享 TTL 缓存实例。"""
    global _SHARED_CACHE
    if _SHARED_CACHE is not None:
        return _SHARED_CACHE

    with _SHARED_CACHE_LOCK:
        if _SHARED_CACHE is None:
            _SHARED_CACHE = SharedTtlCache()
    return _SHARED_CACHE


__all__ = ["SharedTtlCache", "get_shared_ttl_cache", "_MISS"]
