# -*- coding: utf-8 -*-
"""US index/stock symbol rules (domain layer, pure data + pure regex).

Moved out of ``data_provider.us_index_mapping`` so application/quote code can
detect US index and stock symbols without importing the data provider layer.
``us_index_mapping`` re-imports the three names below for its Yahoo-symbol
helpers and existing consumers; this module is the single source of truth.

R3-S14 additionally moved ``is_us_stock_code`` here (previously defined in
the data provider layer) so ``src/domain/market/trading_calendar.py`` can
classify a code's market without importing ``data_provider``.
"""

import re


# 用户输入 -> (Yahoo Finance 符号, 中文名称)
US_INDEX_MAPPING = {
    # 标普 500
    'SPX': ('^GSPC', '标普500指数'),
    '^GSPC': ('^GSPC', '标普500指数'),
    'GSPC': ('^GSPC', '标普500指数'),
    # 道琼斯工业平均指数
    'DJI': ('^DJI', '道琼斯工业指数'),
    '^DJI': ('^DJI', '道琼斯工业指数'),
    'DJIA': ('^DJI', '道琼斯工业指数'),
    # 纳斯达克综合指数
    'IXIC': ('^IXIC', '纳斯达克综合指数'),
    '^IXIC': ('^IXIC', '纳斯达克综合指数'),
    'NASDAQ': ('^IXIC', '纳斯达克综合指数'),
    # 纳斯达克 100
    'NDX': ('^NDX', '纳斯达克100指数'),
    '^NDX': ('^NDX', '纳斯达克100指数'),
    # VIX 波动率指数
    'VIX': ('^VIX', 'VIX恐慌指数'),
    '^VIX': ('^VIX', 'VIX恐慌指数'),
    # 罗素 2000
    'RUT': ('^RUT', '罗素2000指数'),
    '^RUT': ('^RUT', '罗素2000指数'),
}


# 美股代码正则：1-5 个大写字母，可选 .X 后缀（如 BRK.B）
_US_STOCK_PATTERN = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')


def is_us_index_code(code: str) -> bool:
    """
    判断代码是否为美股指数符号。

    Args:
        code: 股票/指数代码，如 'SPX', 'DJI'

    Returns:
        True 表示是已知美股指数符号，否则 False

    Examples:
        >>> is_us_index_code('SPX')
        True
        >>> is_us_index_code('AAPL')
        False
    """
    return (code or '').strip().upper() in US_INDEX_MAPPING


def is_us_stock_code(code: str) -> bool:
    """
    判断代码是否为美股股票符号（排除美股指数）。

    美股股票代码为 1-5 个大写字母，可选 .X 后缀如 BRK.B。
    美股指数（SPX、DJI 等）明确排除。

    Args:
        code: 股票代码，如 'AAPL', 'TSLA', 'BRK.B'

    Returns:
        True 表示是美股股票符号，否则 False

    Examples:
        >>> is_us_stock_code('AAPL')
        True
        >>> is_us_stock_code('TSLA')
        True
        >>> is_us_stock_code('BRK.B')
        True
        >>> is_us_stock_code('SPX')
        False
        >>> is_us_stock_code('600519')
        False
    """
    normalized = (code or '').strip().upper()
    # 美股指数不是股票
    if normalized in US_INDEX_MAPPING:
        return False
    return bool(_US_STOCK_PATTERN.match(normalized))
