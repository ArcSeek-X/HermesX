"""Yfinance 日线请求与标准化；原 Fetcher 保留会话、重试及共享状态。"""

from dataclasses import dataclass
import logging
from typing import Callable

import pandas as pd

from data_provider.common.errors import DataFetchError
from data_provider.common.fetcher_contract import STANDARD_COLUMNS

logger = logging.getLogger("data_provider.yfinance_fetcher")


@dataclass(frozen=True)
class YfinanceDailySource:
    """通过窄回调复用宿主能力，不创建另一份 SDK 或连接状态。"""

    convert_code: Callable[[str], str]

    def fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从 Yahoo Finance 获取原始数据

        使用 yfinance.download() 获取历史数据

        流程：
        1. 转换股票代码格式
        2. 调用 yfinance API
        3. 处理返回数据
        """
        import yfinance as yf

        # 转换代码格式
        yf_code = self.convert_code(stock_code)

        logger.debug(f"调用 yfinance.download({yf_code}, {start_date}, {end_date})")

        try:
            # 使用 yfinance 下载数据
            df = yf.download(
                tickers=yf_code,
                start=start_date,
                end=end_date,
                progress=False,  # 禁止进度条
                auto_adjust=True,  # 自动调整价格（复权）
                multi_level_index=True
            )

            # 筛选出 yf_code 的列, 避免多只股票数据混淆
            if isinstance(df.columns, pd.MultiIndex) and len(df.columns) > 1:
                ticker_level = df.columns.get_level_values(1)
                mask = ticker_level == yf_code
                if mask.any():
                    df = df.loc[:, mask].copy()

            if df.empty:
                raise DataFetchError(f"Yahoo Finance 未查询到 {stock_code} 的数据")

            return df

        except Exception as e:
            if isinstance(e, DataFetchError):
                raise
            raise DataFetchError(f"Yahoo Finance 获取数据失败: {e}") from e

    @staticmethod
    def normalize_data(df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化 Yahoo Finance 数据

        yfinance 返回的列名：
        Open, High, Low, Close, Volume（索引是日期）

        注意：新版 yfinance 返回 MultiIndex 列名，如 ('Close', 'AMD')
        需要先扁平化列名再进行处理

        需要映射到标准列名：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()

        # 处理 MultiIndex 列名（新版 yfinance 返回格式）
        # 例如: ('Close', 'AMD') -> 'Close'
        if isinstance(df.columns, pd.MultiIndex):
            logger.debug("检测到 MultiIndex 列名，进行扁平化处理")
            # 取第一级列名（Price level: Close, High, Low, etc.）
            df.columns = df.columns.get_level_values(0)

        # 重置索引，将日期从索引变为列
        df = df.reset_index()

        # 列名映射（yfinance 使用首字母大写）
        column_mapping = {
            'Date': 'date',
            'Datetime': 'date',
            'datetime': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        }

        df = df.rename(columns=column_mapping)
        if 'date' not in df.columns:
            index_col = df.columns[0] if len(df.columns) else None
            if index_col is not None:
                candidate = df[index_col]
                if pd.api.types.is_datetime64_any_dtype(candidate):
                    df = df.rename(columns={index_col: 'date'})
                elif not pd.api.types.is_numeric_dtype(candidate):
                    parsed_dates = pd.to_datetime(candidate, errors='coerce')
                    if parsed_dates.notna().any():
                        df = df.rename(columns={index_col: 'date'})
                        df['date'] = parsed_dates

        # 计算涨跌幅（因为 yfinance 不直接提供）
        if 'close' in df.columns:
            df['pct_chg'] = df['close'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].fillna(0).round(2)

        # 计算成交额（yfinance 不提供，使用估算值）
        # 成交额 ≈ 成交量 * 平均价格
        if 'volume' in df.columns and 'close' in df.columns:
            df['amount'] = df['volume'] * df['close']
        else:
            df['amount'] = 0

        # 添加股票代码列
        df['code'] = stock_code

        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]

        return df

