"""供应商侧共享符号适配；指数映射复用领域真源，不加载运行管理器。"""

from src.domain.market.us_index_symbols import US_INDEX_MAPPING, is_us_stock_code
from src.domain.market.market_symbol_utils import is_suffix_market_symbol


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


def convert_yfinance_symbol(stock_code: str, *, is_jp_kr, is_tw, is_bse, logger) -> str:
    """
    转换股票代码为 Yahoo Finance 格式

    Yahoo Finance 代码格式：
    - A股沪市：600519.SS (Shanghai Stock Exchange)
    - A股深市：000001.SZ (Shenzhen Stock Exchange)
    - 港股：0700.HK (Hong Kong Stock Exchange)
    - 美股：AAPL, TSLA, GOOGL (无需后缀)

    Args:
        stock_code: 原始代码，如 '600519', 'hk00700', 'AAPL'

    Returns:
        Yahoo Finance 格式代码

    Examples:
        >>> fetcher._convert_stock_code('600519')
        '600519.SS'
        >>> fetcher._convert_stock_code('hk00700')
        '0700.HK'
        >>> fetcher._convert_stock_code('AAPL')
        'AAPL'
    """
    code = stock_code.strip().upper()

    # 美股指数：映射到 Yahoo Finance 符号（如 SPX -> ^GSPC）
    yf_symbol, _ = get_us_index_yf_symbol(code)
    if yf_symbol:
        logger.debug(f"识别为美股指数: {code} -> {yf_symbol}")
        return yf_symbol

    # 美股：1-5 个大写字母（可选 .X 后缀），原样返回
    if is_us_stock_code(code):
        logger.debug(f"识别为美股代码: {code}")
        return code

    # 日股/韩股/台股 MVP：显式 Yahoo Finance suffix-only 代码，原样传给 Yahoo。
    if is_jp_kr(code) or is_tw(code):
        logger.debug(f"识别为日韩台 Yahoo suffix 代码: {code}")
        return code

    # 港股：hk前缀 -> .HK后缀
    if code.startswith('HK'):
        hk_code = code[2:].lstrip('0') or '0'  # 去除前导0，但保留至少一个0
        hk_code = hk_code.zfill(4)  # 补齐到4位
        logger.debug(f"转换港股代码: {stock_code} -> {hk_code}.HK")
        return f"{hk_code}.HK"

    # 港股裸码：4-5 位纯数字（如 00700、02513、0001）按港股处理。
    # A 股代码全部是 6 位，4-5 位裸数字不可能是 A 股或 BSE（BSE 是
    # 4/8/920xxx 6 位），因此可以先于 .SZ 兜底分流到 .HK，避免 yfinance
    # 把 02513 这类新港股误判为深市后缀导致 Yahoo 404。详见 issue #2091。
    if code.isdigit() and 4 <= len(code) <= 5:
        hk_code = code.lstrip('0') or '0'
        hk_code = hk_code.zfill(4)
        logger.debug(f"识别裸港股代码: {stock_code} -> {hk_code}.HK")
        return f"{hk_code}.HK"

    # 已经包含后缀的情况
    if '.SS' in code or '.SZ' in code or '.HK' in code or '.BJ' in code:
        return code

    # 去除可能的 .SH 后缀
    code = code.replace('.SH', '')

    # ETF: Shanghai ETF (51xx, 52xx, 56xx, 58xx) -> .SS; Shenzhen ETF (15xx, 16xx, 18xx) -> .SZ
    if len(code) == 6:
        if code.startswith(('51', '52', '56', '58')):
            return f"{code}.SS"
        if code.startswith(('15', '16', '18')):
            return f"{code}.SZ"

    # BSE (Beijing Stock Exchange): 8xxxxx, 4xxxxx, 920xxx
    if is_bse(code):
        base = code.split('.')[0] if '.' in code else code
        return f"{base}.BJ"

    # A股：根据代码前缀判断市场
    if code.startswith(('600', '601', '603', '688')):
        return f"{code}.SS"
    elif code.startswith(('000', '002', '300')):
        return f"{code}.SZ"
    else:
        logger.warning(f"无法确定股票 {code} 的市场，默认使用深市")
        return f"{code}.SZ"


def _is_us_market(code: str) -> bool:
    """判断是否为美股/美股指数代码（不含中文前后缀）。"""
    from src.domain.market.us_index_symbols import is_us_stock_code, is_us_index_code

    normalized = (code or "").strip().upper()
    return is_us_index_code(normalized) or is_us_stock_code(normalized)


def _is_hk_market(code: str) -> bool:
    """
    判定是否为港股代码。

    支持 ``.HK`` 后缀、``HK00700`` 前缀形式，以及 4-5 位纯数字裸码
    （A 股 ETF/股票为 6 位，与港股 4-5 位裸数字不冲突）。``YfinanceFetcher``
    与 ``AkshareFetcher`` / ``LongbridgeFetcher`` 的 ``_is_hk_code`` 与本
    函数对裸港股码的位数范围保持一致。
    """
    normalized = (code or "").strip().upper()
    if normalized.endswith(".HK"):
        base = normalized[:-3]
        return base.isdigit() and 1 <= len(base) <= 5
    if normalized.startswith("HK"):
        digits = normalized[2:]
        return digits.isdigit() and 1 <= len(digits) <= 5
    if normalized.isdigit() and 4 <= len(normalized) <= 5:
        return True
    return False


def _is_jp_market(code: str) -> bool:
    """判定是否为日本 Yahoo Finance suffix 代码（如 7203.T）。"""
    return is_suffix_market_symbol(code, "jp")


def _is_kr_market(code: str) -> bool:
    """判定是否为韩国 Yahoo Finance suffix 代码（如 005930.KS / 035720.KQ）。"""
    return is_suffix_market_symbol(code, "kr")


def _is_tw_market(code: str) -> bool:
    """判定是否为台湾 Yahoo Finance suffix 代码（TWSE 上市 2330.TW / TPEx 上柜 6505.TWO）。

    台股 base 为 4-6 位（普通股 4 位，ETF/其他至 6 位，如 00878 / 006208）。
    仅带 .TW/.TWO 后缀的代码才识别为台股，裸 6 位代码仍按 A 股语义处理。
    """
    return is_suffix_market_symbol(code, "tw")


def _market_tag(code: str) -> str:
    """返回市场标签: cn/us/hk/jp/kr/tw."""
    if _is_us_market(code):
        return "us"
    if _is_hk_market(code):
        return "hk"
    if _is_jp_market(code):
        return "jp"
    if _is_kr_market(code):
        return "kr"
    if _is_tw_market(code):
        return "tw"
    return "cn"
