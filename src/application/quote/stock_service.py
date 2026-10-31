# -*- coding: utf-8 -*-
"""
===================================
股票数据服务层
===================================

职责：
1. 封装股票数据获取逻辑
2. 提供实时行情和历史数据接口

取数经端口注入：实时行情走 :class:`~src.application.quote.ports.RealtimeQuotePort`，
历史 K 线复用 :class:`~src.application.quote.service.QuoteService`（与行情用例共享同一
``QuoteProviderPort`` 取数链路，不再各自实现一份 K 线抓取），应用层不直接依赖
``data_provider``。本服务不持有日线仓储：历史 K 线完全经 ``QuoteService`` 取数，原
``self.repo = StockRepository()`` 为无消费者的死依赖，已于 P3/P4 持久化收口 PP-6 删除。
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from src.application.quote.ports import RealtimeQuotePort
from src.application.quote.service import QuoteService

logger = logging.getLogger(__name__)


class StockService:
    """
    股票数据服务

    封装股票数据获取的业务逻辑
    """

    def __init__(self, quote_service: QuoteService, realtime_port: RealtimeQuotePort):
        """初始化股票数据服务。

        Args:
            quote_service: 行情用例，历史 K 线复用其 ``get_kline`` 取数与整形
            realtime_port: 实时行情取数端口
        """
        self._quote_service = quote_service
        self._realtime_port = realtime_port

    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票实时行情

        Args:
            stock_code: 股票代码

        Returns:
            实时行情数据字典
        """
        try:
            quote = self._realtime_port.fetch_realtime_quote(stock_code=stock_code)

            if quote is None:
                logger.warning(f"获取 {stock_code} 实时行情失败")
                return None

            # 端口返回 UnifiedRealtimeQuote 的字段字典（源字段名），
            # 字段映射: 源字段 -> API 响应
            # - code -> stock_code
            # - name -> stock_name
            # - price -> current_price
            # - change_amount -> change
            # - change_pct -> change_percent
            # - open_price -> open
            # - high -> high
            # - low -> low
            # - pre_close -> prev_close
            # - volume -> volume
            # - amount -> amount
            return {
                "stock_code": quote.get("code", stock_code),
                "stock_name": quote.get("name", None),
                "current_price": quote.get("price", 0.0) or 0.0,
                "change": quote.get("change_amount", None),
                "change_percent": quote.get("change_pct", None),
                "open": quote.get("open_price", None),
                "high": quote.get("high", None),
                "low": quote.get("low", None),
                "prev_close": quote.get("pre_close", None),
                "volume": quote.get("volume", None),
                "amount": quote.get("amount", None),
                "turnover_rate": quote.get("turnover_rate", None),
                "total_mv": quote.get("total_mv", None),
                "update_time": datetime.now().isoformat(),
            }

        except ImportError:
            logger.warning("DataFetcherManager 未找到，使用占位数据")
            return self._get_placeholder_quote(stock_code)
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}", exc_info=True)
            return None

    def get_history_data(
        self,
        stock_code: str,
        period: str = "daily",
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取股票历史行情

        Args:
            stock_code: 股票代码
            period: K 线周期 (daily/weekly/monthly)
            days: 获取天数

        Returns:
            历史行情数据字典

        Raises:
            ValueError: 当 period 不是 daily 时抛出（weekly/monthly 暂未实现）
        """
        # 验证 period 参数，只支持 daily
        if period != "daily":
            raise ValueError(
                f"暂不支持 '{period}' 周期，目前仅支持 'daily'。"
                "weekly/monthly 聚合功能将在后续版本实现。"
            )

        try:
            # 复用行情用例的 K 线取数链路（同一 QuoteProviderPort），
            # 不再单独实现一份 K 线抓取；成交量整形（股 -> 手）沿用 QuoteService 契约。
            payload = self._quote_service.get_kline(
                stock_code=stock_code,
                period="daily",
                limit=days,
            )
            rows = payload.get("data") or []
            stock_name = payload.get("stock_name") or None

            # 转换为响应格式（键与 KLineData 契约一致）
            data = [
                {
                    "date": row.get("date"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                    "volume": row.get("volume"),
                    "amount": row.get("amount"),
                    "change_percent": row.get("change_percent"),
                }
                for row in rows
            ]

            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "period": period,
                "data": data,
            }

        except ImportError:
            logger.warning("DataFetcherManager 未找到，返回空数据")
            return {"stock_code": stock_code, "period": period, "data": []}
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}", exc_info=True)
            return {"stock_code": stock_code, "period": period, "data": []}

    def _get_placeholder_quote(self, stock_code: str) -> Dict[str, Any]:
        """
        获取占位行情数据（用于测试）

        Args:
            stock_code: 股票代码

        Returns:
            占位行情数据
        """
        return {
            "stock_code": stock_code,
            "stock_name": f"股票{stock_code}",
            "current_price": 0.0,
            "change": None,
            "change_percent": None,
            "open": None,
            "high": None,
            "low": None,
            "prev_close": None,
            "volume": None,
            "amount": None,
            "update_time": datetime.now().isoformat(),
        }
