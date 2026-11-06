"""分析日线选源与回退协调；通过窄操作集合使用管理器拥有的资源。

调用方负责代码归一、市场识别和可用源快照。此模块不创建 Manager、SDK、
缓存、熔断器或锁，不反向调用门面，也不接收整个管理器对象。
"""

from dataclasses import dataclass
import logging
import time
from typing import Any, Callable, List, Optional, Tuple

import pandas as pd

from data_provider.common.errors import DataFetchError, summarize_exception
from data_provider.common.fetcher_contract import BaseFetcher

logger = logging.getLogger("data_provider.base")


@dataclass(frozen=True)
class DailyHistoryRequest:
    """已经过代码归一与市场识别的分析日线请求。"""

    stock_code: str
    start_date: Optional[str]
    end_date: Optional[str]
    days: int
    market: str
    is_us_index: bool


@dataclass(frozen=True)
class DailyHistoryOperations:
    """仅开放日线协调所需操作，不持有额外状态或整个宿主。"""

    invoke: Callable[..., Any]
    available: Callable[[BaseFetcher, str], bool]
    unavailable_error: Callable[[BaseFetcher], str]
    succeeded: Callable[[BaseFetcher, str], None]
    failed: Callable[[BaseFetcher, str, str], None]
    longbridge_preferred: Callable[..., bool]
    started: Callable[..., None]
    finished: Callable[..., None]


