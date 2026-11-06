"""实时行情缺字段补全及新鲜度元数据；不持有 SDK、缓存或管理器。"""

from dataclasses import dataclass
from typing import Dict

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional

logger = logging.getLogger("data_provider.base")


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 字符串。"""
    return datetime.now(timezone.utc).isoformat()


def parse_realtime_timestamp(value: Any) -> Optional[datetime]:
    """解析实时行情时间戳。"""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def realtime_fetcher_token(fetcher_name: str, **kw) -> str:
    """返回实时抓取器标识。"""
    if fetcher_name == "AkshareFetcher" and kw.get("source") == "hk":
        return "akshare_hk"
    mapping = {
        "LongbridgeFetcher": "longbridge",
        "YfinanceFetcher": "yfinance",
        "AkshareFetcher": "akshare",
        "FinnhubFetcher": "finnhub",
        "AlphaVantageFetcher": "alphavantage",
        "EfinanceFetcher": "efinance",
        "TushareFetcher": "tushare",
    }
    return mapping.get(fetcher_name, fetcher_name.replace("Fetcher", "").lower())


def enrich_realtime_quote(
    quote,
    *,
    fallback_from: Optional[str] = None,
    realtime_cache_ttl: Optional[int] = None,
    now: Callable[[], str] = utc_now_iso,
    parse: Callable[[Any], Optional[datetime]] = parse_realtime_timestamp,
):
    """Attach runtime metadata without inventing provider-side timestamps."""
    if quote is None:
        return None

    fetched_at = now()
    setattr(quote, "fetched_at", fetched_at)
    if fallback_from:
        setattr(quote, "fallback_from", str(fallback_from))

    provider_dt = parse(getattr(quote, "provider_timestamp", None))
    if provider_dt is None:
        setattr(quote, "provider_timestamp", None)
        setattr(quote, "stale_seconds", None)
        setattr(quote, "is_stale", None)
        return quote

    setattr(quote, "provider_timestamp", provider_dt.isoformat())
    fetched_dt = parse(fetched_at) or datetime.now(timezone.utc)
    stale_seconds = max(0, int((fetched_dt - provider_dt).total_seconds()))
    ttl = realtime_cache_ttl if realtime_cache_ttl is not None else 600
    setattr(quote, "stale_seconds", stale_seconds)
    setattr(quote, "is_stale", stale_seconds > int(ttl))
    return quote


def quote_needs_supplement(quote, fields: Iterable[str]) -> bool:
    """Check if any key supplementary field is still None."""
    for f in fields:
        if getattr(quote, f, None) is None:
            return True
    return False


def merge_quote_fields(primary, secondary, fields: Iterable[str]) -> list:
    """
    Copy non-None fields from *secondary* into *primary* where
    *primary* has None. Returns list of field names that were filled.
    """
    filled = []
    for f in fields:
        if getattr(primary, f, None) is None:
            val = getattr(secondary, f, None)
            if val is not None:
                setattr(primary, f, val)
                filled.append(f)
    return filled


def supplement_quote(
    stock_code: str, primary_quote, fetcher_name: str, *, needs: Callable, try_quote: Callable, merge: Callable, **kw
):
    """Supplement *primary_quote* with data from *fetcher_name*.

    If *primary_quote* is None, try *fetcher_name* as the sole source.
    Returns the (potentially enriched) quote, or None.
    """
    if primary_quote is not None:
        if not needs(primary_quote):
            return primary_quote
        try:
            secondary = try_quote(stock_code, fetcher_name, **kw)
            if secondary is not None:
                filled = merge(primary_quote, secondary)
                if filled:
                    logger.info(f"[实时行情] {stock_code} 从 {fetcher_name} 补充了: {filled}")
        except Exception as e:
            logger.debug(f"[实时行情] {stock_code} {fetcher_name} 补充失败: {e}")
        return primary_quote

    q = try_quote(stock_code, fetcher_name, **kw)
    if q is not None:
        logger.info(f"[实时行情] {stock_code} 从 {fetcher_name} 获取成功 (独立数据源)")
    return q


@dataclass(frozen=True)
class AkshareEnhancedData:
    """原能力实现；不接收整个 Fetcher，不拥有第二份客户端或缓存。"""

    use_get_chip_distribution: Callable
    use_get_daily_data: Callable
    use_get_realtime_quote: Callable
    read_global_logger: Callable

    def get_enhanced_data(self, stock_code: str, days: int = 60) -> Dict[str, Any]:
        """
        获取增强数据（历史K线 + 实时行情 + 筹码分布）

        Args:
            stock_code: 股票代码
            days: 历史数据天数

        Returns:
            包含所有数据的字典
        """
        result = {
            "code": stock_code,
            "daily_data": None,
            "realtime_quote": None,
            "chip_distribution": None,
        }
        try:
            df = self.use_get_daily_data(stock_code, days=days)
            result["daily_data"] = df
        except Exception as e:
            self.read_global_logger().error(f"获取 {stock_code} 日线数据失败: {e}")
        result["realtime_quote"] = self.use_get_realtime_quote(stock_code)
        result["chip_distribution"] = self.use_get_chip_distribution(stock_code)
        return result


@dataclass(frozen=True)
class EfinanceEnhancedData:
    """原能力实现；不接收整个 Fetcher，不拥有第二份客户端或缓存。"""

    use_get_base_info: Callable
    use_get_belong_board: Callable
    use_get_daily_data: Callable
    use_get_realtime_quote: Callable
    read_global_logger: Callable

    def get_enhanced_data(self, stock_code: str, days: int = 60) -> Dict[str, Any]:
        """
        获取增强数据（历史K线 + 实时行情 + 基本信息）

        Args:
            stock_code: 股票代码
            days: 历史数据天数

        Returns:
            包含所有数据的字典
        """
        result = {
            "code": stock_code,
            "daily_data": None,
            "realtime_quote": None,
            "base_info": None,
            "belong_board": None,
        }
        try:
            df = self.use_get_daily_data(stock_code, days=days)
            result["daily_data"] = df
        except Exception as e:
            self.read_global_logger().error(f"获取 {stock_code} 日线数据失败: {e}")
        result["realtime_quote"] = self.use_get_realtime_quote(stock_code)
        result["base_info"] = self.use_get_base_info(stock_code)
        result["belong_board"] = self.use_get_belong_board(stock_code)
        return result
