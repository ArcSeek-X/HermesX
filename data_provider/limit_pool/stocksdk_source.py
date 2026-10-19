# -*- coding: utf-8 -*-
"""
@file: stocksdk_source.py
@description: 涨跌停池 StockSDK source（桥接型补充源）。
@author: Lensgcx (GaoCangxiong)

当前状态：**显式不可用**。
StockSDK bridge 的 action 白名单（`scripts/stocksdk_bridge/bridge.mjs`）目前只覆盖
ping / search / quote / timeline / kline / market_indices / market_overview /
northbound_summary / market_fund_flow / board_list / sector_fund_flow_rank /
sector_fund_flow_history_batch，**没有涨跌停池 action**；stock-sdk 的命名空间
（`quotes` / `kline` / `search` / `board` / `fundFlow` / `northbound`）亦未提供封板股池能力。

因此本 source 的 `is_available()` 返回 False：Manager 会跳过它而不产生无效调用开销，
避免"注册了第二源但实际不可用"的假象（ADR-001 §10.2 B2 ⑤ 已记录该缺口）。

启用条件（两步）：
1. `scripts/stocksdk_bridge/bridge.mjs` 新增涨跌停池 action 并返回明细数组；
2. 本文件 `is_available()` 改为 `self._client().is_available()`，并实现
   `fetch()` 调用 `client.invoke("<action>", {...})` 后按 `_to_entry` 映射为 `LimitPoolEntry`。
"""

from __future__ import annotations

import logging
from typing import Optional

from data_provider.limit_pool.base import (
    LimitPoolDataSource,
    LimitPoolEntry,
    LimitPoolRequest,
    LimitPoolResult,
)

logger = logging.getLogger(__name__)


class StockSdkLimitPoolSource(LimitPoolDataSource):
    """StockSDK 涨跌停池 source：bridge 尚不支持，当前不可用。"""

    source_id = "stocksdk"

    def is_available(self) -> bool:
        """bridge 未提供涨跌停池 action，显式声明不可用。"""
        return False

    def fetch(self, request: LimitPoolRequest) -> Optional[LimitPoolResult]:
        """不可用时不会被引擎调用；保留实现以满足抽象接口。"""
        logger.debug("[limit_pool][stocksdk] source 不可用，跳过 pool_type=%s", request.pool_type)
        return None

    @staticmethod
    def _to_entry(row: dict) -> LimitPoolEntry:
        """StockSDK 明细行 → LimitPoolEntry 的映射（待 bridge 支持后启用）。"""
        raise NotImplementedError("StockSDK 涨跌停池 action 尚未在 bridge 中提供")
