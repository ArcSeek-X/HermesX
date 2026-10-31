# -*- coding: utf-8 -*-
"""持仓实时行情适配器：把 ``data_provider.DataFetcherManager`` 的实时取数转成
应用端口 :class:`~src.application.portfolio.ports.PortfolioRealtimeQuotePort` 形状。

``data_provider/`` 原位保留为数据源能力包（ADR-001），本适配器只封装持仓快照估值
所需的两项能力：批量预热缓存（``prefetch_realtime_quotes``）与单票取价取源
（``get_realtime_quote(stock_code, log_final_failure=False)`` → ``(price, source)``）。
每次调用现场构造 ``DataFetcherManager``（与迁移前调用点逐字一致：manager 只用于暖缓存、
per-symbol worker 各自新建 manager 以免串在其 per-fetcher 锁上），选源 / 回退 / 限速 /
主机轮换 / 重试仍由 data_provider 内部负责，本层不重复实现。

失败语义：取数异常一律上抛（与迁移前 ``_fetch_realtime_position_price`` 外层 try/except
捕获后 ``logger.warning`` + 返回 ``(None, None)`` 的语义逐字一致）；``UnifiedRealtimeQuote``
→ ``(price, provider)`` 的收敛在此完成（provider 取 ``source.value``，回退 ``str(source)``），
价的有效性（float / ``>0``）仍由应用层校验。
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DataProviderPortfolioRealtimeQuote:
    """:class:`PortfolioRealtimeQuotePort` 的 ``data_provider`` 实现。"""

    def prefetch_quotes(self, *, codes: List[str]) -> None:
        """批量预热实时行情缓存；仅暖缓存、返回值不被消费，异常上抛由用例降级。"""
        from data_provider.base import DataFetcherManager

        DataFetcherManager().prefetch_realtime_quotes(list(codes))

    def fetch_price_and_source(
        self, *, code: str
    ) -> Optional[Tuple[Any, Optional[str]]]:
        """取单票实时价与来源，返回 ``(原始 price, provider 字符串)``；无数据返回 ``None``。"""
        from data_provider.base import DataFetcherManager

        quote = DataFetcherManager().get_realtime_quote(code, log_final_failure=False)
        if quote is None:
            return None
        price = getattr(quote, "price", None)
        source = getattr(quote, "source", None)
        provider = getattr(source, "value", None) or (str(source) if source is not None else None)
        return price, provider
