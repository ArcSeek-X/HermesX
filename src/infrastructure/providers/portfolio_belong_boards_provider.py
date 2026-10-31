# -*- coding: utf-8 -*-
"""个股所属板块适配器：把 ``data_provider.DataFetcherManager.get_belong_boards``
转成应用端口形状。

``data_provider/`` 原位保留为数据源能力包（ADR-001），本适配器只封装"取个股所属
板块"这一用例所需能力；``DataFetcherManager`` 惰性导入（与迁移前 ``_get_data_manager``
一致），SDK / 数据源缺失或调用异常时按 best-effort 回退语义返回空列表，由应用层
按"无板块信息"降级。选源 / 回退 / 限速 / 主机轮换 / 重试仍由 data_provider 内部负责，
本层不重复实现。

实现端口：:class:`~src.application.quote.ports` 同域的
:class:`~src.application.portfolio.ports.BelongBoardsPort`
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DataProviderPortfolioBelongBoards:
    """:class:`BelongBoardsPort` 的 ``data_provider`` 实现。"""

    def get_belong_boards(self, *, code: str) -> List[Dict[str, Any]]:
        """取个股所属板块；DataFetcherManager 不可用或异常返回空列表（best-effort）。"""
        try:
            from data_provider import DataFetcherManager

            result = DataFetcherManager().get_belong_boards(code)
        except Exception as exc:  # noqa: BLE001 - 数据源缺失等，降级为无板块信息
            logger.debug("[PortfolioRisk] 板块归属取数不可用 %s: %s", code, exc)
            return []
        if isinstance(result, list):
            return result
        return []
