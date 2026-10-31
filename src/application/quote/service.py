# -*- coding: utf-8 -*-
"""行情用例（K 线、股票搜索、股票基础信息）。

职责边界：

- 用例层：对外契约整形——K 线成交量按「手」输出（前端按手格式化）、剔除
  上游行内的 ``prev_close``（响应里已有顶层 ``prev_close``）、补 ``update_time``；
- 端口层：取数（``ports.QuoteProviderPort``），不做降级、不吞异常；
- 适配器：``data_provider`` 各 Manager 的选源 / 回退 / TTL / 健康冷却保持原位，
  适配器只做 dataclass → 字典的字段收敛。

错误映射（404 / 422 / 502）留在端点：它是 HTTP 语义，端口与用例都不应知道
状态码；因此本模块不 ``try/except`` 取数异常，让 ``LookupError`` / ``ValueError``
原样上抛。唯一例外是整形自身发现上游结构不合契约，抛 :class:`QuoteDataError`，
避免被端点的 ``ValueError → 422`` 分支误判为「客户端参数错误」。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application.quote.ports import QuoteProviderPort

# 上游 K 线成交量单位为「股」，对外契约沿用前端既有假设「手」。
_VOLUME_UNIT_DIVISOR = 100


class QuoteDataError(RuntimeError):
    """上游结果不符合对外契约（如 K 线行不是字典）。

    不能抛 ``ValueError``：端点的 ``ValueError → 422`` 是给客户端参数用的，
    把上游数据格式异常当 422 会把故障归错到调用方。
    """


class QuoteService:
    """行情用例。"""

    def __init__(self, provider: QuoteProviderPort) -> None:
        self._provider = provider

    def search_codes(self, *, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """按关键词搜索代码；无命中返回空列表（由数据源侧保证）。"""
        return self._provider.search_codes(keyword=keyword, limit=limit)

    def get_kline(
        self,
        *,
        stock_code: str,
        period: str,
        limit: int,
        fqt: int = 1,
        before_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """取 K 线序列并整形为对外契约。"""
        payload = self._provider.fetch_kline(
            stock_code=stock_code,
            period=period,
            limit=limit,
            fqt=fqt,
            before_date=before_date,
        )
        rows: List[Dict[str, Any]] = []
        for index, row in enumerate(payload.get("data") or []):
            try:
                item = dict(row)
            except (TypeError, ValueError) as exc:
                raise QuoteDataError(
                    f"K 线第 {index} 行不是字典: {type(row).__name__}"
                ) from exc
            if item.get("volume") is not None:
                item["volume"] = item["volume"] / _VOLUME_UNIT_DIVISOR
            item.pop("prev_close", None)
            rows.append(item)
        return {**payload, "data": rows}

    def get_stock_info(self, *, stock_code: str) -> Dict[str, Any]:
        """取股票基础信息。

        ``update_time`` 在数据源结果里没有对应值，但属于响应契约字段，统一由
        用例补 ``None``，避免端点各写一份。
        """
        payload = self._provider.fetch_stock_info(stock_code=stock_code)
        return {**payload, "update_time": None}
