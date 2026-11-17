# -*- coding: utf-8 -*-
"""行情用例（K 线、股票搜索、股票基础信息）。

按 ``ARCHITECTURE_TARGET.md`` §4.1，行情 / K 线 / 股票信息 / 代码解析同属
``application/quote/``；端点仍按能力域保留 URL（ADR-001 §5.3），不按端点名
新建平行用例包。

对外只暴露用例与端口；适配器在 ``src.infrastructure.providers.kline_provider``，
选源 / 回退 / TTL / 健康冷却仍由 ``data_provider`` 各 Manager 负责。
"""

from src.application.quote.ports import QuoteProviderPort, RealtimeQuotePort
from src.application.quote.service import QuoteDataError, QuoteService

# 不在此顶层聚合 StockService：顶层聚合会把 ``src.application.quote.service`` 的
# 取数链路一并拉入，且 StockService 目前统一经子模块全路径导入（见 src.bootstrap.quote）。
# （PP-6 已删除其对 ``src.repositories`` 的死依赖，历史上引发循环导入的路径不再存在。）
__all__ = [
    "QuoteDataError",
    "QuoteProviderPort",
    "QuoteService",
    "RealtimeQuotePort",
]
