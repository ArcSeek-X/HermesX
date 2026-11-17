"""TickFlow 日线协议与字段转换；共享客户端和状态仍由原 Fetcher 持有。"""

from typing import Iterable, Dict, List
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger("data_provider.tickflow_fetcher")

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import pandas as pd

from data_provider.common.errors import DataFetchError
from data_provider.common.fetcher_contract import STANDARD_COLUMNS
from src.domain.market.stock_codes import normalize_stock_code


@dataclass(frozen=True)
class TickFlowDailySource:
    """只使用日线所需回调，不持有宿主或新建缓存、连接及限流状态。"""

    to_tickflow_symbol: Callable[[str], Optional[str]]
    daily_cache_key: Callable[[str, str, str], Tuple[str, str, str, str]]
    get_daily_cache: Callable[[Tuple[str, str, str, str]], Optional[pd.DataFrame]]
    get_client: Callable[[], Any]
    daily_kline_count: Callable[[str, str], int]
    date_to_ms: Callable[..., int]
    adjust: Callable[[], str]
    prepare_daily_frame: Callable[..., pd.DataFrame]
    set_daily_cache: Callable[[Tuple[str, str, str, str], pd.DataFrame], None]
    coerce_frame: Callable[[Any], pd.DataFrame]
    extract_date_series: Callable[[pd.DataFrame], pd.Series]
    cn_lots_to_shares: Callable[..., Any]
    ratio_series_to_percent: Callable[[pd.Series], pd.Series]

    def fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """按代码与日期区间向 TickFlow 请求原始 K 线数据。"""
        symbol = self.to_tickflow_symbol(stock_code)
        if not symbol:
            raise DataFetchError("TickFlowFetcher only supports A-share/ETF symbols")

        cache_key = self.daily_cache_key(symbol, start_date, end_date)
        cached = self.get_daily_cache(cache_key)
        if cached is not None:
            return cached

        client = self.get_client()
        if client is None:
            raise DataFetchError("TickFlow API key is not configured")

        request_count = self.daily_kline_count(start_date, end_date)
        try:
            df = client.klines.get(
                symbol,
                period="1d",
                count=request_count,
                start_time=self.date_to_ms(start_date),
                end_time=self.date_to_ms(end_date, end_of_day=True),
                adjust=self.adjust(),
                as_dataframe=True,
            )
        except Exception as exc:
            raise DataFetchError(f"TickFlow daily K-line request failed: {exc}") from exc

        raw_df = self.prepare_daily_frame(
            df,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            count=request_count,
            context="single",
        )
        self.set_daily_cache(cache_key, raw_df)
        return raw_df.copy()

    def normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """将原始行情帧强制为标准列与数值类型。"""
        raw = self.coerce_frame(df)
        if raw.empty:
            return pd.DataFrame(columns=["code", *STANDARD_COLUMNS])

        normalized = pd.DataFrame()
        normalized["date"] = self.extract_date_series(raw)
        normalized["code"] = normalize_stock_code(stock_code)
        for column in ("open", "high", "low", "close", "amount"):
            normalized[column] = pd.to_numeric(raw.get(column), errors="coerce")

        # TickFlow daily volume is in lots for A-shares; project standard is shares.
        normalized["volume"] = self.cn_lots_to_shares(raw.get("volume"))

        if "pct_chg" in raw.columns:
            normalized["pct_chg"] = pd.to_numeric(raw["pct_chg"], errors="coerce")
        elif "change_pct" in raw.columns:
            normalized["pct_chg"] = self.ratio_series_to_percent(raw["change_pct"])
        else:
            close = pd.to_numeric(normalized["close"], errors="coerce")
            normalized["pct_chg"] = close.pct_change().fillna(0.0) * 100.0

        normalized = normalized.dropna(subset=["date", "close", "volume"])
        normalized = normalized.sort_values("date", ascending=True).reset_index(drop=True)
        return normalized[["code", *STANDARD_COLUMNS]]



