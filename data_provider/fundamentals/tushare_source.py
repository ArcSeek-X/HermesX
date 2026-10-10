# -*- coding: utf-8 -*-
"""
@file: tushare_source.py
@description: 基本面能力 tushare source，先复用既有基本面聚合入口完成 ADR 落位。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Optional

from data_provider.base import DataFetcherManager
from data_provider.fundamentals.base import (
    FundamentalsDataSource,
    FundamentalsRequest,
    FundamentalsResult,
)
from src.config import get_config


class TushareFundamentalsSource(FundamentalsDataSource):
    """基本面 source，占位承接现有聚合链路并收敛到 ADR 目录。"""

    source_id = "tushare"

    def __init__(self) -> None:
        self.fetcher_manager = DataFetcherManager()

    def is_available(self) -> bool:
        """仅在配置 Tushare Token 时参与选源。"""
        return bool(get_config().tushare_token)

    def fetch(self, request: FundamentalsRequest) -> Optional[FundamentalsResult]:
        """
        复用既有基本面聚合入口，先将能力收口到 ADR 目录。

        这里保持运行期兼容，后续若项目将 Tushare 财务通道进一步下沉，
        该 source 可以在不改调用方的前提下直接替换内部实现。
        """
        payload = self.fetcher_manager.get_fundamental_context(
            request.stock_code,
            budget_seconds=request.budget_seconds,
        )
        if not payload:
            return None
        return FundamentalsResult(
            stock_code=request.stock_code,
            payload=payload,
            source=self.source_id,
            metadata={"budget_seconds": request.budget_seconds},
        )
