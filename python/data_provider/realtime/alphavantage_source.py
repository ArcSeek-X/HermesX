"""AlphaVantage 实时请求与载荷适配；SDK、缓存和请求状态由原宿主维护。"""

from dataclasses import dataclass
import logging
from typing import Any, Callable, Optional

from data_provider.realtime.types import UnifiedRealtimeQuote, RealtimeSource

logger = logging.getLogger("data_provider.alphavantage_fetcher")


@dataclass(frozen=True)
class AlphaVantageRealtimeOperations:
    """显式绑定所需能力，不新建宿主、缓存、SDK 或熔断实例。"""

    use_is_us_stock: Callable
    use_random_sleep: Callable
    current_api_key: Callable[[], Any]
    read_requests: Callable[[], Any]
    read_av_base_url: Callable[[], Any]

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """获取实时行情。"""
        if not self.current_api_key() or not self.use_is_us_stock(stock_code):
            return None

        symbol = stock_code.strip().upper()
        try:
            self.use_random_sleep(0.5, 1.5)
            resp = self.read_requests().get(
                self.read_av_base_url(),
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.current_api_key(),
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[AlphaVantage] Realtime quote failed for {symbol}: {e}")
            return None

        gq = data.get("Global Quote", {})
        price_str = gq.get("05. price")
        if not price_str:
            return None

        price = float(price_str)
        prev_close = float(gq.get("08. previous close", 0))
        change_pct_str = gq.get("10. change percent", "0%").replace("%", "")
        change_pct = float(change_pct_str) if change_pct_str else None

        return UnifiedRealtimeQuote(
            code=symbol,
            source=RealtimeSource.FALLBACK,
            price=price,
            change_pct=round(change_pct, 2) if change_pct is not None else None,
            change_amount=round(float(gq.get("09. change", 0)), 4),
            volume=int(float(gq.get("06. volume", 0))),
            amount=None,
            volume_ratio=None,
            turnover_rate=None,
            amplitude=None,
            open_price=float(gq.get("02. open", 0)),
            high=float(gq.get("03. high", 0)),
            low=float(gq.get("04. low", 0)),
            pre_close=prev_close,
        )
