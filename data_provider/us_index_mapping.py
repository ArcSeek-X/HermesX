# -*- coding: utf-8 -*-
"""
===================================
美股指数与股票代码工具
===================================

提供：
1. 美股指数代码映射（如 SPX -> ^GSPC）
2. 美股股票代码识别（AAPL、TSLA 等）

规则本体已下沉 ``src.domain.market.us_index_symbols``（R3-S14 把
``is_us_stock_code`` 也一并移入），本模块只保留薄 re-export 以兼容
既有 ``from data_provider.us_index_mapping import ...`` 调用方，并继续
提供 Yahoo Finance 符号转换。
"""

from src.domain.market.us_index_symbols import (  # noqa: F401  re-export: single source of truth lives in domain
    US_INDEX_MAPPING,
    is_us_index_code,
    is_us_stock_code,
)


def get_us_index_yf_symbol(code: str) -> tuple:
    """
    获取美股指数的 Yahoo Finance 符号与中文名称。

    Args:
        code: 用户输入，如 'SPX', '^GSPC', 'DJI'

    Returns:
        (yf_symbol, chinese_name) 元组，未找到时返回 (None, None)。

    Examples:
        >>> get_us_index_yf_symbol('SPX')
        ('^GSPC', '标普500指数')
        >>> get_us_index_yf_symbol('AAPL')
        (None, None)
    """
    normalized = (code or '').strip().upper()
    return US_INDEX_MAPPING.get(normalized, (None, None))
