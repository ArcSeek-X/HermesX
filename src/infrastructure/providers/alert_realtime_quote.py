# -*- coding: utf-8 -*-
"""DataFetcherManager 适配器：实现 RealtimeQuotePort。

通过 ``data_provider.realtime.base.get_realtime_quote`` 多源 fallback 获取实时行情，
使 ``src/application/alert/`` 不直接依赖 ``data_provider``（搬入 alert 用例层的禁入前置）。

失败语义按端口契约收敛：能力层在「全部 source 失败」时抛 ``LookupError``，适配器把它
转为 ``None``（与旧 ``DataFetcherManager`` 的降级行为一致），同时保留失败汇总日志，
避免告警侧静默无数据。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DataProviderRealtimeQuote:
    """通过实时行情多源 fallback 获取即时快照。"""

    def get_realtime_quote(self, stock_code: str) -> Any:
        from data_provider.realtime.base import get_realtime_quote

        try:
            return get_realtime_quote(stock_code)
        except LookupError as exc:
            logger.info("[实时行情] %s 所有数据源均失败: %s", stock_code, exc)
            return None
