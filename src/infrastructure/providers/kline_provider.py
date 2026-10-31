# -*- coding: utf-8 -*-
"""行情端口的数据源适配器。

只做 ``data_provider`` dataclass → 端口字典的字段收敛：

- 不重写选源 / 回退 / TTL / 健康冷却（仍在各 Manager）；
- 不做单位换算、不删字段、不补契约字段（那些在 ``src.application.quote``）；
- 不吞异常，交给用例与端点决定降级或错误码。

模块级 import 保持与原端点一致的导入时机（``data_provider`` 各能力包在导入期
构造 Manager 与 source 注册表）；因此测试必须 patch 本模块符号
（``src.infrastructure.providers.kline_provider.get_kline_data`` 等），
patch ``data_provider.*`` 包属性对已绑定引用不生效。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from data_provider.code_search.base import search_codes
from data_provider.kline.base import KLineRequest, get_kline_data
from data_provider.stock_info.base import get_stock_info

# 与 ``api.v1.schemas.kline.StockInfoResponse`` 对齐；``update_time`` 无数据源对应值，
# 由用例层补 ``None``。
_STOCK_INFO_FIELDS = (
    "stock_code",
    "stock_name",
    "current_price",
    "change",
    "change_percent",
    "open",
    "prev_close",
    "high",
    "low",
    "volume",
    "amount",
    "turnover_rate",
    "amplitude",
    "pe_ratio_ttm",
    "total_market_cap",
    "source",
)


class DataProviderQuoteProvider:
    """基于 ``data_provider`` 各能力 Manager 的行情取数。"""

    def search_codes(self, *, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """代码搜索；全部 source 未命中时 ``search_codes`` 自身返回空列表。"""
        return [
            {
                "code": item.code,
                "name": item.name,
                "market": item.market,
                "secid": item.secid,
            }
            for item in search_codes(keyword, limit=limit)
        ]

    def fetch_kline(
        self,
        *,
        stock_code: str,
        period: str,
        limit: int,
        fqt: int,
        before_date: Optional[str],
    ) -> Dict[str, Any]:
        """取 K 线；全部 source 失败时由 Manager 抛 ``LookupError``。"""
        result = get_kline_data(
            KLineRequest(
                stock_code=stock_code,
                period=period,
                limit=limit,
                fqt=fqt,
                before_date=before_date,
            )
        )
        return {
            "stock_code": result.stock_code,
            "stock_name": result.stock_name,
            "period": result.period,
            "secid": result.secid,
            "prev_close": result.prev_close,
            "source": result.source,
            # 不在这里 ``dict(row)``：行拷贝与契约整形都在用例层，畸形行的失败才能被
            # 收成一个应用层错误（否则会以裸 ``ValueError`` 漏到端点的 422 分支）。
            "data": list(result.data),
        }

    def fetch_stock_info(self, *, stock_code: str) -> Dict[str, Any]:
        """取股票基础信息；全部 source 失败时由 Manager 抛 ``LookupError``。"""
        result = get_stock_info(stock_code)
        return {field: getattr(result, field) for field in _STOCK_INFO_FIELDS}
