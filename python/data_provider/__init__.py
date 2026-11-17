"""数据源公开兼容入口；按需解析，导入包本身不加载全部厂商。"""

from importlib import import_module

_EXPORTS = {
    "BaseFetcher": ("data_provider.common.fetcher_contract", "BaseFetcher"),
    "DataFetcherManager": ("data_provider.runtime.manager", "DataFetcherManager"),
    "EfinanceFetcher": ("data_provider.runtime.fetchers.efinance", "EfinanceFetcher"),
    "TencentFetcher": ("data_provider.kline.daily_tencent_source", "TencentFetcher"),
    "AkshareFetcher": ("data_provider.runtime.fetchers.akshare", "AkshareFetcher"),
    "TushareFetcher": ("data_provider.runtime.fetchers.tushare", "TushareFetcher"),
    "PytdxFetcher": ("data_provider.runtime.fetchers.pytdx", "PytdxFetcher"),
    "BaostockFetcher": ("data_provider.runtime.fetchers.baostock", "BaostockFetcher"),
    "YfinanceFetcher": ("data_provider.runtime.fetchers.yfinance", "YfinanceFetcher"),
    "LongbridgeFetcher": ("data_provider.runtime.fetchers.longbridge", "LongbridgeFetcher"),
    "FinnhubFetcher": ("data_provider.runtime.fetchers.finnhub", "FinnhubFetcher"),
    "AlphaVantageFetcher": ("data_provider.runtime.fetchers.alphavantage", "AlphaVantageFetcher"),
    "is_us_index_code": ("src.domain.market.us_index_symbols", "is_us_index_code"),
    "is_us_stock_code": ("src.domain.market.us_index_symbols", "is_us_stock_code"),
    "is_hk_stock_code": ("data_provider.runtime.fetchers.akshare", "is_hk_stock_code"),
    "get_us_index_yf_symbol": ("data_provider.common.symbols", "get_us_index_yf_symbol"),
    "US_INDEX_MAPPING": ("src.domain.market.us_index_symbols", "US_INDEX_MAPPING"),
}

__all__ = [
    "BaseFetcher",
    "DataFetcherManager",
    "EfinanceFetcher",
    "TencentFetcher",
    "AkshareFetcher",
    "TushareFetcher",
    "PytdxFetcher",
    "BaostockFetcher",
    "YfinanceFetcher",
    "LongbridgeFetcher",
    "FinnhubFetcher",
    "AlphaVantageFetcher",
    "is_us_index_code",
    "is_us_stock_code",
    "is_hk_stock_code",
    "get_us_index_yf_symbol",
    "US_INDEX_MAPPING",
]


def __getattr__(name):
    try:
        module, symbol = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    return getattr(import_module(module), symbol)


def __dir__():
    return sorted(set(globals()) | set(__all__))
