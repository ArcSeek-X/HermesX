# -*- coding: utf-8 -*-
"""东方财富全市场行情快照（直连 push2 clist）。

定位：尾盘选股（EOD Picker）stage-1 的首选数据源，与 ``tencent_quote_snapshot.py``
对等——两者都是独立快照模块，**不继承** ``BaseFetcher``、不参与
``DataFetcherManager`` 回退链，仅由 现有 MarketSnapshotPort 适配与应用层选股用例调用。

为什么直连 clist：
- 复用东方财富全市场快照接口 ``https://push2.eastmoney.com/api/qt/clist/get``，
  与 akshare ``ak.stock_zh_a_spot_em()`` 同源同语义，字段覆盖尾盘选股基础过滤所需的
  全部指标（最新价 / 涨跌幅 / 量比 / 换手率 / 流通市值 / 成交额）；
- 绕开 ``AkshareFetcher._enforce_rate_limit()`` 每次请求前的 2~5s 随机休眠。

分页实现要点（关键，曾因页大小踩坑）：
- 东财 clist 的 ``pz``（页大小）**服务端硬上限为 100**，请求更大也只回 100，
  因此固定按 100 翻页，并依据首页返回的 ``data.total`` 计算总页数；
- 排序用 ``fid=f12``（按代码），代码当日不变，翻页边界稳定，**可安全并行拉取**
  （若按涨跌幅 f3 排序，盘中价格变动会导致页边界漂移、重复/漏股）；
- 第 2..N 页用线程池并行拉取后按「代码」去重（防御性），第 1 页失败即整体返回
  None（交由调用方回退腾讯 / 东财 akshare），其余页失败仅记日志、跳过该页。

休市日返回最近一个交易日的收盘数据，尾盘选股在休市日也能以上一交易日为基准运行。

返回列与 ``tencent_quote_snapshot.py`` 完全一致，可直接喂给 EOD 基础过滤：
成交量=手，成交额=元，流通市值=元（``eod_picker_service._normalize_cmv`` 会按量级
归一化到亿元，兼容腾讯的「亿元」口径）。
"""

from __future__ import annotations

import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger("data_provider.eastmoney_quote_snapshot")

_CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
# 全 A 股（深主板 / 深创业板 / 沪主板 / 科创板 / 北交所），与 akshare stock_zh_a_spot_em 的 fs 一致
_FS = "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048"
# 只取快照所需字段：f2 最新价 f3 涨跌幅 f5 成交量 f6 成交额 f8 换手率 f10 量比
# f12 代码 f14 名称 f15 最高 f16 最低 f17 今开 f18 昨收 f21 流通市值
_FIELDS = "f2,f3,f5,f6,f8,f10,f12,f14,f15,f16,f17,f18,f21"
_UT = "fa5fd1943c7b386f172d6893dbfba10b"
# 东财 clist 页大小服务端硬上限为 100，写更大也会被压到 100
_PAGE_SIZE = 100
# clist 位于 push2，限流比 push2his（trends2）宽松；适度并行加速全市场翻页
_MAX_WORKERS = 6
_PAGE_RETRIES = 2
_TIMEOUT = 15
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 输出列契约，与 tencent_quote_snapshot.py 完全一致（drop-in 对等）
_COLUMNS = [
    "代码",
    "名称",
    "最新价",
    "涨跌幅",
    "量比",
    "换手率",
    "流通市值",
    "成交额",
    "成交量",
    "昨收",
    "今开",
    "最高",
    "最低",
]

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": _USER_AGENT, "Referer": "https://quote.eastmoney.com/"})


