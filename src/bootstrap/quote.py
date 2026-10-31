# -*- coding: utf-8 -*-
"""行情用例的装配。

用例只依赖取数端口，具体实现绑定到 ``data_provider`` 的适配器；``api`` 只通过
依赖注入拿到装配好的 :class:`~src.application.quote.QuoteService`，不接触数据源包。
"""

from __future__ import annotations

from src.application.quote import QuoteService
from src.application.quote.stock_service import StockService
from src.infrastructure.providers.kline_provider import DataProviderQuoteProvider
from src.infrastructure.providers.realtime_provider import DataProviderRealtimeQuoteProvider


def build_quote_service() -> QuoteService:
    """装配行情用例。

    用例无状态、不持有数据库句柄，按请求装配即可；各数据源的选源与缓存状态在
    ``data_provider`` 的 Manager 单例里，不随用例重建而失效。
    """
    return QuoteService(provider=DataProviderQuoteProvider())


def build_stock_service() -> StockService:
    """装配股票数据服务。

    历史 K 线复用行情用例 :class:`~src.application.quote.QuoteService`（与
    ``QuoteProviderPort`` 共享取数链路），实时行情走
    :class:`~src.application.quote.ports.RealtimeQuotePort`；端点只通过本装配拿到
    依赖，不直接构造或接触数据源包。
    """
    return StockService(
        quote_service=QuoteService(provider=DataProviderQuoteProvider()),
        realtime_port=DataProviderRealtimeQuoteProvider(),
    )


def configure_stock_repository() -> None:
    """装配日线仓储端口工厂（decision / quote 等跨域用例的缺省实现）。

    注册 ``StockRepository`` **类本身**（可调用工厂）而非 eager 实例：用例侧默认
    经 ``get_stock_repository(db_manager)`` 现建仓储，以适配
    ``DatabaseManager.reset_instance()`` 重建后的生命周期（与 PP-1/PP-4/PP-5 同型）。
    进程启动时调用一次（API lifespan / CLI 入口），setter 幂等。
    """
    from src.application.backtest.ports import set_stock_repository_factory
    from src.infrastructure.persistence.repositories.stock_repository import StockRepository

    set_stock_repository_factory(StockRepository)


def configure_name_to_code_resolver() -> None:
    """装配名称→代码解析用例的 code-search 在线 fallback 端口。

    复用既有 :class:`~src.infrastructure.providers.kline_provider.DataProviderQuoteProvider`
    的 ``search_codes``，不新建平行适配器；解析用例只按端口协议调用，不直接依赖
    ``data_provider``。进程启动时调用一次（API lifespan / CLI 入口），setter 幂等；
    未装配时优雅降级为仅本地映射 + 拼音 + 模糊匹配（与原 code-search 失败降级一致）。
    """
    from src.application.quote.name_to_code_resolver import set_code_search_port

    set_code_search_port(DataProviderQuoteProvider())


def configure_intraday_timeline_bridge() -> None:
    """装配单票分时服务的 stock-sdk 桥接回退端口。

    分时的主路径是直连东财 trends2（requests，仍在应用层，网络适配归位留 P4）；
    本装配只接管“直连失败后的桥接回退”这一唯一 ``data_provider`` 依赖，使其不再直接
    耦合数据源包。进程启动时调用一次（API lifespan / CLI 入口），setter 幂等；未装配时
    优雅降级为“仅直连”（与原“桥接不可用→空”一致）。
    """
    from src.application.quote.intraday_timeline_service import set_timeline_bridge_port
    from src.infrastructure.providers.stocksdk_timeline_provider import (
        DataProviderStocksdkTimelineBridge,
    )

    set_timeline_bridge_port(DataProviderStocksdkTimelineBridge())


def configure_market_snapshot() -> None:
    """装配尾盘选股 / 榜单选股用例的全市场快照取数端口。

    回退链编排（东财直连→腾讯→akshare）与日志在用例层，本装配只绑定三源
    实现（``data_provider`` 适配器）。进程启动时调用一次（API lifespan / CLI 入口），
    setter 幂等；未装配时快照优雅降级为 ``None``（用例报“数据源暂不可用”，与迁移前
    三源全部失败的语义一致）。
    """
    from src.application.analysis.eod_picker_service import set_market_snapshot_port
    from src.infrastructure.providers.market_snapshot_provider import (
        DataProviderMarketSnapshotSource,
    )

    set_market_snapshot_port(DataProviderMarketSnapshotSource())
