# -*- coding: utf-8 -*-
"""
@file: tushare_source.py
@description: 基本面能力 tushare source，先复用既有基本面聚合入口完成 ADR 落位。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Optional

from data_provider.fundamentals.aggregate import (
    FundamentalContextLoader,
    build_fundamental_context_loader,
)
from data_provider.fundamentals.source_contract import (
    FundamentalsDataSource,
    FundamentalsRequest,
    FundamentalsResult,
)
from src.config import get_config


class TushareFundamentalsSource(FundamentalsDataSource):
    """历史 tushare 注册入口，实际承接多源聚合；保留原 Token 门控与来源标签。"""

    source_id = "tushare"

    def __init__(self, context_loader: Optional[FundamentalContextLoader] = None) -> None:
        """保留原构造时机；仅注入聚合加载能力，不让 Source 依赖整个 Manager。"""
        self._context_loader = context_loader if context_loader is not None else build_fundamental_context_loader()

    def is_available(self) -> bool:
        """仅在配置 Tushare Token 时参与选源。"""
        return bool(get_config().tushare_token)

    def fetch(self, request: FundamentalsRequest) -> Optional[FundamentalsResult]:
        """
        通过单向加载边界访问独立聚合实现，不回调可能委托本能力的旧门面。

        这里保持运行期兼容，后续若项目将 Tushare 财务通道进一步下沉，
        该 source 可以在不改调用方的前提下直接替换内部实现。
        """
        payload = self._context_loader(
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
