# -*- coding: utf-8 -*-
"""
@file: base.py
@description: 实时行情能力抽象，统一 source 协议与 Manager 行为。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from data_provider.base import normalize_stock_code
from data_provider.common.base import DataSource, DataSourceManager
from data_provider.realtime_types import UnifiedRealtimeQuote


class RealtimeSource(DataSource[str, UnifiedRealtimeQuote]):
    """实时行情 source 公共抽象。"""


class RealtimeDataSourceManager(DataSourceManager[str, UnifiedRealtimeQuote]):
    """实时行情 Manager。"""

    def get_realtime_quote(self, stock_code: str) -> UnifiedRealtimeQuote:
        """获取首个有效的实时行情结果。

        入口先做代码归一（`000533.SZ` -> `000533`、`00700.HK` -> `HK00700`），
        与旧版 `DataFetcherManager.get_realtime_quote` 行为保持一致：下游通道
        拿到统一格式，缓存键也不会因代码书写风格不同而分裂。
        """
        return self.fetch_first(normalize_stock_code(stock_code or ""))

    def resolve_source_order(self) -> List[str]:
        """解析选源链，并剔除本能力未注册的源名。

        `realtime_source_priority` 沿用旧版实时行情配置键，其中可能包含本能力
        未注册的源（如 `efinance` / `tushare`）。过滤后若一个都不剩，则退回
        默认链，避免整条链落空导致「一个源都不尝试」的静默无数据。
        """
        known = [sid for sid in super().resolve_source_order() if sid in self.sources]
        if known:
            return known
        return [sid for sid in self.default_source_order if sid in self.sources]

    def build_cache_key(self, stock_code: str):
        """按股票代码构造短 TTL 缓存键。"""
        return f"realtime:{stock_code}"

    def is_valid_result(self, result):
        """实时行情至少要有价格数据。"""
        return result is not None and result.has_basic_data()


# 注册 id 与 REALTIME_SOURCE_PRIORITY 配置词表对齐；tickflow 需显式配置且已有 API Key
DEFAULT_SOURCE_ORDER = ("tencent", "akshare_sina", "akshare_em")


def _build_sources() -> Dict[str, RealtimeSource]:
    """构造实时行情能力默认 source 注册表。

    `tencent` / `akshare_sina` / `akshare_em` 分别对应 akshare 的三个行情通道
    （腾讯单股直连 / 新浪 / 东财全量），写法与 `REALTIME_SOURCE_PRIORITY`
    中的配置项一一对应，使该配置键对新旧两条实时行情链路含义一致。
    """
    from data_provider.realtime.akshare_source import AkshareRealtimeSource
    from data_provider.realtime.tickflow_source import TickflowRealtimeSource

    return {
        "tickflow": TickflowRealtimeSource(),
        "tencent": AkshareRealtimeSource(market_source="tencent", source_id="tencent"),
        "akshare_sina": AkshareRealtimeSource(market_source="sina", source_id="akshare_sina"),
        "akshare_em": AkshareRealtimeSource(market_source="em", source_id="akshare_em"),
    }


_MANAGER = RealtimeDataSourceManager(
    sources=_build_sources(),
    default_source_order=DEFAULT_SOURCE_ORDER,
    data_source_key="realtime_data_source",
    source_priority_key="realtime_source_priority",
    fallback_enabled_key="realtime_fallback_enabled",
    cache_ttl_seconds=5,
    health_cooldown_seconds=5,
)


def get_realtime_quote(stock_code: str) -> UnifiedRealtimeQuote:
    """按配置顺序获取实时行情。"""
    return _MANAGER.get_realtime_quote(stock_code)


def resolve_realtime_source_order() -> Iterable[str]:
    """返回当前配置生效的实时行情 source 顺序。"""
    return _MANAGER.resolve_source_order()
