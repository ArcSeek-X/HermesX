# -*- coding: utf-8 -*-
"""涨跌停榜单用例（市场域）。

职责边界：

- 用例层：榜单类型词汇、取数失败降级（fail-open 为空榜）；
- 端口层：按榜单类型取明细（``ports.LimitPoolProviderPort``）；
- 适配器：选源 / 回退 / 60s TTL 缓存 / 健康冷却由
  ``data_provider/limit_pool/`` 的 Manager 提供，适配器只做契约转换。

失败降级为 ``[]`` 而不是抛错：涨跌停池是展示型数据，单次上游抖动不应让接口
500；空榜不会被数据源 Manager 缓存（``is_valid_result`` 只认非空结果），
因此下一次请求会重新取数，不冻结整段 TTL。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.application.market.ports import LimitPoolProviderPort

logger = logging.getLogger(__name__)

# 榜单类型词汇。取值与 ``data_provider.limit_pool.base`` 一致，由
# ``tests/test_limit_pool_endpoints.py`` 逐值对齐，避免两侧字符串漂移。
LIMIT_UP = "limit_up"
LIMIT_DOWN = "limit_down"
VALID_LIMIT_POOL_TYPES = (LIMIT_UP, LIMIT_DOWN)


class LimitPoolService:
    """涨跌停榜单用例。"""

    def __init__(self, provider: LimitPoolProviderPort) -> None:
        self._provider = provider

    def get_board(
        self,
        *,
        board: str,
        date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """取榜单明细；数据源异常降级为空列表，不拖垮接口。

        ``board`` 的合法取值见 :data:`VALID_LIMIT_POOL_TYPES`；非法值沿用数据源
        Manager 的既有归一行为（回退到涨停池），用例层不重复实现一份归一。
        """
        try:
            return self._provider.fetch_board(
                pool_type=board,
                date=date,
                limit=limit,
            )
        except Exception as exc:  # 数据源异常不拖垮接口
            logger.warning(
                "[LimitPool] 获取榜单失败: pool_type=%s error=%s", board, exc
            )
            return []
