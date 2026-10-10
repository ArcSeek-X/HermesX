# -*- coding: utf-8 -*-
"""
===================================
市场总览卡片聚合 source
===================================

职责：
1. 将 `/market/index` 页面所需的多源行情与统计接口收敛为统一 `cards[]` 契约。
2. 对外暴露 `market=a|hk-us|jp-kr` 三个 TAB 的标准卡片列表。
3. 复用既有 sector source，不在 endpoint 层拼装业务卡片数据。

性能约定（/market/index 首屏要求 1 秒内渲染）：
1. 聚合层对最终 `market/cards` 结果做 stale-while-revalidate 缓存：
   新鲜期内直接返回缓存；过期后先返回旧值并后台异步刷新，避免用户空等上游。
2. 单次构建内部各数据源并发取数，总耗时由「串行累加」变为「取最慢者」。
3. 每个数据源都有等待预算，超预算即降级；对反复超时的 StockSDK 板块源做退避，
   避免每轮都白等其超时（该源失败时不写缓存，原实现会每次重试至超时）。
4. 最强板块卡片 payload 允许为 null（前端 `BoardListItem | null` 契约），
   因此它可以安全降级而不影响其余卡片渲染。
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Any, Callable, Dict, List, Optional, Set

from data_provider.sector.eastmoney_source import (
    get_cached_board_list as get_cached_board_list_from_eastmoney,
    get_cached_market_fund_flow as get_cached_market_fund_flow_from_eastmoney,
    get_cached_market_indices as get_cached_market_indices_from_eastmoney,
    get_cached_market_overview as get_cached_market_overview_from_eastmoney,
    get_cached_northbound_flow as get_cached_northbound_flow_from_eastmoney,
)
from data_provider.sector.shidaotec_source import get_board_card_list as get_board_card_list_from_shidaotec
from data_provider.sector.stocksdk_source import (
    get_cached_board_list as get_cached_board_list_from_stocksdk,
    get_cached_market_fund_flow as get_cached_market_fund_flow_from_stocksdk,
    get_cached_market_indices as get_cached_market_indices_from_stocksdk,
    get_cached_market_overview as get_cached_market_overview_from_stocksdk,
    get_cached_northbound_flow as get_cached_northbound_flow_from_stocksdk,
)

logger = logging.getLogger(__name__)

MARKET_TAB_KEYS = ("a", "hk-us", "jp-kr")
_INDEX_MARKET_MAPPING = {
    "a": "a",
    "hk-us": "us",
    "jp-kr": "jp-kr",
}

# ===========================================================================
# 并发与缓存基础设施
# ===========================================================================

# 卡片构建专用线程池：各数据源并发取数，避免串行累加耗时。
_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="market-cards")

# 聚合结果缓存：market -> {"payload": {...}, "timestamp": float}
_PAYLOAD_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()

# 新鲜期：命中即直接返回，完全不触碰上游（决定稳态响应耗时）。
_CACHE_FRESH_TTL = 20.0
# 陈旧可用期：过期但仍在窗口内时，先返回旧值并触发后台刷新。
_CACHE_STALE_TTL = 900.0

# 单次构建的总体等待预算（秒）。所有数据源并发等待、整体超时，
# 因此冷启动耗时有确定上限，不会随数据源数量累加。
_BUILD_BUDGET = 4.0

# 后台刷新在途标记：同一 market 合并刷新，避免并发请求重复打上游。
_REFRESH_INFLIGHT_TTL = 60.0
_REFRESH_LOCK = threading.Lock()
_REFRESHING: Dict[str, float] = {}

# StockSDK 板块源失败/超时后的退避时长（秒），退避期内直连东财/神策。
_BOARD_STOCKSDK_BACKOFF_TTL = 180.0
_BOARD_BACKOFF_LOCK = threading.Lock()
_BOARD_BACKOFF_UNTIL = 0.0


def get_market_cards(market: str) -> Optional[Dict[str, Any]]:
    """按前端 TAB key 返回统一卡片列表（stale-while-revalidate）。"""
    normalized_market = str(market or "").strip().lower()
    if normalized_market not in MARKET_TAB_KEYS:
        return None

    entry = _read_cache(normalized_market)
    if entry is not None:
        age = time.time() - float(entry["timestamp"])
        if age <= _CACHE_FRESH_TTL:
            return entry["payload"]
        if age <= _CACHE_STALE_TTL:
            # 过期但仍可用：立即回旧值，后台刷新，用户不必空等上游。
            _schedule_refresh(normalized_market)
            return entry["payload"]

    payload = _build_payload(normalized_market)
    # 空结果不入缓存，避免把一次上游故障固化成长期空卡片。
    if payload.get("cards"):
        _write_cache(normalized_market, payload)
    return payload


def warm_market_cards_cache() -> None:
    """预热全部 TAB 的卡片缓存。

    供服务启动后后台调用，让首个页面请求即可命中新鲜缓存。
    预热失败不影响服务启动，仅记录告警。
    """
    for market in MARKET_TAB_KEYS:
        try:
            payload = _build_payload(market)
            if payload.get("cards"):
                _write_cache(market, payload)
                logger.info(
                    "[market-cards] 预热完成: market=%s cards=%d",
                    market,
                    len(payload["cards"]),
                )
        except Exception as exc:  # noqa: BLE001 - 预热需 best-effort
            logger.warning("[market-cards] 预热失败: market=%s error=%s", market, exc)


def _build_payload(market: str) -> Dict[str, Any]:
    if market == "a":
        cards = _build_a_market_cards()
    else:
        cards = _build_index_cards_for_market(market)
    return {"market": market, "cards": cards}


# ---------------------------------------------------------------------------
# 缓存读写与后台刷新
# ---------------------------------------------------------------------------


def _read_cache(market: str) -> Optional[Dict[str, Any]]:
    with _CACHE_LOCK:
        entry = _PAYLOAD_CACHE.get(market)
        if entry is None:
            return None
        return {"payload": entry["payload"], "timestamp": entry["timestamp"]}


def _write_cache(market: str, payload: Dict[str, Any]) -> None:
    with _CACHE_LOCK:
        _PAYLOAD_CACHE[market] = {"payload": payload, "timestamp": time.time()}


def _schedule_refresh(market: str) -> None:
    """在线程池中异步刷新指定 market 的缓存（同 market 合并）。"""
    with _REFRESH_LOCK:
        started_at = _REFRESHING.get(market, 0.0)
        if time.time() - started_at < _REFRESH_INFLIGHT_TTL:
            return
        _REFRESHING[market] = time.time()
    try:
        _EXECUTOR.submit(_refresh_cache_entry, market)
    except RuntimeError as exc:
        logger.warning("[market-cards] 调度后台刷新失败: market=%s error=%s", market, exc)
        with _REFRESH_LOCK:
            _REFRESHING.pop(market, None)


def _refresh_cache_entry(market: str) -> None:
    try:
        payload = _build_payload(market)
        if payload.get("cards"):
            _write_cache(market, payload)
    except Exception as exc:  # noqa: BLE001 - 后台刷新失败不影响前台响应
        logger.warning("[market-cards] 后台刷新失败: market=%s error=%s", market, exc)
    finally:
        with _REFRESH_LOCK:
            _REFRESHING.pop(market, None)


# ---------------------------------------------------------------------------
# 并发取数与降级
# ---------------------------------------------------------------------------


def _await_all(futures: Dict[str, Future], labels: Dict[str, str]) -> Set[Future]:
    """并发等待全部数据源，整体最多等 `_BUILD_BUDGET` 秒。

    未在预算内完成的 future 不取消：它们继续在后台跑完并回填上游 source
    自身的缓存，因此下一轮可直接命中，不必重复支付上游超时成本。
    """
    done, not_done = wait(list(futures.values()), timeout=_BUILD_BUDGET)
    for key, future in futures.items():
        if future in not_done:
            logger.warning(
                "[market-cards] %s 在 %.1fs 总体预算内未完成，本轮降级",
                labels.get(key, key),
                _BUILD_BUDGET,
            )
    return done


def _grab(
    futures: Dict[str, Future],
    done: Set[Future],
    key: str,
    default: Any,
    label: str,
) -> Any:
    """取回已完成数据源的结果；未完成或异常时降级为 default。"""
    future = futures[key]
    if future not in done:
        return default
    try:
        result = future.result(timeout=0)
    except Exception as exc:  # noqa: BLE001 - 单源失败不拖垮整卡
        logger.warning("[market-cards] %s 取数异常: %s", label, exc)
        return default
    return result if result else default


def _build_a_market_cards() -> List[Dict[str, Any]]:
    futures = {
        "indices": _EXECUTOR.submit(_get_market_indices, "a"),
        "overview": _EXECUTOR.submit(_get_market_overview),
        "northbound": _EXECUTOR.submit(_get_northbound_flow),
        "fund_flow": _EXECUTOR.submit(_get_market_fund_flow),
        "board": _EXECUTOR.submit(_get_strongest_board),
    }
    labels = {
        "indices": "指数(a)",
        "overview": "市场概览",
        "northbound": "北向资金",
        "fund_flow": "大盘主力",
        "board": "最强板块",
    }
    done = _await_all(futures, labels)

    indices = _grab(futures, done, "indices", [], "指数(a)")
    overview = _grab(futures, done, "overview", {}, "市场概览")
    northbound = _grab(futures, done, "northbound", None, "北向资金")
    fund_flow = _grab(futures, done, "fund_flow", None, "大盘主力")
    strongest_board = _grab(futures, done, "board", None, "最强板块")
    if futures["board"] not in done:
        # 板块源未在预算内返回，进入退避，后续轮次直连东财/神策。
        _mark_board_stocksdk_backoff()

    cards = _build_index_quote_cards(indices or [])
    cards.extend(
        [
            {
                "cardType": "market_breadth",
                "cardKey": "market_breadth",
                "payload": {
                    "riseCount": int(overview.get("riseCount") or 0),
                    "fallCount": int(overview.get("fallCount") or 0),
                    "flatCount": int(overview.get("flatCount") or 0),
                },
            },
            {
                "cardType": "limit_up_down",
                "cardKey": "limit_up_down",
                "payload": {
                    "limitUpCount": int(overview.get("limitUpCount") or 0),
                    "limitDownCount": int(overview.get("limitDownCount") or 0),
                },
            },
            {
                "cardType": "total_amount",
                "cardKey": "total_amount",
                "payload": {
                    "totalAmount": float(overview.get("totalAmount") or 0),
                },
            },
            {
                "cardType": "northbound_flow",
                "cardKey": "northbound_flow",
                "payload": northbound or _build_empty_northbound_payload(),
            },
            {
                "cardType": "main_flow",
                "cardKey": "main_flow",
                "payload": fund_flow or _build_empty_main_flow_payload(),
            },
            {
                "cardType": "strongest_board",
                "cardKey": "strongest_board",
                "payload": strongest_board,
            },
        ]
    )
    return cards


def _build_index_cards_for_market(market: str) -> List[Dict[str, Any]]:
    futures = {"indices": _EXECUTOR.submit(_get_market_indices, market)}
    labels = {"indices": f"指数({market})"}
    done = _await_all(futures, labels)
    indices = _grab(futures, done, "indices", [], f"指数({market})")
    return _build_index_quote_cards(indices or [])


def _build_index_quote_cards(indices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    for index, item in enumerate(indices):
        code = str(item.get("code") or "").strip()
        cards.append(
            {
                "cardType": "index_quote",
                "cardKey": f"index_quote:{code or index}",
                "payload": item,
            }
        )
    return cards


# ---------------------------------------------------------------------------
# 数据源入口
# ---------------------------------------------------------------------------


def _get_market_indices(market: str) -> Optional[List[Dict[str, Any]]]:
    source_market = _INDEX_MARKET_MAPPING[market]
    return _prefer_loader_chain(
        lambda: get_cached_market_indices_from_stocksdk(source_market),
        lambda: get_cached_market_indices_from_eastmoney(source_market),
    )


def _get_market_overview() -> Optional[Dict[str, Any]]:
    return _prefer_loader_chain(
        get_cached_market_overview_from_stocksdk,
        get_cached_market_overview_from_eastmoney,
    )


def _get_northbound_flow() -> Optional[Dict[str, Any]]:
    return _prefer_loader_chain(
        get_cached_northbound_flow_from_stocksdk,
        get_cached_northbound_flow_from_eastmoney,
    )


def _get_market_fund_flow() -> Optional[Dict[str, Any]]:
    return _prefer_loader_chain(
        get_cached_market_fund_flow_from_stocksdk,
        get_cached_market_fund_flow_from_eastmoney,
    )


def _get_strongest_board() -> Optional[Dict[str, Any]]:
    """最强板块：StockSDK 优先，退避期内直连东财/神策。"""
    if not _is_board_stocksdk_in_backoff():
        boards = _try_board_loader(
            lambda: get_cached_board_list_from_stocksdk("industry"), "StockSDK"
        )
        if boards:
            return boards[0]
        _mark_board_stocksdk_backoff()

    boards = _try_board_loader(
        lambda: get_cached_board_list_from_eastmoney("industry"), "东方财富"
    )
    if boards:
        return boards[0]

    boards = _try_board_loader(
        lambda: get_board_card_list_from_shidaotec("industry"), "师大神策"
    )
    if boards:
        return boards[0]
    return None


def _try_board_loader(loader: Callable[[], Any], label: str) -> Optional[List[Dict[str, Any]]]:
    try:
        boards = loader()
    except Exception as exc:  # noqa: BLE001 - 板块源逐个降级
        logger.warning("[market-cards] 板块源失败: source=%s error=%s", label, exc)
        return None
    return boards or None


def _is_board_stocksdk_in_backoff() -> bool:
    with _BOARD_BACKOFF_LOCK:
        return time.time() < _BOARD_BACKOFF_UNTIL


def _mark_board_stocksdk_backoff() -> None:
    """标记 StockSDK 板块源进入退避，期间跳过以避免每轮白等其超时。"""
    global _BOARD_BACKOFF_UNTIL
    with _BOARD_BACKOFF_LOCK:
        _BOARD_BACKOFF_UNTIL = time.time() + _BOARD_STOCKSDK_BACKOFF_TTL
    logger.info(
        "[market-cards] StockSDK 板块源进入 %.0fs 退避，期间直连东财/神策",
        _BOARD_STOCKSDK_BACKOFF_TTL,
    )


def _build_empty_northbound_payload() -> Dict[str, Any]:
    return {
        "netInflow": None,
        "name": "北向资金",
        "date": None,
        "riseCount": None,
        "fallCount": None,
    }


def _build_empty_main_flow_payload() -> Dict[str, Any]:
    return {
        "mainNetInflow": None,
        "mainNetInflowPercent": None,
        "date": None,
    }


def _prefer_loader_chain(*loaders):
    """按顺序尝试多个 source，返回第一份非空数据。"""
    for loader in loaders:
        try:
            data = loader()
        except Exception as exc:  # noqa: BLE001 - provider 聚合层只做兜底
            logger.warning("[market-cards] source failed in fallback chain: %s", exc)
            data = None
        if data:
            return data
    return None