def _to_float(value: Any) -> Optional[float]:
    """东财 clist 数值字段转 float；停牌 / 空 / '-' 返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    try:
        f = float(text)
        return f if pd.notna(f) else None
    except (TypeError, ValueError):
        return None


def _parse_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """解析 clist 单只股票（f-field 字典）为快照行。"""
    code = str(item.get("f12") or "").strip()
    name = str(item.get("f14") or "").strip()
    price = _to_float(item.get("f2"))
    if not code or not name or price is None or price <= 0:
        return None
    return {
        "代码": code,
        "名称": name,
        "最新价": price,
        "涨跌幅": _to_float(item.get("f3")),
        "量比": _to_float(item.get("f10")),
        "换手率": _to_float(item.get("f8")),
        "流通市值": _to_float(item.get("f21")),  # 元
        "成交额": _to_float(item.get("f6")),  # 元
        "成交量": _to_float(item.get("f5")),  # 手
        "昨收": _to_float(item.get("f18")),
        "今开": _to_float(item.get("f17")),
        "最高": _to_float(item.get("f15")),
        "最低": _to_float(item.get("f16")),
    }


def _fetch_page(page: int, page_size: int) -> Dict[str, Any]:
    """拉取一页 clist 数据，返回原始 JSON（网络异常 / 限流由上层重试）。

    按代码（fid=f12）排序以保证翻页边界稳定，支持并行拉取。
    """
    resp = _SESSION.get(
        _CLIST_URL,
        params={
            "pn": page,
            "pz": page_size,
            "po": "1",
            "np": "1",
            "ut": _UT,
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": _FS,
            "fields": _FIELDS,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_page(payload: Dict[str, Any]) -> "tuple[List[Dict[str, Any]], Optional[int]]":
    """解析一页 payload，返回 (行列表, total)。total 缺失时为 None。"""
    data = payload.get("data") or {}
    diff = data.get("diff") or []
    rows: List[Dict[str, Any]] = []
    for item in diff:
        row = _parse_item(item)
        if row:
            rows.append(row)
    total = _to_float(data.get("total"))
    return rows, (int(total) if total is not None else None)


def _fetch_page_rows(page: int, page_size: int) -> List[Dict[str, Any]]:
    """带重试地拉取并解析一页；连续失败返回空列表（由调用方决定如何降级）。"""
    last_exc: Optional[Exception] = None
    for attempt in range(_PAGE_RETRIES):
        try:
            return _parse_page(_fetch_page(page, page_size))[0]
        except Exception as exc:  # pragma: no cover - 网络 / 限流兜底
            last_exc = exc
            if attempt < _PAGE_RETRIES - 1:
                time.sleep(0.5)
    logger.info("[东财clist] 第 %d 页拉取失败: %s", page, last_exc)
    return []


def fetch_eastmoney_market_snapshot(
    page_size: int = _PAGE_SIZE, max_workers: int = _MAX_WORKERS
) -> Optional[pd.DataFrame]:
    """返回全市场 A 股实时快照 DataFrame；失败或无数据返回 None。

    先取第 1 页拿到 ``total``，据 ``ceil(total/page_size)`` 计算总页数，再把第
    2..N 页并行拉取；按代码排序保证翻页边界稳定，最后按「代码」去重。第 1 页失败
    整体返回 None（回退腾讯 / 东财 akshare），其余页失败仅跳过该页。
    """
    # 东财 clist 每页上限 100（请求更大也被压到 100）。先收敛页大小，保证据 total
    # 计算出的翻页数与「实际每页条数」一致——否则请求 500 只回 100 时会少翻页，
    # 又退回「只取到第 1 页」的老 bug（曾导致尾盘选股 0 结果）。
    page_size = min(page_size, _PAGE_SIZE)
    # 第 1 页：既拿数据也拿 total
    try:
        rows, total = _parse_page(_fetch_page(1, page_size))
    except Exception as exc:  # pragma: no cover - 网络 / 限流兜底
        logger.info("[东财clist] 第 1 页拉取失败: %s", exc)
        return None
    if not rows:
        return None
    if total is None or total <= len(rows):
        return pd.DataFrame(rows, columns=_COLUMNS)

    num_pages = math.ceil(total / page_size)
    if num_pages > 1:
        workers = max(1, min(max_workers, num_pages - 1))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for page_rows in ex.map(lambda pn: _fetch_page_rows(pn, page_size), range(2, num_pages + 1)):
                rows.extend(page_rows)

    # 防御性去重（按代码）；正常情况下稳定排序不会有重复
    seen = set()
    unique: List[Dict[str, Any]] = []
    for r in rows:
        code = r.get("代码")
        if code and code not in seen:
            seen.add(code)
            unique.append(r)
    logger.info("[东财clist] 全市场快照: %d 只", len(unique))
    return pd.DataFrame(unique, columns=_COLUMNS)


# === 股票度量视图（stock_metric）：三市场 clist 快照 ===
# 在既有 _FS / _FIELDS 之外新增，避免影响尾盘选股等既有调用方。
_FS_BY_MARKET: Dict[str, str] = {
    "cn": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
    "hk": "m:128 t:3,m:128 t:4,m:128 t:1,m:128 t:2",
    "us": "m:105,m:106,m:107",
}
# 度量视图标准字段（camelCase）-> 东财 clist f-id 映射（13 列 + 额外可筛字段）
_METRIC_FIELD_MAP: Dict[str, str] = {
    "f2": "price",
    "f3": "changePct",
    "f5": "volume",
    "f10": "relativeVolume",
    "f12": "code",
    "f14": "name",
    "f20": "totalMarketCap",
    "f23": "pbRatio",
    "f37": "roePct",
    "f100": "industry",
    "f112": "epsDiluted",
    "f115": "peRatioTTM",
    "f130": "psRatioTTM",
    "f133": "dividendYieldPct",
}
_METRIC_FIELDS = ",".join(_METRIC_FIELD_MAP.keys())


def _fetch_metric_page(market: str, page: int, page_size: int) -> Optional[Dict[str, Any]]:
    """拉取指定市场第 page 页 clist 原始 payload（与 _fetch_page 同构，但 fs/fields 可变）。"""
    fs = _FS_BY_MARKET[market]
    try:
        resp = _SESSION.get(
            _CLIST_URL,
            params={
                "pn": page,
                "pz": page_size,
                "po": 1,
                "np": 1,
                "ut": _UT,
                "fltt": 2,
                "invt": 2,
                "fid": "f12",
                "fs": fs,
                "fields": _METRIC_FIELDS,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # pragma: no cover - 网络 / 限流兜底
        logger.info("[东财clist] 市场 %s 第 %d 页失败: %s", market, page, exc)
        return None


def _parse_metric_item(item: Dict[str, Any], market: str) -> Optional[Dict[str, Any]]:
    code = str(item.get("f12") or "").strip()
    name = str(item.get("f14") or "").strip()
    price = _to_float(item.get("f2"))
    if not code or not name or price is None or price <= 0:
        return None
    row: Dict[str, Any] = {"market": market, "code": code, "name": name}
    for fid, field in _METRIC_FIELD_MAP.items():
        if fid in ("f12", "f14"):
            continue
        raw = item.get(fid)
        if field == "industry":
            row[field] = str(raw).strip() if raw not in (None, "", "-") else None
        else:
            row[field] = _to_float(raw)
    return row


def _collect_metric_rows(payload: Dict[str, Any], market: str) -> List[Dict[str, Any]]:
    data = payload.get("data") or {}
    diff = data.get("diff") or []
    rows: List[Dict[str, Any]] = []
    for item in diff:
        row = _parse_metric_item(item, market)
        if row is not None:
            rows.append(row)
    return rows


def _dedup_metric_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique: List[Dict[str, Any]] = []
    for r in rows:
        key = f"{r['market']}:{r['code']}"
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# 度量视图快照 TTL 缓存：翻页 / 排序 / 切市场复用同一次全市场抓取，
# 避免每次查询都对东财发起 50+ 页请求（既慢又容易触发限流）。
_METRIC_SNAPSHOT_TTL_SECONDS = 20.0
# 缓存值 = (写入时的 monotonic 秒, 该批数据抓取时刻 ISO 8601(UTC), 行副本)。
# monotonic 只用于 TTL 比较、无法换算墙钟时间，因此抓取时刻随缓存一起保存：
# 命中缓存 / 回源失败沿用旧快照时都回传它，不用「当前时刻」冒充数据新鲜度。
_METRIC_SNAPSHOT_CACHE: Dict[str, Tuple[float, str, List[Dict[str, Any]]]] = {}
_METRIC_SNAPSHOT_CACHE_LOCK = threading.Lock()
_METRIC_SNAPSHOT_REFRESH_LOCKS: Dict[str, threading.Lock] = {}


def _clone_metric_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """返回行副本，避免服务层 join / 排序改写缓存内的 dict。"""
    return [dict(row) for row in rows]


def _load_metric_snapshot(market: str, page_size: int, max_workers: int) -> Optional[List[Dict[str, Any]]]:
    """实际回源拉取并解析全市场快照（无缓存）。"""
    payload = _fetch_metric_page(market, 1, page_size)
    if payload is None:
        return None
    rows = _collect_metric_rows(payload, market)
    if not rows:
        return None
    total = (payload.get("data") or {}).get("total")
    if total is None or total <= len(rows):
        return _dedup_metric_rows(rows)
    num_pages = math.ceil(total / page_size)
    if num_pages > 1:
        workers = max(1, min(max_workers, num_pages - 1))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for page_payload in ex.map(
                lambda pn: _fetch_metric_page(market, pn, page_size), range(2, num_pages + 1)
            ):
                if page_payload is None:
                    continue
                rows.extend(_collect_metric_rows(page_payload, market))
    return _dedup_metric_rows(rows)


def fetch_eastmoney_clist_snapshot(
    market: str,
    page_size: int = _PAGE_SIZE,
    max_workers: int = _MAX_WORKERS,
    force_refresh: bool = False,
) -> Optional[Tuple[List[Dict[str, Any]], str]]:
    """按市场拉取全市场股票度量快照，并回传本批数据的抓取时刻。

    返回 ``(rows, fetched_at)``：``fetched_at`` 是本批数据写入缓存的时刻，ISO 8601
    且带 UTC 偏移（``+00:00``），前端可 ``new Date()`` 解析后按本地时区展示。
    同市场结果在 ``_METRIC_SNAPSHOT_TTL_SECONDS`` 内复用；按市场的细粒度锁避免并发
    缓存击穿；回源失败时沿用最近一次成功快照（stale-while-error）。命中缓存与沿用
    旧快照两种情况都返回该批缓存自己的抓取时刻，不伪造当前时刻；全无缓存才返回
    None（调用方降级跳过，不抛异常）。始终返回行副本，服务层可安全改写。
    """
    if market not in _FS_BY_MARKET:
        logger.warning("[东财clist] 不支持的市场: %s", market)
        return None
    page_size = min(page_size, _PAGE_SIZE)
    request_start = time.monotonic()

    with _METRIC_SNAPSHOT_CACHE_LOCK:
        cached = _METRIC_SNAPSHOT_CACHE.get(market)
        refresh_lock = _METRIC_SNAPSHOT_REFRESH_LOCKS.setdefault(market, threading.Lock())

    if not force_refresh and cached and time.monotonic() - cached[0] < _METRIC_SNAPSHOT_TTL_SECONDS:
        return _clone_metric_rows(cached[2]), cached[1]

    with refresh_lock:
        with _METRIC_SNAPSHOT_CACHE_LOCK:
            cached = _METRIC_SNAPSHOT_CACHE.get(market)
        # 强制刷新时只复用「等待锁期间其他线程刚回源」的新快照，避免重复打源
        if (
            cached
            and (not force_refresh or cached[0] >= request_start)
            and time.monotonic() - cached[0] < _METRIC_SNAPSHOT_TTL_SECONDS
        ):
            return _clone_metric_rows(cached[2]), cached[1]
        rows = _load_metric_snapshot(market, page_size, max_workers)
        if rows:
            # 抓取完成 / 落缓存的墙钟时刻；与 TTL 用的 monotonic 分开记录
            fetched_at = datetime.now(timezone.utc).isoformat()
            with _METRIC_SNAPSHOT_CACHE_LOCK:
                _METRIC_SNAPSHOT_CACHE[market] = (
                    time.monotonic(), fetched_at, _clone_metric_rows(rows)
                )
            return rows, fetched_at
        # 回源失败：有旧快照就用旧快照，并沿用它自己的抓取时刻，避免整页空白
        if cached:
            logger.info("[东财clist] 市场 %s 回源失败，沿用最近一次快照", market)
            return _clone_metric_rows(cached[2]), cached[1]
    return None
