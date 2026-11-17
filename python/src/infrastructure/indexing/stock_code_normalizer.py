# -*- coding: utf-8 -*-
"""数据源侧的股票代码归一化实现。

纯规则复用 ``src.domain.market.stock_codes``；应用层仍通过既有端口
取用，不因股票代码转换加载数据源运行管理器。
"""

from __future__ import annotations


class DataProviderStockCodeNormalizer:
    """``StockCodeNormalizerPort`` 的默认实现。"""

    def normalize(self, stock_code: str) -> str:
        """将股票代码规范化为统一格式。"""
        from src.domain.market.stock_codes import normalize_stock_code

        return normalize_stock_code(stock_code or "")
