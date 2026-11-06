# -*- coding: utf-8 -*-
"""
@file: tw_source.py
@description: 台湾机构持仓 source，复用既有 TwInstitutionalFetcher 通道。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

import sys
from typing import Optional

from data_provider.institutional.base import (
    InstitutionalDataSource,
    InstitutionalRequest,
    InstitutionalResult,
)


def __getattr__(name: str):
    """保留原客户端替换点，按需解析，避免首次导入永久绑定测试替身。"""
    if name == "TwInstitutionalFetcher":
        from data_provider.institutional.tw_client import TwInstitutionalFetcher

        return TwInstitutionalFetcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class TwInstitutionalSource(InstitutionalDataSource):
    """复用 TwInstitutionalFetcher 的台湾机构 source。"""

    source_id = "tw"

    def __init__(self) -> None:
        """构造台股机构数据源。"""
        # 在装配时解析客户端，避免首次导入发生在 mock 范围内后永久绑定替身。
        self.fetcher = getattr(sys.modules[__name__], "TwInstitutionalFetcher")()

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
