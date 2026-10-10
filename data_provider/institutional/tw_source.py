# -*- coding: utf-8 -*-
"""
@file: tw_source.py
@description: 台湾机构持仓 source，复用既有 TwInstitutionalFetcher 通道。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from typing import Optional

from data_provider.institutional.base import (
    InstitutionalDataSource,
    InstitutionalRequest,
    InstitutionalResult,
)
from data_provider.tw_institutional_fetcher import TwInstitutionalFetcher


class TwInstitutionalSource(InstitutionalDataSource):
    """复用 TwInstitutionalFetcher 的台湾机构 source。"""

    source_id = "tw"

    def __init__(self) -> None:
        self.fetcher = TwInstitutionalFetcher()

    def fetch(self, request: InstitutionalRequest) -> Optional[InstitutionalResult]:
        """获取单只台股的三大法人买卖超数据。"""
        if request.date:
            payload = self.fetcher.get_institutional_net(request.stock_code, request.date)
        else:
            payload = self.fetcher.get_institutional_net(request.stock_code)
        if not payload:
            return None
        return InstitutionalResult(
            stock_code=request.stock_code,
            payload=payload,
            source=self.source_id,
            metadata={"date": request.date},
        )
