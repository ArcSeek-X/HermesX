"""创建默认数据源；不持有 Manager、缓存、锁或回退状态。"""

import logging
from typing import List

from data_provider.common.fetcher_contract import BaseFetcher

logger = logging.getLogger("data_provider.base")


def build_default_fetchers() -> List[BaseFetcher]:
    """按原时机读取配置并构造源；优先级排序仍由管理器持锁执行。"""
    from src.config import get_config
    from data_provider.runtime.fetchers.efinance import EfinanceFetcher
    from data_provider.kline.daily_tencent_source import TencentFetcher
    from data_provider.runtime.fetchers.akshare import AkshareFetcher
    from data_provider.runtime.fetchers.tushare import TushareFetcher
    from data_provider.runtime.fetchers.tickflow import TickFlowFetcher
    from data_provider.runtime.fetchers.pytdx import PytdxFetcher
    from data_provider.runtime.fetchers.baostock import BaostockFetcher
    from data_provider.runtime.fetchers.yfinance import YfinanceFetcher
    from data_provider.runtime.fetchers.longbridge import LongbridgeFetcher
    config = get_config()
    # 创建所有数据源实例（优先级在各 Fetcher 的 __init__ 中确定）
    efinance = EfinanceFetcher()
    tencent = TencentFetcher()
    akshare = AkshareFetcher()
    pytdx = PytdxFetcher()      # 通达信数据源（可配 PYTDX_HOST/PYTDX_PORT）
    baostock = BaostockFetcher()
    yfinance = YfinanceFetcher()
    optional_fetchers: List[BaseFetcher] = []

    tushare_token = (getattr(config, "tushare_token", None) or "").strip()
    if tushare_token:
        optional_fetchers.append(TushareFetcher())  # 会根据 Token 配置自动调整优先级
    else:
        logger.debug("[数据源初始化] 跳过未配置的 TushareFetcher")

    tickflow_api_key = (getattr(config, "tickflow_api_key", None) or "").strip()
    if tickflow_api_key:
        optional_fetchers.append(
            TickFlowFetcher(
                api_key=tickflow_api_key,
                kline_adjust=getattr(config, "tickflow_kline_adjust", "none"),
                batch_daily_enabled=getattr(config, "tickflow_batch_daily_enabled", True),
                batch_size=getattr(config, "tickflow_batch_size", 100),
                priority=getattr(config, "tickflow_priority", 2),
            )
        )
    else:
        logger.debug("[data source init] skip TickFlowFetcher because TICKFLOW_API_KEY is not configured")

    if LongbridgeFetcher.has_configured_credentials(config):
        optional_fetchers.append(LongbridgeFetcher())  # 长桥（美股/港股兜底，懒加载）
    else:
        logger.debug("[数据源初始化] 跳过未配置的 LongbridgeFetcher")

    finnhub_api_key = (getattr(config, "finnhub_api_key", None) or "").strip()
    if finnhub_api_key:
        from data_provider.runtime.fetchers.finnhub import FinnhubFetcher
        optional_fetchers.append(FinnhubFetcher())
    else:
        logger.debug("[数据源初始化] 跳过未配置的 FinnhubFetcher")

    alphavantage_api_key = (getattr(config, "alphavantage_api_key", None) or "").strip()
    if alphavantage_api_key:
        from data_provider.runtime.fetchers.alphavantage import AlphaVantageFetcher
        optional_fetchers.append(AlphaVantageFetcher())
    else:
        logger.debug("[数据源初始化] 跳过未配置的 AlphaVantageFetcher")

    return [efinance, akshare, pytdx, baostock, yfinance, tencent, *optional_fetchers]
