# -*- coding: utf-8 -*-
"""基于股票主数据索引的代码核验适配器。

实现 :class:`~src.application.watchlist.ports.StockCodeValidatorPort`：索引的读取与
缓存语义沿用 ``src.data.stock_index_loader``，本适配器只决定「缺失时怎么办」——
索引加载异常时宽松放行，避免主数据缺失拖垮自选股新增。
"""

from __future__ import annotations

import logging

from src.data.stock_index_loader import get_stock_name_index_map

logger = logging.getLogger(__name__)


class StockIndexCodeValidator:
    """以 ``stocks.index.json`` 的规范代码集合核验股票代码。"""

    def is_known(self, stock_code: str) -> bool:
        try:
            return stock_code in get_stock_name_index_map()
        except Exception as exc:  # pragma: no cover - 索引加载异常时降级
            logger.warning("[自选股] 股票索引核验失败，降级放行：%s", exc)
            return True
