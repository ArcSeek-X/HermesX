# -*- coding: utf-8 -*-
"""行情用例的端口定义。

端口只描述用例需要的能力，返回「纯数据」形状（``dict`` / ``list[dict]``），
不暴露 ``data_provider`` 的 dataclass：``KLineResult`` / ``StockInfoResult`` /
``CodeSearchResult`` 的字段收敛在适配器里完成，应用层不感知数据源类型。

失败语义：取数失败由实现方抛原异常（``LookupError`` / ``ValueError`` / 其他），
用例不吞异常；HTTP 状态码映射由端点负责（404 / 422 / 502）。

实现方：:class:`~src.infrastructure.providers.kline_provider.DataProviderQuoteProvider`
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class QuoteProviderPort(Protocol):
    """行情取数能力（K 线、代码搜索、股票基础信息）。"""

    def search_codes(self, *, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """按关键词搜索代码，返回 ``code`` / ``name`` / ``market`` / ``secid``。

        数据源侧的「全部 source 未命中」由 ``search_codes`` 自身降级为空列表，
        端口不重复实现该降级。
        """

    def fetch_kline(
        self,
        *,
        stock_code: str,
        period: str,
        limit: int,
        fqt: int,
        before_date: Optional[str],
    ) -> Dict[str, Any]:
        """取 K 线序列。

        返回键：``stock_code`` / ``stock_name`` / ``period`` / ``secid`` /
        ``prev_close`` / ``source`` / ``data``（逐行原始字典，单位换算与字段
        裁剪由用例层按对外契约处理）。
        """

    def fetch_stock_info(self, *, stock_code: str) -> Dict[str, Any]:
        """取股票基础信息，键与 ``StockInfoResponse`` 字段一致（除 ``update_time``）。"""


class RealtimeQuotePort(Protocol):
    """实时行情取数能力。

    实现方：:class:`~src.infrastructure.providers.realtime_provider.DataProviderRealtimeQuoteProvider`
    """

    def fetch_realtime_quote(self, *, stock_code: str) -> Optional[Dict[str, Any]]:
        """取实时行情快照，返回 ``UnifiedRealtimeQuote`` 的字段字典（源字段名，
        如 ``code`` / ``price`` / ``change_pct`` ...）；所有数据源失败时返回 ``None``。

        失败语义与既有实现一致：取数异常由实现方抛出，是否降级由用例决定；
        应用层不感知 ``data_provider`` 的 dataclass 类型。
        """


class IntradayTimelineBridgePort(Protocol):
    """单票分时的 stock-sdk 桥接回退能力（best-effort fallback）。

    实现方：:class:`~src.infrastructure.providers.stocksdk_timeline_provider.DataProviderStocksdkTimelineBridge`
    """

    def fetch_timeline(self, *, code: str) -> Optional[Dict[str, Any]]:
        """走 stock-sdk 桥接取当日分时，返回上游 ``fetch_timeline`` 的原始字典
        （含 ``points`` / ``preClose`` / ``name``）；桥接不可用或异常时返回 ``None``。

        这是直连东财失败后的兜底回退，语义上是 best-effort：不可用不算错误，
        返回 ``None`` 由用例降级为空（与既有“桥接不可用→空”一致）。
        """


class MarketSnapshotPort(Protocol):
    """全市场实时快照取数能力（尾盘选股 / 榜单选股共用）。

    实现方：:class:`~src.infrastructure.providers.market_snapshot_provider.DataProviderMarketSnapshotSource`

    形参例外说明：快照为全市场体量（5000+ 行），转纯 dict 列表会使应用层向量化
    过滤管线性能坍塌，故端口边界以 ``pandas.DataFrame`` 为既定数据形状（非
    ``data_provider`` 类型，应用层不感知数据源 dataclass）。失败语义与其余端口
    一致：取数异常由实现方抛出，回退/降级编排由用例决定。
    """

    def fetch_eastmoney_snapshot(self) -> Any:
        """东财 clist 直连全市场快照（中文列名 DataFrame）；无数据返回 ``None``。"""

    def fetch_tencent_snapshot(self) -> Any:
        """腾讯批量行情全市场快照（中文列名 DataFrame）；无数据返回 ``None``。"""

    def fetch_akshare_snapshot(self) -> Any:
        """东财 ak.stock_zh_a_spot_em（akshare）全市场快照（中文列名 DataFrame）；
        无数据返回 ``None``；高覆盖兜底源，单次调用含随机限速。"""

