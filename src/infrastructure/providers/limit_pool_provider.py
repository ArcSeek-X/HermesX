# -*- coding: utf-8 -*-
"""涨跌停榜单的数据源适配器。

把 ``data_provider/limit_pool`` 的 ``LimitPoolResult`` 契约转成用例端口的
「明细字典列表」：

- 选源、回退、60s TTL 缓存、健康冷却完全复用该包的 Manager，这里不重写；
- 空榜仍是有效返回值（不是异常），降级语义在用例层；
- 归一化（非法 ``pool_type`` 回退涨停池）也留在数据源包，避免两份归一规则。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from data_provider.limit_pool import get_limit_pool


class DataProviderLimitPoolProvider:
    """``LimitPoolProviderPort`` 的数据源实现。"""

    def fetch_board(
        self,
        *,
        pool_type: str,
        date: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """取出榜单明细；全部 source 失败时由数据源抛 ``LookupError``。"""
        result = get_limit_pool(pool_type=pool_type, date=date, n=limit)
        return [entry.to_dict() for entry in result.entries]
