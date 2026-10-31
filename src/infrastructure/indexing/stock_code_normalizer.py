# -*- coding: utf-8 -*-
"""数据源侧的股票代码归一化实现。

``normalize_stock_code`` 仍归属 ``data_provider.base``（被扫描/行情链路复用），
应用层通过本适配器取用；导入放在方法内，避免 API 启动时加载整个数据源包。
"""

from __future__ import annotations


class DataProviderStockCodeNormalizer:
    """``StockCodeNormalizerPort`` 的默认实现。"""

    def normalize(self, stock_code: str) -> str:
        from data_provider.base import normalize_stock_code

        return normalize_stock_code(stock_code or "")
