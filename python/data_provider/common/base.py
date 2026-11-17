# -*- coding: utf-8 -*-
"""
@file: base.py
@description: data_provider 公共泛型底座，统一数据源协议、选源顺序、回退、健康探针与可选缓存。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Dict, Generic, Iterable, List, Optional, TypeVar

from data_provider.common.cache import _MISS, SharedTtlCache, get_shared_ttl_cache
from data_provider.common.health import HealthProbeRegistry, get_health_probe_registry
from src.config import get_config

logger = logging.getLogger(__name__)

RequestT = TypeVar("RequestT")
ResultT = TypeVar("ResultT")


class DataSource(ABC, Generic[RequestT, ResultT]):
    """所有功能包 source 的公共抽象。"""

    source_id: str = ""

    def is_available(self) -> bool:
        """返回 source 当前是否可用。默认始终可尝试。"""
        return True

    @abstractmethod
    def fetch(self, request: RequestT) -> Optional[ResultT]:
        """执行一次取数，并返回标准化结果。"""


class DataSourceManager(Generic[RequestT, ResultT], ABC):
    """统一管理 source 顺序、回退、健康与缓存的公共 Manager。"""

    def __init__(
        self,
        *,
        sources: Dict[str, DataSource[RequestT, ResultT]],
        default_source_order: Iterable[str],
        data_source_key: str,
        source_priority_key: str,
        fallback_enabled_key: str,
        cache_ttl_seconds: int = 0,
        health_cooldown_seconds: int = 10,
        cache: Optional[SharedTtlCache] = None,
        health_registry: Optional[HealthProbeRegistry] = None,
    ) -> None:
        """初始化 Manager 依赖与配置键。"""
        self.sources = sources
        self.default_source_order = tuple(default_source_order)
        self.data_source_key = data_source_key
        self.source_priority_key = source_priority_key
        self.fallback_enabled_key = fallback_enabled_key
        self.cache_ttl_seconds = max(int(cache_ttl_seconds), 0)
        self.health_cooldown_seconds = max(int(health_cooldown_seconds), 1)
        self.cache = cache or get_shared_ttl_cache()
        self.health_registry = health_registry or get_health_probe_registry()

    def resolve_source_order(self) -> List[str]:
        """按运行时配置解析当前请求的 source 优先级链。"""
        config = get_config()
        raw_value = (getattr(config, self.data_source_key, "") or "").strip().lower()
        raw_priority = (
            getattr(config, self.source_priority_key, "") or ",".join(self.default_source_order)
        ).strip().lower()
        fallback_enabled = bool(getattr(config, self.fallback_enabled_key, True))

        # 兼容旧配置：如果主源字段直接给的是逗号列表，则按显式顺序执行。
        if "," in raw_value:
            return [item.strip() for item in raw_value.split(",") if item.strip()]

        priority_order = [item.strip() for item in raw_priority.split(",") if item.strip()]
        if not priority_order:
            priority_order = list(self.default_source_order)

        if not raw_value or raw_value == "auto":
            return priority_order if fallback_enabled else priority_order[:1]

        if not fallback_enabled:
            return [raw_value]

        ordered = [raw_value]
        ordered.extend(item for item in priority_order if item != raw_value)
        return ordered

    def fetch_first(self, request: RequestT) -> ResultT:
        """按配置顺序依次尝试 source，返回首个有效结果。"""
        cache_key = self.build_cache_key(request)
        if cache_key and self.cache_ttl_seconds > 0:
            cached = self.cache.get(cache_key)
            if cached is not _MISS:
                return cached

        errors: List[str] = []
        for source_id in self.resolve_source_order():
            source = self.sources.get(source_id)
            if source is None or not source.is_available():
                continue
            if not self.health_registry.can_try(source_id):
                continue

            try:
                result = source.fetch(request)
                if self.is_valid_result(result):
                    self.health_registry.mark_success(source_id)
                    finalized = self.finalize_result(result, request)
                    if cache_key and self.cache_ttl_seconds > 0:
                        self.cache.set(cache_key, finalized, self.cache_ttl_seconds)
                    return finalized
            except Exception as exc:  # noqa: BLE001 - Manager 负责回退与错误聚合
                logger.warning("[%s] source=%s failed: %s", self.__class__.__name__, source_id, exc)
                self.health_registry.mark_failure(source_id, str(exc), self.health_cooldown_seconds)
                errors.append(f"{source_id}:{exc}")

        raise LookupError(self.build_lookup_error_message(request, errors))

    def build_cache_key(self, request: RequestT) -> Optional[str]:
        """为请求构造可选缓存键；默认不缓存。"""
        return None

    def is_valid_result(self, result: Optional[ResultT]) -> bool:
        """判断 source 返回是否可视为有效结果。"""
        return result is not None

    def finalize_result(self, result: ResultT, request: RequestT) -> ResultT:
        """在命中 source 后执行统一补齐逻辑。默认原样返回。"""
        return result

    def build_lookup_error_message(self, request: RequestT, errors: List[str]) -> str:
        """构造最终查找失败的错误消息。"""
        request_repr = self.describe_request(request)
        return f"No data source returned data for {request_repr}: {', '.join(errors)}"

    def describe_request(self, request: RequestT) -> str:
        """为日志与异常生成可读请求描述。"""
        return repr(request)


__all__ = ["DataSource", "DataSourceManager"]
