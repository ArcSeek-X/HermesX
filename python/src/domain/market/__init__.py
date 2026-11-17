# -*- coding: utf-8 -*-
"""市场领域包。

对外暴露跨层复用的市场结构与交易日规则（纯业务语义，无框架 / ORM / 存储 / IO 依赖）。
当前成员：

- :mod:`src.domain.market.market_symbol_utils`：后缀型离岸市场（jp / kr / tw）的
  Yahoo 代码后缀规则与归一化，供数据源、市场上下文、交易日历、股票索引加载与
  API 输入归一化复用。
"""

from __future__ import annotations

from src.domain.market.market_symbol_utils import (
    SuffixMarketSpec,
    get_suffix_market,
    is_jp_suffix_symbol,
    is_kr_suffix_symbol,
    is_suffix_market_symbol,
    is_tw_suffix_symbol,
    market_suffixes,
    normalize_suffix_market_symbol,
    split_suffix_symbol,
    suffix_base_lookup_allowed,
)

__all__ = [
    "SuffixMarketSpec",
    "get_suffix_market",
    "is_jp_suffix_symbol",
    "is_kr_suffix_symbol",
    "is_suffix_market_symbol",
    "is_tw_suffix_symbol",
    "market_suffixes",
    "normalize_suffix_market_symbol",
    "split_suffix_symbol",
    "suffix_base_lookup_allowed",
]
