# -*- coding: utf-8 -*-
"""
===================================
StockDB 共享客户端
===================================

职责：
1. 封装 StockDB 本地 HTTP 协议，作为 `local` source 的唯一接线层。
2. 提供 K 线 / 基础信息 / 代码搜索三类能力共享的只读访问方法。
3. 统一连接异常、结构异常、TTL 缓存与冷却短路，避免各能力重复实现。
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from threading import RLock
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

_MISS = object()


class StockDbError(RuntimeError):
    """StockDB 调用失败。"""

    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class StockDbSettings:
    """StockDB 运行配置。"""

    enabled: bool
    base_url: str
    timeout_ms: int
    max_rows: int
    cache_ttl_sec: int
    cooldown_sec: int


def settings_from_config(config: Any) -> StockDbSettings:
    """从全局 Config 生成 StockDB 设置。"""
    return StockDbSettings(
        enabled=bool(getattr(config, "stockdb_enabled", False)),
        base_url=str(getattr(config, "stockdb_base_url", "http://127.0.0.1:7899")).rstrip("/"),
        timeout_ms=int(getattr(config, "stockdb_timeout_ms", 5000)),
        max_rows=int(getattr(config, "stockdb_max_rows", 5000)),
        cache_ttl_sec=int(getattr(config, "stockdb_cache_ttl_sec", 60)),
        cooldown_sec=int(getattr(config, "stockdb_cooldown_sec", 10)),
    )


class _TtlCache:
    """轻量线程安全 TTL 缓存。"""

    def __init__(self) -> None:
        self._items: Dict[str, Tuple[float, Any]] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any:
        with self._lock:
            item = self._items.get(key)
            if not item:
                return _MISS
            expires_at, value = item
            if expires_at < time.time():
                self._items.pop(key, None)
                return _MISS
            return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            self._items[key] = (time.time() + max(ttl, 1), value)


class StockDbClient:
    """StockDB 只读 HTTP 客户端。"""

    def __init__(self, settings: StockDbSettings) -> None:
        self.settings = settings
        self._cache = _TtlCache()
        self._cooldown_until = 0.0
        self._session = requests.Session()
        self._session.trust_env = False
        self._session.proxies = {"http": None, "https": None}

    def _guard_enabled(self) -> None:
        if not self.settings.enabled:
            raise StockDbError("stockdb_disabled", "本地 StockDB 数据源未启用", 503)
        if time.time() < self._cooldown_until:
            raise StockDbError("stockdb_unavailable", "本地 StockDB 正处于冷却期，请稍后重试", 503)

    def _request(self, params: Dict[str, Any], *, cache_key: Optional[str] = None, ttl: Optional[int] = None) -> Any:
        self._guard_enabled()
        final_params = {k: v for k, v in params.items() if v not in (None, "")}
        final_params["json"] = 1
        cache_ttl = self.settings.cache_ttl_sec if ttl is None else ttl
        key = cache_key or urlencode(sorted((str(k), str(v)) for k, v in final_params.items()))
        cached = self._cache.get(key)
        if cached is not _MISS:
            return cached
        try:
            response = self._session.get(
                f"{self.settings.base_url}/",
                params=final_params,
                timeout=max(self.settings.timeout_ms, 1) / 1000.0,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            self._cooldown_until = time.time() + self.settings.cooldown_sec
            raise StockDbError(
                "stockdb_unavailable",
                f"本地 StockDB 服务不可达：{exc}",
                503,
            ) from exc
        except ValueError as exc:
            raise StockDbError("stockdb_bad_response", "StockDB 返回的不是合法 JSON", 502) from exc

        self._cache.set(key, payload, cache_ttl)
        return payload

    def ping(self) -> Tuple[bool, Optional[int]]:
        """返回连通状态与近似条目数。"""
        try:
            payload = self._request({"cmd": "len", "t": "股票代码"}, cache_key="ping", ttl=10)
        except StockDbError:
            return False, None
        count = payload if isinstance(payload, int) else None
        return True, count

    def fetch_daily_bars(self, stock_code: str, start: str = "", end: str = "", limit: Optional[int] = None) -> Any:
        """读取日 K 原始数据。"""
        params: Dict[str, Any] = {
            "cmd": "vals",
            "t": "日k",
            "k1": f"key:{stock_code}",
            "k2": f"fwd:{start},{end}" if start and end else "all:",
        }
        if limit:
            capped = max(min(limit, self.settings.max_rows), 1)
            params["num"] = -capped
        return self._request(params, ttl=self.settings.cache_ttl_sec)

    def fetch_minute_bars(self, stock_code: str, start: str = "", end: str = "", limit: Optional[int] = None) -> Any:
        """读取分钟 K 原始数据。"""
        params: Dict[str, Any] = {
            "cmd": "vals",
            "t": "分钟k",
            "k1": f"key:{stock_code}",
            "k2": f"fwd:{start},{end}" if start and end else "all:",
        }
        if limit:
            capped = max(min(limit, self.settings.max_rows), 1)
            params["num"] = -capped
        return self._request(params, ttl=self.settings.cache_ttl_sec)

    def fetch_adjust_factors(self, stock_code: str) -> Any:
        """读取复权事件。"""
        return self._request(
            {"cmd": "vals", "t": "复权", "k1": f"key:{stock_code}", "k2": "all:"},
            ttl=max(self.settings.cache_ttl_sec, 300),
        )

    def fetch_code_index(self) -> Any:
        """读取股票代码总表。"""
        return self._request(
            {"cmd": "get", "t": "股票代码"},
            cache_key="stock_codes",
            ttl=max(self.settings.cache_ttl_sec, 3600),
        )

    def fetch_boards(self) -> Any:
        """读取板块表。"""
        return self._request(
            {"cmd": "vals", "t": "板块*"},
            cache_key="stock_boards",
            ttl=max(self.settings.cache_ttl_sec, 300),
        )


_CLIENT: Optional[StockDbClient] = None
_CLIENT_LOCK = RLock()


def get_stockdb_client() -> StockDbClient:
    """返回进程内共享客户端。"""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None:
            from src.config import get_config

            _CLIENT = StockDbClient(settings_from_config(get_config()))
            logger.info("[StockDB] client initialized with base_url=%s", _CLIENT.settings.base_url)
    return _CLIENT

