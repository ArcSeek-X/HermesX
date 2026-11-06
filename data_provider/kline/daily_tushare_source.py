"""Tushare 日线协议与单位转换；SDK、限额计数及重试由旧宿主持有。"""

from dataclasses import dataclass
import logging
from typing import Any, Callable

import pandas as pd

from data_provider.common.errors import DataFetchError, RateLimitError
from data_provider.common.fetcher_contract import STANDARD_COLUMNS

logger = logging.getLogger("data_provider.tushare_fetcher")


@dataclass(frozen=True)
class TushareDailySource:
    """读取同一 API 及限额实例，不复制 minute_start/call_count/date_list。"""

    get_api: Callable[[], Any]
    rate_limit: Callable[[], None]
    convert_hk: Callable[[str], str]
    convert_code: Callable[[str], str]
    is_us: Callable[[str], bool]
    is_hk: Callable[[str], bool]
    is_etf: Callable[[str], bool]

    def fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从 Tushare 获取原始数据
        
        根据代码类型选择不同接口：
        - 普通股票：daily()
        - ETF 基金：fund_daily()
        
        流程：
        1. 检查 API 是否可用
        2. 检查是否为美股（不支持）
        3. 执行速率限制检查
        4. 转换股票代码格式
        5. 根据代码类型选择接口并调用
        """
        if self.get_api() is None:
            raise DataFetchError("Tushare API 未初始化，请检查 Token 配置")

        # US stocks not supported
        if self.is_us(stock_code):
            raise DataFetchError(f"TushareFetcher 不支持美股 {stock_code}，请使用 AkshareFetcher 或 YfinanceFetcher")

        # Rate-limit check
        self.rate_limit()

        is_hk = self.is_hk(stock_code)
        # 判断是否为 ETF / 港股，以选择不同接口
        is_etf = self.is_etf(stock_code)
        if is_hk:
            ts_code = self.convert_hk(stock_code)
            api_name = "hk_daily"
        else:
            ts_code = self.convert_code(stock_code)
            api_name = "fund_daily" if is_etf else "daily"

        # Convert date format (Tushare requires YYYYMMDD)
        ts_start = start_date.replace('-', '')
        ts_end = end_date.replace('-', '')



        logger.debug(f"调用 Tushare {api_name}({ts_code}, {ts_start}, {ts_end})")

        try:
            if is_hk:
                # 港股使用 hk_daily 接口
                df = self.get_api().hk_daily(
                    ts_code=ts_code,
                    start_date=ts_start,
                    end_date=ts_end,
                )
            elif is_etf:
                # ETF uses fund_daily interface
                df = self.get_api().fund_daily(
                    ts_code=ts_code,
                    start_date=ts_start,
                    end_date=ts_end,
                )
            else:
                # Regular A-share stocks use daily interface
                df = self.get_api().daily(
                    ts_code=ts_code,
                    start_date=ts_start,
                    end_date=ts_end,
                )

            return df

        except Exception as e:
            error_msg = str(e).lower()

            # 检测配额超限
            if any(keyword in error_msg for keyword in ['quota', '配额', 'limit', '权限']):
                logger.warning(f"Tushare 配额可能超限: {e}")
                raise RateLimitError(f"Tushare 配额超限: {e}") from e

            raise DataFetchError(f"Tushare 获取数据失败: {e}") from e


    def normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化 Tushare 数据
        
        Tushare daily / fund_daily 返回的列名：
        ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
        
        需要映射到标准列名：
        date, open, high, low, close, volume, amount, pct_chg

        单位缩放仅适用于 A 股（及 ETF 等使用同一套单位的接口）：
        - vol 按「手」计，乘以 100 转为「股」
        - amount 按「千元」计，乘以 1000 转为「元」

        港股 hk_daily 返回的 vol / amount 已是可直接使用的量级，不做上述缩放。
        """
        df = df.copy()
        is_hk = self.is_hk(stock_code)

        # 列名映射
        column_mapping = {
            'trade_date': 'date',
            'vol': 'volume',
            # open, high, low, close, amount, pct_chg 列名相同
        }

        df = df.rename(columns=column_mapping)

        # 转换日期格式（YYYYMMDD -> YYYY-MM-DD）
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

        # 成交量 / 成交额：仅 A 股类接口做单位换算（港股 hk_daily 不换算）
        if 'volume' in df.columns and not is_hk:
            df['volume'] = df['volume'] * 100

        if 'amount' in df.columns and not is_hk:
            df['amount'] = df['amount'] * 1000

        # 添加股票代码列
        df['code'] = stock_code

        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]

        return df