@dataclass(frozen=True)
class TickFlowDailyPrefetch:
    """原能力实现；不接收整个 Fetcher，不拥有第二份客户端或缓存。"""

    use_capability_available: Callable
    use_daily_cache_key: Callable
    use_daily_kline_count: Callable
    use_date_to_ms: Callable
    use_dedupe_symbols: Callable
    use_get_client: Callable
    use_is_permission_error: Callable
    use_iter_batch_frames: Callable
    use_mark_capability: Callable
    use_prepare_daily_frame: Callable
    use_set_daily_cache: Callable
    read_batch_daily_enabled: Callable
    read_batch_size: Callable
    read_kline_adjust: Callable
    read_global_logger: Callable
    read_global_datetime: Callable
    read_global_timedelta: Callable
    read_global_MAX_DAILY_PREFETCH_LOOKBACK_DAYS: Callable

    def prefetch_daily_klines(
        self,
        stock_codes: Iterable[str],
        *,
        days: int = 30,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """Batch-prefetch daily K-lines into the per-process raw cache.

        Args:
            stock_codes: Project stock codes to prefetch.
            days: Target trading days to cover. When start_date is omitted,
                up to days * 2 calendar days are fetched, capped at 730 days.
            start_date: Optional YYYY-MM-DD lower bound.
            end_date: Optional YYYY-MM-DD upper bound.
        """
        if not self.read_batch_daily_enabled() or not self.use_capability_available(
            "batch_daily"
        ):
            return 0
        try:
            requested_days = int(days)
        except (TypeError, ValueError):
            self.read_global_logger().info(
                "[TickFlowFetcher] skip daily K-line prefetch because days is invalid: %r",
                days,
            )
            return 0
        if requested_days <= 0:
            self.read_global_logger().info(
                "[TickFlowFetcher] skip daily K-line prefetch because days must be positive: %r",
                days,
            )
            return 0
        client = self.use_get_client()
        if client is None:
            return 0
        if end_date is None:
            end_date = self.read_global_datetime().now().strftime("%Y-%m-%d")
        if start_date is None:
            lookback_days = min(
                requested_days * 2, self.read_global_MAX_DAILY_PREFETCH_LOOKBACK_DAYS()
            )
            start_dt = self.read_global_datetime().strptime(
                end_date, "%Y-%m-%d"
            ) - self.read_global_timedelta()(days=lookback_days)
            start_date = start_dt.strftime("%Y-%m-%d")
        symbols = self.use_dedupe_symbols(stock_codes)
        if not symbols:
            return 0
        batch_count = (
            len(symbols) + self.read_batch_size() - 1
        ) // self.read_batch_size()
        cached_count = 0
        for offset in range(0, len(symbols), self.read_batch_size()):
            batch_symbols = symbols[offset : offset + self.read_batch_size()]
            try:
                request_count = self.use_daily_kline_count(start_date, end_date)
                batch_result = client.klines.batch(
                    batch_symbols,
                    period="1d",
                    count=request_count,
                    start_time=self.use_date_to_ms(start_date),
                    end_time=self.use_date_to_ms(end_date, end_of_day=True),
                    adjust=self.read_kline_adjust(),
                    as_dataframe=True,
                )
                self.use_mark_capability("batch_daily", True)
            except Exception as exc:
                if self.use_is_permission_error(exc):
                    self.use_mark_capability("batch_daily", False)
                    self.read_global_logger().info(
                        "[TickFlowFetcher] batch daily K-line is not available; fallback to single requests"
                    )
                    self.read_global_logger().info(
                        "[TickFlowFetcher] batch daily prefetch complete: cached=%d total=%d batches=%d",
                        cached_count,
                        len(symbols),
                        batch_count,
                    )
                    return cached_count
                self.read_global_logger().warning(
                    "[TickFlowFetcher] batch daily K-line failed: %s", exc
                )
                continue
            for symbol, df in self.use_iter_batch_frames(batch_result):
                if not symbol:
                    continue
                cache_key = self.use_daily_cache_key(symbol, start_date, end_date)
                try:
                    frame = self.use_prepare_daily_frame(
                        df,
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        count=request_count,
                        context="batch",
                    )
                except DataFetchError:
                    continue
                if frame.empty:
                    continue
                self.use_set_daily_cache(cache_key, frame)
                cached_count += 1
        self.read_global_logger().info(
            "[TickFlowFetcher] batch daily prefetch complete: cached=%d total=%d batches=%d",
            cached_count,
            len(symbols),
            batch_count,
        )
        return cached_count


_MIN_DAILY_KLINE_COUNT = 30


_MAX_DAILY_KLINE_COUNT = 10000


_DAILY_KLINE_COUNT_MULTIPLIER = 1.8


_DAILY_KLINE_COUNT_BUFFER = 20


def date_to_ms(date_str: str, *, end_of_day: bool=False, zone_info) -> int:
    """将日期字符串转为毫秒时间戳（可选当日收盘）。"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end_of_day:
        dt = dt + timedelta(days=1) - timedelta(milliseconds=1)
    if zone_info is not None:
        dt = dt.replace(tzinfo=zone_info("Asia/Shanghai"))
    else:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
    return int(dt.timestamp() * 1000)



def extract_date_series(raw: pd.DataFrame) -> pd.Series:
    """从原始数据提取并规范化日期序列。"""
    if "date" in raw.columns:
        return pd.to_datetime(raw["date"], errors="coerce").dt.normalize()
    if "trade_date" in raw.columns:
        return pd.to_datetime(raw["trade_date"], errors="coerce").dt.normalize()
    for column in ("timestamp", "time", "ts"):
        if column in raw.columns:
            numeric = pd.to_numeric(raw[column], errors="coerce")
            return pd.to_datetime(numeric, unit="ms", errors="coerce").dt.normalize()
    return pd.Series(pd.NaT, index=raw.index)



def daily_kline_count(start_date: str, end_date: str) -> int:
    """估算日期区间内的交易日数量。"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        calendar_days = max(1, (end - start).days + 1)
    except (TypeError, ValueError):
        calendar_days = 365
    estimated = int(calendar_days * _DAILY_KLINE_COUNT_MULTIPLIER) + _DAILY_KLINE_COUNT_BUFFER
    return max(_MIN_DAILY_KLINE_COUNT, min(_MAX_DAILY_KLINE_COUNT, estimated))



def prepare_daily_frame(value: Any, *, symbol: str, start_date: str, end_date: str, count: int, context: str, use_coerce_frame, use_extract_date_series, use_is_daily_frame_truncated) -> pd.DataFrame:
    """准备日线帧并做日期截断与去重。"""
    frame = use_coerce_frame(value)
    if frame.empty:
        return frame

    dates = use_extract_date_series(frame)
    valid_dates = dates.dropna()
    if valid_dates.empty:
        logger.warning(
            "[TickFlowFetcher] daily K-line response has no usable dates: symbol=%s context=%s rows=%d count=%d",
            symbol,
            context,
            len(frame),
            count,
        )
        return pd.DataFrame(columns=frame.columns)

    if use_is_daily_frame_truncated(
        dates=valid_dates,
        start_date=start_date,
        end_date=end_date,
        count=count,
        returned_rows=len(frame),
    ):
        first_date = valid_dates.min().strftime("%Y-%m-%d")
        last_date = valid_dates.max().strftime("%Y-%m-%d")
        logger.warning(
            "[TickFlowFetcher] reject incomplete daily K-line response: symbol=%s context=%s "
            "start=%s end=%s first=%s last=%s rows=%d count=%d reason=count_cap",
            symbol,
            context,
            start_date,
            end_date,
            first_date,
            last_date,
            len(frame),
            count,
        )
        raise DataFetchError(
            "TickFlow daily K-line response may be truncated by count: "
            f"symbol={symbol} start={start_date} end={end_date} rows={len(frame)} count={count}"
        )

    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    in_range = dates.notna() & (dates >= start) & (dates <= end)
    if not in_range.any():
        return pd.DataFrame(columns=frame.columns)
    return frame.loc[in_range].reset_index(drop=True)



def is_daily_frame_truncated(*, dates: pd.Series, start_date: str, end_date: str, count: int, returned_rows: int, use_first_trading_date_on_or_after) -> bool:
    """判断日线返回是否被单次上限截断。"""
    if returned_rows < count:
        return False
    try:
        requested_start = datetime.strptime(start_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False

    first_expected = use_first_trading_date_on_or_after(requested_start)
    first_returned = dates.min().to_pydatetime().replace(tzinfo=None)
    return first_returned > first_expected



def first_trading_date_on_or_after(start_date: datetime, *, calendars) -> datetime:
    """返回不早于给定日期的首个交易日。"""
    if calendars is not None:
        try:
            cal = calendars.get_calendar("XSHG")
            session = cal.date_to_session(start_date.date(), direction="next")
            return datetime.combine(session.date(), datetime.min.time())
        except Exception:
            pass
    current = start_date
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current



def dedupe_symbols(stock_codes: Iterable[str], *, use_to_tickflow_symbol) -> List[str]:
    """对符号列表去重并保持顺序。"""
    symbols: List[str] = []
    seen = set()
    for stock_code in stock_codes:
        symbol = use_to_tickflow_symbol(stock_code)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)
    return symbols



def iter_batch_frames(batch_result: Any) -> Iterable[Tuple[str, Any]]:
    """迭代批量请求结果中的各符号 DataFrame。"""
    if isinstance(batch_result, dict):
        for symbol, df in batch_result.items():
            yield str(symbol).upper(), df
        return

    if isinstance(batch_result, pd.DataFrame):
        if "symbol" not in batch_result.columns:
            return
        for symbol, group in batch_result.groupby("symbol"):
            yield str(symbol).upper(), group.reset_index(drop=True)
        return

    if isinstance(batch_result, list):
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in batch_result:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or "").upper()
            if not symbol:
                continue
            grouped.setdefault(symbol, []).append(item)
        for symbol, rows in grouped.items():
            yield symbol, pd.DataFrame(rows)

