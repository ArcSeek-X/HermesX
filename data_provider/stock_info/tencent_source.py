# -*- coding: utf-8 -*-
"""
===================================
腾讯基础信息源（兜底）
===================================

东财在部分网络环境不可达时，作为 `stock_info` 能力的兜底源。
腾讯实时行情接口 `qt.gtimg.cn/q=<symbol>` 返回以 `~` 分隔的行情串，
关键字段下标已用贵州茅台 / 平安银行 / 湖北宜化等多只标的反查核对。

字段下标（0-based，按 ~ 切分）：
- 1  名称
- 2  代码
- 3  现价
- 4  昨收
- 5  今开
- 6  成交量（手）
- 31 涨跌
- 32 涨跌幅（%）
- 33 最高
- 34 最低
- 37 成交额（万元）
- 38 换手率（%）
- 43 振幅（%）
- 44 总市值（亿元）
- 52 市盈率(TTM)

统一输出语义（与东财源、`StockInfoHeader` 渲染约定一致）：
- volume 单位：股（`手 * 100`）
- amount 单位：元（`万元 * 10000`）
- total_market_cap 单位：元（`亿元 * 1e8`）
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

import requests

from data_provider.common.normalize import code_to_sina_symbol
from data_provider.stock_info.base import StockInfoResult, StockInfoSource

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 12
TENCENT_QUOTE_URL = "http://qt.gtimg.cn/q"
_USER_AGENT = "Mozilla/5.0"

# 关键字段下标（见模块 docstring）
_NAME_INDEX = 1
_PRICE_INDEX = 3
_PREV_CLOSE_INDEX = 4
_OPEN_INDEX = 5
_VOLUME_LOTS_INDEX = 6
_CHANGE_INDEX = 31
_CHANGE_PERCENT_INDEX = 32
_HIGH_INDEX = 33
_LOW_INDEX = 34
_AMOUNT_WAN_INDEX = 37
_TURNOVER_INDEX = 38
_AMPLITUDE_INDEX = 43
_MARKET_CAP_YI_INDEX = 44
_PE_TTM_INDEX = 52

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.proxies = {"http": None, "https": None}

# 解析所需的最少字段数（至少覆盖市盈率下标 52）
_MIN_FIELD_COUNT = 53


class TencentStockInfoSource(StockInfoSource):
    """腾讯实时行情兜底源（东财不可达时使用）。"""

    source_id = "tencent"

    def fetch(self, stock_code: str) -> Optional[StockInfoResult]:
        symbol = code_to_sina_symbol(stock_code)
        try:
            response = _SESSION.get(
                TENCENT_QUOTE_URL,
                params={"q": symbol},
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": _USER_AGENT},
            )
            response.raise_for_status()
            fields = _parse_fields(response.content)
        except Exception as exc:
            logger.warning("[TencentStockInfoSource] fetch failed: %s", exc)
            return None

        if len(fields) < _MIN_FIELD_COUNT:
            logger.warning(
                "[TencentStockInfoSource] unexpected payload for %s (fields=%d)",
                symbol,
                len(fields),
            )
            return None

        try:
            current_price = _to_float(fields[_PRICE_INDEX])
            if current_price is None:
                return None

            volume_lots = _to_float(fields[_VOLUME_LOTS_INDEX])
            amount_wan = _to_float(fields[_AMOUNT_WAN_INDEX])
            market_cap_yi = _to_float(fields[_MARKET_CAP_YI_INDEX])

            return StockInfoResult(
                stock_code=stock_code,
                stock_name=_normalize_name(fields[_NAME_INDEX]),
                current_price=current_price,
                change=_to_float(fields[_CHANGE_INDEX]),
                change_percent=_to_float(fields[_CHANGE_PERCENT_INDEX]),
                open=_to_float(fields[_OPEN_INDEX]),
                prev_close=_to_float(fields[_PREV_CLOSE_INDEX]),
                high=_to_float(fields[_HIGH_INDEX]),
                low=_to_float(fields[_LOW_INDEX]),
                volume=(volume_lots * 100) if volume_lots is not None else None,
                amount=(amount_wan * 10000) if amount_wan is not None else None,
                turnover_rate=_to_float(fields[_TURNOVER_INDEX]),
                amplitude=_to_float(fields[_AMPLITUDE_INDEX]),
                pe_ratio_ttm=_to_float(fields[_PE_TTM_INDEX]),
                total_market_cap=(market_cap_yi * 1e8) if market_cap_yi is not None else None,
                source=self.source_id,
            )
        except (ValueError, IndexError) as exc:
            logger.warning("[TencentStockInfoSource] parse failed for %s: %s", symbol, exc)
            return None


def _parse_fields(content: bytes) -> List[str]:
    """从腾讯行情响应（`v_sz000422="...";`）中提取 ~ 分隔字段列表。"""
    text = content.decode("gbk", errors="replace")
    match = re.search(r'="([^"]*)"', text)
    if not match:
        return []
    return match.group(1).split("~")


def _normalize_name(value: object) -> Optional[str]:
    if value in (None, "", "-"):
        return None
    return str(value).strip() or None


def _to_float(value: object) -> Optional[float]:
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None
