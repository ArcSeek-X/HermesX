"""Efinance 分析日线协议及字段标准化；SDK/节流仍由旧实例显式提供。

同一个 EfinanceFetcher 的日线和实时等能力继续共享 _last_request_time，
此组件不另建 SDK 客户端、锁、缓存或重试策略。
"""


from dataclasses import dataclass
import logging
import time
from typing import Callable, Tuple
from src.domain.market.stock_codes import normalize_stock_code

import pandas as pd

from data_provider.common.errors import DataFetchError, RateLimitError
from data_provider.clients.efinance import _classify_eastmoney_error
from data_provider.common.fetcher_contract import STANDARD_COLUMNS

logger = logging.getLogger("data_provider.efinance_fetcher")
EASTMONEY_HISTORY_ENDPOINT = "push2his.eastmoney.com/api/qt/stock/kline/get"


@dataclass(frozen=True)
class EfinanceDailySource:
    """只接收历史调用、共享请求准备、错误格式化和 ETF 代码转换能力。"""

    history_call: Callable[..., pd.DataFrame]
    prepare_request: Callable[[], None]
    history_failure: Callable[..., Tuple[str, str]]
    etf_secid: Callable[[str], str]

    def fetch_stock(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取普通 A 股历史数据
        
        数据来源：ef.stock.get_quote_history()
        
        API 参数说明：
        - stock_codes: 股票代码
        - beg: 开始日期，格式 'YYYYMMDD'
        - end: 结束日期，格式 'YYYYMMDD'
        - klt: 周期，101=日线
        - fqt: 复权方式，1=前复权
        """

        # 防封禁策略 1: 随机 User-Agent
        self.prepare_request()

        # 防封禁策略 2: 强制休眠
        # 共享节流已由 prepare_request 按原顺序执行。

        # 格式化日期（efinance 使用 YYYYMMDD 格式）
        beg_date = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')

        logger.info(f"[API调用] ef.stock.get_quote_history(stock_codes={stock_code}, "
                   f"beg={beg_date}, end={end_date_fmt}, klt=101, fqt=1)")

        api_start = time.time()
        try:
            # 调用 efinance 获取 A 股日线数据
            # klt=101 获取日线数据
            # fqt=1 获取前复权数据
            df = self.history_call(
                stock_codes=stock_code,
                beg=beg_date,
                end=end_date_fmt,
                klt=101,  # 日线
                fqt=1,    # 前复权
                timeout=60,
            )

            api_elapsed = time.time() - api_start

            # 记录返回数据摘要
            if df is not None and not df.empty:
                logger.info(
                    "[API返回] Eastmoney 历史K线成功: "
                    f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, "
                    f"range={beg_date}~{end_date_fmt}, rows={len(df)}, elapsed={api_elapsed:.2f}s"
                )
                logger.info(f"[API返回] 列名: {list(df.columns)}")
                if '日期' in df.columns:
                    logger.info(f"[API返回] 日期范围: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[API返回] 最新3条数据:\n{df.tail(3).to_string()}")
            else:
                logger.warning(
                    "[API返回] Eastmoney 历史K线为空: "
                    f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, "
                    f"range={beg_date}~{end_date_fmt}, elapsed={api_elapsed:.2f}s"
                )

            return df

        except Exception as e:
            api_elapsed = time.time() - api_start
            category, failure_message = self.history_failure(
                stock_code=stock_code,
                beg_date=beg_date,
                end_date=end_date_fmt,
                exc=e,
                elapsed=api_elapsed,
            )

            if category == "rate_limit_or_anti_bot":
                logger.warning(failure_message)
                raise RateLimitError(f"efinance 可能被限流: {failure_message}") from e

            logger.error(failure_message)
            raise DataFetchError(f"efinance 获取数据失败: {failure_message}") from e


    def fetch_etf(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取 ETF 基金历史数据

        Exchange-traded ETFs have OHLCV data just like regular stocks, so we use
        ef.stock.get_quote_history (the stock K-line API) which returns full
        open/high/low/close/volume data.

        Previously this method used ef.fund.get_quote_history which only returns
        NAV data (单位净值/累计净值) without volume or OHLC, causing:
        - Issue #541: 'got an unexpected keyword argument beg'
        - Issue #527: ETF volume/turnover always showing 0

        Args:
            stock_code: ETF code, e.g. '512400', '159883', '515120'
            start_date: Start date, format 'YYYY-MM-DD'
            end_date: End date, format 'YYYY-MM-DD'

        Returns:
            ETF historical OHLCV DataFrame
        """

        # Anti-ban strategy 1: random User-Agent
        self.prepare_request()

        # Anti-ban strategy 2: enforce rate limit
        # 共享节流已由 prepare_request 按原顺序执行。

        # Format dates (efinance uses YYYYMMDD)
        beg_date = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')
        secid = self.etf_secid(stock_code)

        logger.info(
            f"[API调用] ef.stock.get_quote_history(stock_codes={secid}, "
            f"beg={beg_date}, end={end_date_fmt}, klt=101, fqt=1, "
            f"quote_id_mode=True, use_id_cache=False)  [ETF stock_code={stock_code}]"
        )

        api_start = time.time()
        try:
            # ETFs are exchange-traded securities; use the stock API to get full OHLCV data
            df = self.history_call(
                stock_codes=secid,
                beg=beg_date,
                end=end_date_fmt,
                klt=101,  # daily
                fqt=1,    # forward-adjusted
                quote_id_mode=True,
                use_id_cache=False,
                timeout=60,
            )

            api_elapsed = time.time() - api_start

            if df is not None and not df.empty:
                logger.info(
                    "[API返回] Eastmoney 历史K线成功 [ETF]: "
                    f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, secid={secid}, "
                    f"range={beg_date}~{end_date_fmt}, rows={len(df)}, elapsed={api_elapsed:.2f}s"
                )
                logger.info(f"[API返回] 列名: {list(df.columns)}")
                if '日期' in df.columns:
                    logger.info(f"[API返回] 日期范围: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[API返回] 最新3条数据:\n{df.tail(3).to_string()}")
            else:
                logger.warning(
                    "[API返回] Eastmoney 历史K线为空 [ETF]: "
                    f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, secid={secid}, "
                    f"range={beg_date}~{end_date_fmt}, elapsed={api_elapsed:.2f}s"
                )

            return df

        except Exception as e:
            api_elapsed = time.time() - api_start
            category, failure_message = self.history_failure(
                stock_code=stock_code,
                beg_date=beg_date,
                end_date=end_date_fmt,
                exc=e,
                elapsed=api_elapsed,
                is_etf=True,
            )

            if category == "rate_limit_or_anti_bot":
                logger.warning(failure_message)
                raise RateLimitError(f"efinance 可能被限流: {failure_message}") from e

            logger.error(failure_message)
            raise DataFetchError(f"efinance 获取 ETF 数据失败: {failure_message}") from e


    @staticmethod
    def normalize_data( df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化 efinance 数据
        
        efinance 返回的列名（中文）：
        股票名称, 股票代码, 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
        
        需要映射到标准列名：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()

        # Column mapping (efinance Chinese column names -> standard English column names)
        column_mapping = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '涨跌幅': 'pct_chg',
            '股票代码': 'code',
            '股票名称': 'name',
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # Fallback: if OHLC columns are missing (e.g. very old data path), fill from close
        if 'close' in df.columns and 'open' not in df.columns:
            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']

        # Fill volume and amount if missing
        if 'volume' not in df.columns:
            df['volume'] = 0
        if 'amount' not in df.columns:
            df['amount'] = 0


        # 如果没有 code 列，手动添加
        if 'code' not in df.columns:
            df['code'] = stock_code

        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]

        return df



@dataclass(frozen=True)
class EfinanceDailyRouting:
    """原能力实现；不接收整个 Fetcher，不拥有第二份客户端或缓存。"""

    use_fetch_etf_data: Callable
    use_fetch_stock_data: Callable
    read_global_is_us_code: Callable
    read_global_is_hk_market: Callable
    read_global_is_etf_code: Callable

    def _fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        从 efinance 获取原始数据

        根据代码类型自动选择 API：
        - 美股：不支持，抛出异常让 DataFetcherManager 切换到其他数据源
        - 普通股票：使用 ef.stock.get_quote_history()
        - ETF 基金：使用 ef.stock.get_quote_history()（ETF 是交易所证券，使用股票 K 线接口）

        流程：
        1. 判断代码类型（美股/股票/ETF）
        2. 设置随机 User-Agent
        3. 执行速率限制（随机休眠）
        4. 调用对应的 efinance API
        5. 处理返回数据
        """
        if self.read_global_is_us_code()(stock_code):
            raise DataFetchError(
                f"EfinanceFetcher 不支持美股 {stock_code}，请使用 AkshareFetcher 或 YfinanceFetcher"
            )
        if self.read_global_is_hk_market()(stock_code):
            raise DataFetchError(
                f"EfinanceFetcher 不支持港股日线 {stock_code}，请使用 AkshareFetcher 或其他港股数据源"
            )
        if self.read_global_is_etf_code()(stock_code):
            return self.use_fetch_etf_data(stock_code, start_date, end_date)
        else:
            return self.use_fetch_stock_data(stock_code, start_date, end_date)


_ETF_SH_PREFIXES = ('51', '52', '56', '58')


_ETF_SZ_PREFIXES = ('15', '16', '18')


def build_eastmoney_etf_secid(stock_code: str, *, is_etf) -> str:
    """Build Eastmoney secid for A-share ETF historical K-line queries."""
    code = normalize_stock_code(stock_code)
    if not is_etf(code):
        raise DataFetchError(f"无法识别 ETF 代码 {stock_code}")
    if code.startswith(_ETF_SH_PREFIXES):
        return f"1.{code}"
    if code.startswith(_ETF_SZ_PREFIXES):
        return f"0.{code}"
    raise DataFetchError(f"无法确定 ETF {stock_code} 的 Eastmoney 市场前缀")


def build_history_failure_message(
    stock_code: str,
    beg_date: str,
    end_date: str,
    exc: Exception,
    elapsed: float,
    is_etf: bool = False,
) -> Tuple[str, str]:
    """构造历史数据获取失败提示。"""
    category, detail = _classify_eastmoney_error(exc)
    instrument_type = "ETF" if is_etf else "stock"
    message = (
        "Eastmoney 历史K线接口失败: "
        f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, "
        f"market_type={instrument_type}, range={beg_date}~{end_date}, "
        f"category={category}, error_type={type(exc).__name__}, elapsed={elapsed:.2f}s, detail={detail}"
    )
    return category, message
