# -*- coding: utf-8 -*-
"""东方财富全市场行情快照（直连 push2 clist）。

定位：尾盘选股（EOD Picker）stage-1 的首选数据源，与 ``tencent_quote_snapshot.py``
对等——两者都是独立快照模块，**不继承** ``BaseFetcher``、不参与
``DataFetcherManager`` 回退链，仅由 ``src/services/eod_picker_service.py`` 直接调用。

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
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

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
_SESSION.headers.update(
    {"User-Agent": _USER_AGENT, "Referer": "https://quote.eastmoney.com/"}
)


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
        "流通市值": _to_float(item.get("f21")),   # 元
        "成交额": _to_float(item.get("f6")),      # 元
        "成交量": _to_float(item.get("f5")),      # 手
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
            for page_rows in ex.map(
                lambda pn: _fetch_page_rows(pn, page_size), range(2, num_pages + 1)
            ):
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
