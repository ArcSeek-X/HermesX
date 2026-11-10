#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票索引的规范排序规则（单一事实来源）。

排序规则（与 README §2.4 一致）：
1. 顶层市场分组：A股（CN / BSE 合并为一组）→ HK → US → JP → KR。
2. A股内部交易所：上海 SH → 深圳 SZ → 北京 / 北交所 BJ（按 ``canonicalCode`` 后缀判定）。
3. 每个市场 / 交易所分组内，按上市日期 ``list_date`` 从早到晚升序；无日期 / 非法日期排到分组末尾。

``reorder_stock_index.py``（按需纯重排）与 ``merge_stock_index_from_csv.py``（合并后自动重排）
都调用本模块，保证两者的排序结果完全一致。
"""

from datetime import datetime
from typing import List, Sequence, Tuple

# 顶层市场分组顺序：A股把 CN / BSE 合并为一组，组内再按交易所细分。
GROUP_ORDER = {"A": 0, "HK": 1, "US": 2, "JP": 3, "KR": 4}

# A股内部交易所顺序（按 canonicalCode 后缀判定）。
EXCHANGE_ORDER = {"SH": 0, "SZ": 1, "BJ": 2}

MARKET_COLUMN = 6
LIST_DATE_COLUMN = 10


def top_group(market: str) -> int:
    """返回顶层市场分组下标；A股（CN / BSE）归为一组，未知市场排到所有已知分组之后。"""
    if market in ("CN", "BSE"):
        return GROUP_ORDER["A"]
    return GROUP_ORDER.get(market, 9)


def exchange_rank(code: str) -> int:
    """A股内部交易所下标（SH / SZ / BJ）；未知后缀排到末尾。"""
    suffix = code.rsplit(".", 1)[-1].upper() if "." in code else ""
    return EXCHANGE_ORDER.get(suffix, 9)


def date_key(value) -> datetime:
    """上市日期排序键；空值 / 非法值视为「最晚」，排到分组末尾。"""
    text = "" if value is None else str(value).strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return datetime.max


def sort_key(record: Sequence) -> Tuple[int, int, datetime, str]:
    """返回一条记录在规范排序中的位置键。

    键结构：``(顶层分组, A股交易所排名, 上市日期, 代码)``。最后以代码作稳定 tie-breaker，
    保证排序完全确定（相同市场 / 交易所 / 日期的记录不再依赖输入顺序）。
    """
    market = record[MARKET_COLUMN] if len(record) > MARKET_COLUMN else ""
    is_a_share = market in ("CN", "BSE")
    group = 0 if is_a_share else top_group(market)
    exchange = exchange_rank(record[0]) if is_a_share else 0
    list_date = record[LIST_DATE_COLUMN] if len(record) > LIST_DATE_COLUMN else ""
    code = record[0] if len(record) > 0 else ""
    return (group, exchange, date_key(list_date), code)


def sort_records(records: Sequence[Sequence]) -> List[List]:
    """返回按规范排序后的新列表（不修改入参）。"""
    return sorted((list(r) for r in records), key=sort_key)
