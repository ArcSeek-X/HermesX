"""Longbridge 实时请求与载荷适配；SDK、缓存和请求状态由原宿主维护。"""

from dataclasses import dataclass
import logging
from typing import Callable, Optional

from data_provider.realtime.types import UnifiedRealtimeQuote, RealtimeSource

logger = logging.getLogger("data_provider.longbridge_fetcher")


@dataclass(frozen=True)
class LongbridgeRealtimeOperations:
    """显式绑定所需能力，不新建宿主、缓存、SDK 或熔断实例。"""

    use_compute_volume_ratio: Callable
    use_get_ctx: Callable
    use_get_static_info: Callable
    use_is_connection_error: Callable
    use_mark_connection_cooldown: Callable
    use_is_available_for_request: Callable
    call_to_longbridge_symbol: Callable
    call_safe_float: Callable

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """Fetch realtime quote from Longbridge, computing derived fields."""
        if not self.use_is_available_for_request("realtime_quote"):
            return None

        symbol = self.call_to_longbridge_symbol(stock_code)
        if symbol is None:
            logger.debug(f"[Longbridge] 无法转换代码: {stock_code}")
            return None

        ctx = self.use_get_ctx()
        if ctx is None:
            return None

        try:
            quotes = ctx.quote([symbol])
            if not quotes:
                return None
            q = quotes[0]
        except Exception as e:
            logger.info(f"[Longbridge] quote({symbol}) 失败: {e}")
            if self.use_is_connection_error(e):
                self.use_mark_connection_cooldown(e)
            return None

        price = self.call_safe_float(getattr(q, "last_done", None))
        if price is None or price <= 0:
            return None

        prev_close = self.call_safe_float(getattr(q, "prev_close", None))
        open_price = self.call_safe_float(getattr(q, "open", None))
        high = self.call_safe_float(getattr(q, "high", None))
        low = self.call_safe_float(getattr(q, "low", None))
        volume = int(getattr(q, "volume", 0) or 0)
        turnover = self.call_safe_float(getattr(q, "turnover", None))

        change_amount = None
        change_pct = None
        amplitude = None
        if prev_close and prev_close > 0:
            change_amount = round(price - prev_close, 4)
            change_pct = round((price - prev_close) / prev_close * 100, 2)
            if high is not None and low is not None:
                amplitude = round((high - low) / prev_close * 100, 2)

        # Fetch static info for derived fields
        static = self.use_get_static_info(symbol)

        turnover_rate = None
        pe_ratio = None
        pb_ratio = None
        total_mv = None
        circ_mv = None
        name = ""

        if static is not None:
            name = getattr(static, "name_cn", "") or getattr(static, "name_en", "") or ""
            circulating = int(getattr(static, "circulating_shares", 0) or 0)
            total_shares = int(getattr(static, "total_shares", 0) or 0)
            eps_ttm = self.call_safe_float(getattr(static, "eps_ttm", None))
            eps_plain = self.call_safe_float(getattr(static, "eps", None))
            bps = self.call_safe_float(getattr(static, "bps", None))

            # US names often report circulating_shares=0 while total_shares is set — use total for turnover.
            shares_for_turnover = circulating if circulating > 0 else total_shares
            if shares_for_turnover > 0 and volume > 0:
                turnover_rate = round(volume / shares_for_turnover * 100, 4)
            elif volume > 0:
                logger.debug(
                    "[Longbridge] %s 无法计算换手率: volume=%s circulating=%s total_shares=%s",
                    symbol,
                    volume,
                    circulating,
                    total_shares,
                )

            eps_for_pe = None
            if eps_ttm is not None and eps_ttm > 0:
                eps_for_pe = eps_ttm
            elif eps_plain is not None and eps_plain > 0:
                eps_for_pe = eps_plain
            if eps_for_pe:
                pe_ratio = round(price / eps_for_pe, 2)

            if bps is not None and bps > 0:
                pb_ratio = round(price / bps, 2)
            if total_shares > 0:
                total_mv = round(price * total_shares, 2)
            if circulating > 0:
                circ_mv = round(price * circulating, 2)

        volume_ratio = self.use_compute_volume_ratio(symbol, volume)

        quote = UnifiedRealtimeQuote(
            code=stock_code,
            name=name,
            source=RealtimeSource.LONGBRIDGE,
            price=price,
            change_pct=change_pct,
            change_amount=change_amount,
            volume=volume if volume > 0 else None,
            amount=turnover,
            volume_ratio=volume_ratio,
            turnover_rate=turnover_rate,
            amplitude=amplitude,
            open_price=open_price,
            high=high,
            low=low,
            pre_close=prev_close,
            pe_ratio=pe_ratio,
            pb_ratio=pb_ratio,
            total_mv=total_mv,
            circ_mv=circ_mv,
        )

        logger.info(
            f"[Longbridge] {symbol} 行情获取成功: " f"价格={price}, 量比={volume_ratio}, 换手率={turnover_rate}"
        )
        return quote
