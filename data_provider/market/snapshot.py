"""MarketSnapshotPort 的原始快照入口；只透传，不添加回退、重试或缓存。"""


def fetch_eastmoney_market_snapshot():
    """保留源级默认分页/并发参数与惰性加载时机。"""
    from data_provider.market.eastmoney_source import fetch_eastmoney_market_snapshot as fetch

    return fetch()


def fetch_tencent_market_snapshot():
    """保留本地股票索引及腾讯批量抓取语义。"""
    from data_provider.market.tencent_source import fetch_tencent_market_snapshot as fetch

    return fetch()
