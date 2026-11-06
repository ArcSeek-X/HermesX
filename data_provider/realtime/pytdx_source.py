"""Pytdx 实时请求与载荷适配；SDK、缓存和请求状态由原宿主维护。"""

from dataclasses import dataclass
import logging
from typing import Callable, Optional
from data_provider.common.errors import DataFetchError

logger = logging.getLogger("data_provider.pytdx_fetcher")


@dataclass(frozen=True)
class PytdxRealtimeOperations:
    """显式绑定所需能力，不新建宿主、缓存、SDK 或熔断实例。"""

    use_get_market_code: Callable
    use_pytdx_session: Callable
    call_is_bse_code: Callable

    def get_realtime_quote(self, stock_code: str) -> Optional[dict]:
        """
        获取实时行情

        Args:
            stock_code: 股票代码

        Returns:
            实时行情数据字典，失败返回 None
        """
        if self.call_is_bse_code(stock_code):
            raise DataFetchError(f"PytdxFetcher 不支持北交所 {stock_code}，将自动切换其他数据源")
        try:
            market, code = self.use_get_market_code(stock_code)

            with self.use_pytdx_session() as api:
                data = api.get_security_quotes([(market, code)])

                if data and len(data) > 0:
                    quote = data[0]
                    return {
                        "code": stock_code,
                        "name": quote.get("name", ""),
                        "price": quote.get("price", 0),
                        "open": quote.get("open", 0),
                        "high": quote.get("high", 0),
                        "low": quote.get("low", 0),
                        "pre_close": quote.get("last_close", 0),
                        "volume": quote.get("vol", 0),
                        "amount": quote.get("amount", 0),
                        "bid_prices": [quote.get(f"bid{i}", 0) for i in range(1, 6)],
                        "ask_prices": [quote.get(f"ask{i}", 0) for i in range(1, 6)],
                    }
        except Exception as e:
            logger.warning(f"Pytdx 获取实时行情失败 {stock_code}: {e}")

        return None
