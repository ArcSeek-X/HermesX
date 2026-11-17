"""Finnhub 实时请求与载荷适配；SDK、缓存和请求状态由原宿主维护。"""

from dataclasses import dataclass
import logging
from typing import Any, Callable, Optional

from data_provider.realtime.types import UnifiedRealtimeQuote, RealtimeSource

logger = logging.getLogger("data_provider.finnhub_fetcher")


@dataclass(frozen=True)
class FinnhubRealtimeOperations:
    """显式绑定所需能力，不新建宿主、缓存、SDK 或熔断实例。"""

    use_is_us_stock: Callable
    use_random_sleep: Callable
    current_api_key: Callable[[], Any]
    read_requests: Callable[[], Any]
    read_finnhub_base_url: Callable[[], Any]

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """获取美股实时报价并转换为统一行情结构；无 key 或非美股返回 None。"""
        if not self.current_api_key() or not self.use_is_us_stock(stock_code):
            return None

        symbol = stock_code.strip().upper()
        try:
            self.use_random_sleep(0.3, 0.8)
            resp = self.read_requests().get(
                f"{self.read_finnhub_base_url()}/quote",
                params={"symbol": symbol, "token": self.current_api_key()},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[Finnhub] Realtime quote failed for {symbol}: {e}")
            return None

        price = data.get("c")
        if not price:
            return None

        prev_close = data.get("pc", 0)
        change_pct = data.get("dp")
        change_amount = data.get("d")
        high = data.get("h")
        low = data.get("l")
        open_price = data.get("o")

        amplitude = None
        if high and low and prev_close and prev_close > 0:
            amplitude = round((high - low) / prev_close * 100, 2)

        return UnifiedRealtimeQuote(
            code=symbol,
            source=RealtimeSource.FALLBACK,
            price=price,
            change_pct=round(change_pct, 2) if change_pct is not None else None,
            change_amount=round(change_amount, 4) if change_amount is not None else None,
            volume=data.get("v"),
            amount=None,
            volume_ratio=None,
            turnover_rate=None,
            amplitude=amplitude,
            open_price=open_price,
            high=high,
            low=low,
            pre_close=prev_close,
        )