def fetch_daily_history(
    request: DailyHistoryRequest,
    fetchers: List[BaseFetcher],
    operations: DailyHistoryOperations,
    *,
    request_start: float,
) -> Tuple[pd.DataFrame, str]:
    """按原市场路由执行一次日线请求，保持空结果、诊断和全源失败语义。"""
    stock_code = request.stock_code
    start_date = request.start_date
    end_date = request.end_date
    days = request.days
    market = request.market
    is_us_index = request.is_us_index
    is_us = market == "us"
    is_hk = market == "hk"
    is_tw = market == "tw"
    errors = []
    total_fetchers = len(fetchers)

    if total_fetchers == 0:
        market_label = "美股指数" if is_us_index else "美股" if is_us else "港股" if is_hk else "台股" if is_tw else "A股"
        error_summary = f"{market_label} {stock_code} 获取失败:\n暂无可用数据源"
        logger.error(f"[数据源终止] {stock_code} 获取失败: {error_summary}")
        raise DataFetchError(error_summary)

    # 美股（含美股指数）使用专用路由；港股走下方通用数据源循环
    # Failover chain: Finnhub(P2) -> AlphaVantage(P3) -> Yfinance(P4) -> Longbridge(P5)
    # When Longbridge preferred: Longbridge -> Finnhub -> AlphaVantage -> Yfinance
    if is_us:
        prefer_lb = operations.longbridge_preferred(capability="daily_data") and not is_us_index
        if is_us_index:
            # 指数始终 YFinance 首选（Longbridge 不提供指数K线）
            source_order = ["YfinanceFetcher", "FinnhubFetcher"]
        elif prefer_lb:
            source_order = ["LongbridgeFetcher", "FinnhubFetcher", "AlphaVantageFetcher", "YfinanceFetcher"]
        else:
            source_order = ["FinnhubFetcher", "AlphaVantageFetcher", "YfinanceFetcher", "LongbridgeFetcher"]
        market_label = "美股指数" if is_us_index else "美股"

        for order_index, src_name in enumerate(source_order):
            fallback_to = (
                source_order[order_index + 1]
                if order_index + 1 < len(source_order)
                else None
            )
            for attempt, fetcher in enumerate(fetchers, start=1):
                if fetcher.name != src_name:
                    continue
                if not operations.available(fetcher, market):
                    errors.append(operations.unavailable_error(fetcher))
                    break
                attempt_start = time.time()
                try:
                    role = "首选" if src_name == source_order[0] else "兜底"
                    logger.info(
                        f"[数据源尝试 {attempt}/{total_fetchers}] [{fetcher.name}] "
                        f"{market_label} {stock_code} {role}路由..."
                    )
                    operations.started(
                        data_type="daily_data",
                        provider=fetcher.name,
                        operation="get_daily_data",
                    )
                    df = operations.invoke(
                        fetcher,
                        "get_daily_data",
                        stock_code=stock_code,
                        start_date=start_date,
                        end_date=end_date,
                        days=days,
                    )
                    if df is not None and not df.empty:
                        duration_ms = int((time.time() - attempt_start) * 1000)
                        operations.finished(
                            data_type="daily_data",
                            provider=fetcher.name,
                            operation="get_daily_data",
                            success=True,
                            latency_ms=duration_ms,
                            record_count=len(df),
                        )
                        elapsed = time.time() - request_start
                        logger.info(
                            f"[数据源完成] {stock_code} 使用 [{fetcher.name}] 获取成功: "
                            f"rows={len(df)}, elapsed={elapsed:.2f}s"
                        )
                        operations.succeeded(fetcher, market)
                        return df, fetcher.name
                    duration_ms = int((time.time() - attempt_start) * 1000)
                    operations.finished(
                        data_type="daily_data",
                        provider=fetcher.name,
                        operation="get_daily_data",
                        success=False,
                        latency_ms=duration_ms,
                        error_type="empty",
                        error_message="empty result",
                        fallback_to=fallback_to,
                        record_count=0,
                    )
                    if df is not None and df.empty:
                        operations.succeeded(fetcher, market)
                except Exception as e:
                    error_type, error_reason = summarize_exception(e)
                    error_msg = f"[{fetcher.name}] ({error_type}) {error_reason}"
                    duration_ms = int((time.time() - attempt_start) * 1000)
                    operations.finished(
                        data_type="daily_data",
                        provider=fetcher.name,
                        operation="get_daily_data",
                        success=False,
                        latency_ms=duration_ms,
                        error_type=error_type,
                        error_message=error_reason,
                        fallback_to=fallback_to,
                    )
                    logger.warning(
                        f"[数据源失败 {attempt}/{total_fetchers}] [{fetcher.name}] {stock_code}: "
                        f"error_type={error_type}, reason={error_reason}"
                    )
                    operations.failed(fetcher, market, error_reason)
                    errors.append(error_msg)
                break

        error_summary = f"{market_label} {stock_code} 获取失败:\n" + "\n".join(errors)
        elapsed = time.time() - request_start
        logger.error(f"[数据源终止] {stock_code} 获取失败: elapsed={elapsed:.2f}s\n{error_summary}")
        raise DataFetchError(error_summary)

    for attempt, fetcher in enumerate(fetchers, start=1):
        if not operations.available(fetcher, market):
            errors.append(operations.unavailable_error(fetcher))
            continue
        attempt_start = time.time()
        fallback_to = fetchers[attempt].name if attempt < total_fetchers else None
        try:
            logger.info(f"[数据源尝试 {attempt}/{total_fetchers}] [{fetcher.name}] 获取 {stock_code}...")
            operations.started(
                data_type="daily_data",
                provider=fetcher.name,
                operation="get_daily_data",
            )
            df = operations.invoke(
                fetcher,
                "get_daily_data",
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                days=days
            )

            if df is not None and not df.empty:
                duration_ms = int((time.time() - attempt_start) * 1000)
                operations.finished(
                    data_type="daily_data",
                    provider=fetcher.name,
                    operation="get_daily_data",
                    success=True,
                    latency_ms=duration_ms,
                    record_count=len(df),
                )
                elapsed = time.time() - request_start
                logger.info(
                    f"[数据源完成] {stock_code} 使用 [{fetcher.name}] 获取成功: "
                    f"rows={len(df)}, elapsed={elapsed:.2f}s"
                )
                operations.succeeded(fetcher, market)
                return df, fetcher.name
            duration_ms = int((time.time() - attempt_start) * 1000)
            operations.finished(
                data_type="daily_data",
                provider=fetcher.name,
                operation="get_daily_data",
                success=False,
                latency_ms=duration_ms,
                error_type="empty",
                error_message="empty result",
                fallback_to=fallback_to,
                record_count=0,
            )
            if df is not None and df.empty:
                operations.succeeded(fetcher, market)

        except Exception as e:
            error_type, error_reason = summarize_exception(e)
            error_msg = f"[{fetcher.name}] ({error_type}) {error_reason}"
            duration_ms = int((time.time() - attempt_start) * 1000)
            operations.finished(
                data_type="daily_data",
                provider=fetcher.name,
                operation="get_daily_data",
                success=False,
                latency_ms=duration_ms,
                error_type=error_type,
                error_message=error_reason,
                fallback_to=fallback_to,
            )
            logger.warning(
                f"[数据源失败 {attempt}/{total_fetchers}] [{fetcher.name}] {stock_code}: "
                f"error_type={error_type}, reason={error_reason}"
            )
            operations.failed(fetcher, market, error_reason)
            errors.append(error_msg)
            if attempt < total_fetchers:
                next_fetcher = fetchers[attempt]
                logger.info(f"[数据源切换] {stock_code}: [{fetcher.name}] -> [{next_fetcher.name}]")
            # 继续尝试下一个数据源
            continue

    # 所有数据源都失败
    error_summary = f"所有数据源获取 {stock_code} 失败:\n" + "\n".join(errors)
    elapsed = time.time() - request_start
    logger.error(f"[数据源终止] {stock_code} 获取失败: elapsed={elapsed:.2f}s\n{error_summary}")
    raise DataFetchError(error_summary)


