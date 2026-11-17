# -*- coding: utf-8 -*-
"""stock-sdk（腾讯行情）全市场快照：股票度量视图的兜底数据源。

定位：东财 push2 clist 按源 IP 限流或被服务端静默断连时，度量视图会整批拿不到
数据（三个市场全空）。本模块走仓库既有的 StockSDK Node 桥接（`stock-sdk` 的
``batch.cn/hk/us``，实测数据源为腾讯 ``qt.gtimg.cn``），与东财不是同一条链路，
可作为兜底把「整页空白」降级为「部分列缺失」。

字段口径与东财 clist 的差异（缺口按契约置 None，不估算、不填 0）：
- 缺 ``epsDiluted`` / ``dividendYieldPct`` / ``industry`` / ``roePct`` /
  ``psRatioTTM`` / ``revenueGrowthYoyPct``：stock-sdk 全市场批量不提供；
- ``relativeVolume``（量比）仅 cn 有，hk / us 为 None；
- ``peRatioTTM`` / ``pbRatio`` 仅 cn / us 有，hk 为 None；
- ``totalMarketCap`` 上游以「亿元」返回，本模块换算成「元」，与东财 ``f20`` 对齐。

缓存语义与东财源保持一致：按市场 TTL 缓存 + 按市场细粒度锁防击穿 +
回源失败沿用最近一次成功快照（stale-while-error），并随缓存保存该批数据的抓取
时刻，不用「当前时刻」冒充数据新鲜度。
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from data_provider.clients.stocksdk.bridge import StockSdkBridgeError, get_stocksdk_client

logger = logging.getLogger("data_provider.stocksdk_metric_snapshot")

_SUPPORTED_MARKETS = ("cn", "hk", "us")

# 兜底源同样按市场缓存：全市场抓取要拉起 Node 子进程并序列化上万行，
# 分钟级复用可避免翻页 / 排序 / 切市场时反复付出该成本。
_SNAPSHOT_TTL_SECONDS = 180.0
# 缓存值 = (写入时的 monotonic 秒, 该批数据抓取时刻 ISO 8601(UTC), 行副本)。
_SNAPSHOT_CACHE: Dict[str, Tuple[float, str, List[Dict[str, Any]]]] = {}
_SNAPSHOT_CACHE_LOCK = threading.Lock()
_SNAPSHOT_REFRESH_LOCKS: Dict[str, threading.Lock] = {}

# stock-sdk 的 totalMarketCap 以「亿元」交付，度量视图契约按「元」（与东财 f20 对齐）
_YI_TO_YUAN = 100_000_000.0
# 美股交易所后缀：stock-sdk 输出形如 ``AAPL.OQ``。只剥离已知交易所后缀，
# ``BRK.A`` 这类股票类别后缀不在集合内，避免把代码本身截断。
_US_EXCHANGE_SUFFIXES = frozenset(
    {"OQ", "N", "AM", "PK", "OB", "OBB", "NYSE", "NASDAQ", "AMEX", "OTC"}
)


def _to_float(value: Any) -> Optional[float]:
    """把上游数值转为 float；None / 空串 / 非法值返回 None。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_us_code(code: str) -> str:
    """剥离美股交易所后缀（``AAPL.OQ`` -> ``AAPL``），与东财 clist 的 f12 口径对齐。"""
    if "." not in code:
        return code
    head, _, tail = code.rpartition(".")
    if tail in _US_EXCHANGE_SUFFIXES:
        return head
    return code


