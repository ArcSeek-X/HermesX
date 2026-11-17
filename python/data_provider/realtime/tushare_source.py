"""Tushare 实时请求与载荷适配；SDK、缓存和请求状态由原宿主维护。"""

from dataclasses import dataclass
import logging
from typing import Any, Callable, Optional
from src.domain.market.stock_codes import normalize_stock_code

from data_provider.realtime.types import UnifiedRealtimeQuote

logger = logging.getLogger("data_provider.tushare_fetcher")


@dataclass(frozen=True)
class TushareRealtimeOperations:
    """显式绑定所需能力，不新建宿主、缓存、SDK 或熔断实例。"""

    use_check_rate_limit: Callable
    use_convert_stock_code: Callable
    use_get_legacy_realtime_symbol: Callable
    current_api: Callable[[], Any]
    call_is_hk_market: Callable

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        获取实时行情

        策略：
        1. 优先尝试 Pro 接口（需要2000积分）：数据全，稳定性高
        2. 失败降级到旧版接口：门槛低，数据较少

        Args:
            stock_code: 股票代码

        Returns:
            UnifiedRealtimeQuote 对象，失败返回 None
        """
        if self.current_api() is None:
            return None

        # HK stocks not supported by Tushare
        if self.call_is_hk_market(stock_code):
            logger.debug(f"TushareFetcher 跳过港股实时行情 {stock_code}")
            return None

        normalized_code = normalize_stock_code(stock_code)

        from data_provider.realtime.types import RealtimeSource, safe_float, safe_int

        # 速率限制检查
        self.use_check_rate_limit()

        # 尝试 Pro 接口
        try:
            ts_code = self.use_convert_stock_code(stock_code)
            # 尝试调用 Pro 实时接口 (需要积分)
            df = self.current_api().quotation(ts_code=ts_code)

            if df is not None and not df.empty:
                row = df.iloc[0]
                logger.debug(f"Tushare Pro 实时行情获取成功: {stock_code}")

                return UnifiedRealtimeQuote(
                    code=normalized_code,
                    name=str(row.get("name", "")),
                    source=RealtimeSource.TUSHARE,
                    price=safe_float(row.get("price")),
                    change_pct=safe_float(row.get("pct_chg")),  # Pro 接口通常直接返回涨跌幅
                    change_amount=safe_float(row.get("change")),
                    volume=safe_int(row.get("vol")),
                    amount=safe_float(row.get("amount")),
                    high=safe_float(row.get("high")),
                    low=safe_float(row.get("low")),
                    open_price=safe_float(row.get("open")),
                    pre_close=safe_float(row.get("pre_close")),
                    turnover_rate=safe_float(row.get("turnover_ratio")),  # Pro 接口可能有换手率
                    pe_ratio=safe_float(row.get("pe")),
                    pb_ratio=safe_float(row.get("pb")),
                    total_mv=safe_float(row.get("total_mv")),
                )
        except Exception as e:
            # 仅记录调试日志，不报错，继续尝试降级
            logger.debug(f"Tushare Pro 实时行情不可用 (可能是积分不足): {e}")

        # 降级：尝试旧版接口
        try:
            import tushare as ts

            symbol = self.use_get_legacy_realtime_symbol(stock_code)

            # 调用旧版实时接口 (ts.get_realtime_quotes)
            df = ts.get_realtime_quotes(symbol)

            if df is None or df.empty:
                return None

            row = df.iloc[0]

            # 计算涨跌幅
            price = safe_float(row["price"])
            pre_close = safe_float(row["pre_close"])
            change_pct = 0.0
            change_amount = 0.0

            if price and pre_close and pre_close > 0:
                change_amount = price - pre_close
                change_pct = (change_amount / pre_close) * 100

            # 构建统一对象
            return UnifiedRealtimeQuote(
                code=normalized_code,
                name=str(row["name"]),
                source=RealtimeSource.TUSHARE,
                price=price,
                change_pct=round(change_pct, 2),
                change_amount=round(change_amount, 2),
                volume=safe_int(row["volume"]) // 100,  # 转换为手
                amount=safe_float(row["amount"]),
                high=safe_float(row["high"]),
                low=safe_float(row["low"]),
                open_price=safe_float(row["open"]),
                pre_close=pre_close,
            )

        except Exception as e:
            logger.warning(f"Tushare (旧版) 获取实时行情失败 {stock_code}: {e}")
            return None