@dataclass(frozen=True)
class DailyEntryOperations:
    """只接受窄回调；无第二份缓存、锁、配额或默认 Manager。"""

    use_filter_daily_fetchers_for_market: Callable
    use_filter_fetchers_by_capability: Callable
    use_get_fetchers_snapshot: Callable
    read_call_fetcher_method: Callable
    read_daily_source_unavailable_error: Callable
    read_is_daily_source_available: Callable
    read_longbridge_preferred: Callable
    read_record_daily_source_failure: Callable
    read_record_daily_source_success: Callable
    global_DailyHistoryOperations: Callable
    global_DailyHistoryRequest: Callable
    global_is_hk_market: Callable
    global_is_jp_market: Callable
    global_is_kr_market: Callable
    global_is_tw_market: Callable
    global_fetch_daily_history: Callable
    global_normalize_stock_code: Callable
    global_record_provider_run: Callable
    global_record_provider_run_started: Callable
    global_time: Callable

    def get_daily_data(self, stock_code: str, start_date: Optional[str]=None, end_date: Optional[str]=None, days: int=30) -> Tuple[pd.DataFrame, str]:
        """
            获取日线数据（自动切换数据源）

            故障切换策略：
            1. 美股指数/美股股票直接路由到 YfinanceFetcher
            2. 其他代码从最高优先级数据源开始尝试
            3. 捕获异常后自动切换到下一个
            4. 记录每个数据源的失败原因
            5. 所有数据源失败后抛出详细异常

            Args:
                stock_code: 股票代码
                start_date: 开始日期
                end_date: 结束日期
                days: 获取天数

            Returns:
                Tuple[DataFrame, str]: (数据, 成功的数据源名称)

            Raises:
                DataFetchError: 所有数据源都失败时抛出
            """
        from src.domain.market.us_index_symbols import is_us_index_code, is_us_stock_code
        stock_code = self.global_normalize_stock_code()(stock_code)
        fetchers = self.use_get_fetchers_snapshot()
        request_start = self.global_time().time()
        is_us_index = is_us_index_code(stock_code)
        is_us = is_us_index or is_us_stock_code(stock_code)
        is_hk = not is_us and self.global_is_hk_market()(stock_code)
        is_jp = not is_us and (not is_hk) and self.global_is_jp_market()(stock_code)
        is_kr = not is_us and (not is_hk) and self.global_is_kr_market()(stock_code)
        is_tw = not is_us and (not is_hk) and self.global_is_tw_market()(stock_code)
        market = 'us' if is_us else 'hk' if is_hk else 'jp' if is_jp else 'kr' if is_kr else 'tw' if is_tw else 'cn'
        if market != 'cn':
            fetchers = self.use_filter_daily_fetchers_for_market(fetchers, market)
        fetchers = self.use_filter_fetchers_by_capability(fetchers, capability='daily_data')
        return self.global_fetch_daily_history()(self.global_DailyHistoryRequest()(stock_code, start_date, end_date, days, market, is_us_index), fetchers, self.global_DailyHistoryOperations()(invoke=self.read_call_fetcher_method(), available=self.read_is_daily_source_available(), unavailable_error=self.read_daily_source_unavailable_error(), succeeded=self.read_record_daily_source_success(), failed=self.read_record_daily_source_failure(), longbridge_preferred=self.read_longbridge_preferred(), started=self.global_record_provider_run_started(), finished=self.global_record_provider_run()), request_start=request_start)