def _map_row(raw: Dict[str, Any], market: str) -> Optional[Dict[str, Any]]:
    """把 stock-sdk 精简行映射为度量视图行；无有效价格的标的不进结果集。"""
    code = str(raw.get("code") or "").strip()
    name = str(raw.get("name") or "").strip()
    price = _to_float(raw.get("price"))
    if not code or not name or price is None or price <= 0:
        return None
    if market == "us":
        code = _normalize_us_code(code)

    cap_yi = _to_float(raw.get("totalMarketCapYi"))
    # 上游真实数据源（stock-sdk 实测 cn / hk / us 均为 tencent）；缺失时退化为接入方标识
    source = str(raw.get("source") or "").strip().lower() or "stocksdk"
    return {
        "market": market,
        "code": code,
        "name": name,
        "source": source,
        "price": price,
        "changePct": _to_float(raw.get("changePct")),
        "volume": _to_float(raw.get("volume")),
        "relativeVolume": _to_float(raw.get("relativeVolume")),
        "totalMarketCap": cap_yi * _YI_TO_YUAN if cap_yi is not None else None,
        "peRatioTTM": _to_float(raw.get("peRatioTTM")),
        "epsDiluted": None,
        "dividendYieldPct": None,
        "industry": None,
        "roePct": None,
        "pbRatio": _to_float(raw.get("pbRatio")),
        "psRatioTTM": None,
        "revenueGrowthYoyPct": None,
    }


def _clone_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """返回行副本，避免服务层 join / 排序改写缓存内的 dict。"""
    return [dict(row) for row in rows]


def _load_snapshot(market: str) -> Optional[List[Dict[str, Any]]]:
    """实际回源拉取并映射该市场全市场快照（无缓存）；不可用或失败返回 None。"""
    client = get_stocksdk_client()
    if not client.is_available():
        logger.info("[stock-sdk快照] 数据源未启用或 Node 运行时不可用，跳过市场 %s", market)
        return None
    try:
        raw_rows = client.fetch_market_snapshot(market)
    except StockSdkBridgeError as exc:
        logger.info("[stock-sdk快照] 市场 %s 拉取失败，已按降级处理: %s", market, exc)
        return None
    rows = [row for row in (_map_row(raw, market) for raw in raw_rows) if row is not None]
    if not rows:
        return None
    logger.info("[stock-sdk快照] 市场 %s 快照完成: %d 只", market, len(rows))
    return rows


def fetch_stocksdk_metric_snapshot(
    market: str, *, force_refresh: bool = False
) -> Optional[Tuple[List[Dict[str, Any]], str]]:
    """按市场拉取全市场度量快照，返回 ``(rows, fetched_at)``。

    与东财快照端口同构：同市场结果在 TTL 内复用；按市场细粒度锁避免并发击穿；
    回源失败沿用最近一次成功快照并回传它自己的抓取时刻；全无缓存才返回 None
    （调用方降级跳过，不抛异常）。始终返回行副本，服务层可安全改写。
    """
    if market not in _SUPPORTED_MARKETS:
        logger.warning("[stock-sdk快照] 不支持的市场: %s", market)
        return None

    request_start = time.monotonic()
    with _SNAPSHOT_CACHE_LOCK:
        cached = _SNAPSHOT_CACHE.get(market)
        refresh_lock = _SNAPSHOT_REFRESH_LOCKS.setdefault(market, threading.Lock())

    if not force_refresh and cached and time.monotonic() - cached[0] < _SNAPSHOT_TTL_SECONDS:
        return _clone_rows(cached[2]), cached[1]

    with refresh_lock:
        with _SNAPSHOT_CACHE_LOCK:
            cached = _SNAPSHOT_CACHE.get(market)
        # 强制刷新时只复用「等待锁期间其他线程刚回源」的新快照，避免重复打源
        if (
            cached
            and (not force_refresh or cached[0] >= request_start)
            and time.monotonic() - cached[0] < _SNAPSHOT_TTL_SECONDS
        ):
            return _clone_rows(cached[2]), cached[1]

        rows = _load_snapshot(market)
        if rows:
            fetched_at = datetime.now(timezone.utc).isoformat()
            with _SNAPSHOT_CACHE_LOCK:
                _SNAPSHOT_CACHE[market] = (time.monotonic(), fetched_at, _clone_rows(rows))
            return rows, fetched_at
        # 回源失败：有旧快照就用旧快照，并沿用它自己的抓取时刻，避免整页空白
        if cached:
            logger.info("[stock-sdk快照] 市场 %s 回源失败，沿用最近一次快照", market)
            return _clone_rows(cached[2]), cached[1]
    return None


__all__ = ["fetch_stocksdk_metric_snapshot"]
