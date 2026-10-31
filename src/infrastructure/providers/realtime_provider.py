# -*- coding: utf-8 -*-
"""实时行情适配器：把 ``data_provider`` 的实时行情契约转成应用端口形状。

``data_provider/`` 原位保留为数据源能力包（ADR-001），本适配器只做
``UnifiedRealtimeQuote`` dataclass -> 源字段字典的收敛，选源 / 回退 / 缓存仍由
``data_provider.realtime.base.get_realtime_quote`` 内部负责；应用层
（:class:`~src.application.quote.stock_service.StockService`）按
:class:`~src.application.quote.ports.RealtimeQuotePort` 协议调用，不感知数据源类型。

失败语义保持与原实现一致：所有数据源失败返回 ``None``；取数过程中的异常原样
上抛，由用例决定降级方式。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from data_provider.realtime.base import get_realtime_quote

# UnifiedRealtimeQuote 中被实时行情端点消费的字段（源字段名）。
_REALTIME_FIELDS = (
    "code",
    "name",
    "price",
    "change_amount",
    "change_pct",
    "open_price",
    "high",
    "low",
    "pre_close",
    "volume",
    "amount",
    "turnover_rate",
    "total_mv",
)


class DataProviderRealtimeQuoteProvider:
    """:class:`RealtimeQuotePort` 的 ``data_provider`` 实现。"""

    def fetch_realtime_quote(self, *, stock_code: str) -> Optional[Dict[str, Any]]:
        """取实时行情并收敛为源字段字典；无数据返回 ``None``。"""
        quote = get_realtime_quote(stock_code)
        if quote is None:
            return None
        return {field: getattr(quote, field, None) for field in _REALTIME_FIELDS}
