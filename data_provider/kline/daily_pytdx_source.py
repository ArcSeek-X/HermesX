"""Pytdx 日线请求与标准化；原 Fetcher 保留会话、重试及共享状态。"""

from dataclasses import dataclass
import logging
from typing import Any, Callable, ContextManager, Tuple

import pandas as pd

from data_provider.common.errors import DataFetchError
from data_provider.common.fetcher_contract import STANDARD_COLUMNS

logger = logging.getLogger("data_provider.pytdx_fetcher")


@dataclass(frozen=True)
class PytdxDailySource:
    """通过窄回调复用宿主能力，不创建另一份 SDK 或连接状态。"""

    market_code: Callable[[str], Tuple[int, str]]
    session: Callable[[], ContextManager[Any]]
    is_us: Callable[[str], bool]
    is_hk: Callable[[str], bool]
    is_bse: Callable[[str], bool]

    def fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从通达信获取原始数据
        
        使用 get_security_bars() 获取日线数据
        
        流程：
        1. 检查是否为美股（不支持）
        2. 使用上下文管理器管理连接
        3. 判断市场代码
        4. 调用 API 获取 K 线数据
        """
        # 美股不支持，抛出异常让 DataFetcherManager 切换到其他数据源
        if self.is_us(stock_code):
            raise DataFetchError(f"PytdxFetcher 不支持美股 {stock_code}，请使用 AkshareFetcher 或 YfinanceFetcher")

        # 港股不支持，抛出异常让 DataFetcherManager 切换到其他数据源
        if self.is_hk(stock_code):
            raise DataFetchError(f"PytdxFetcher 不支持港股 {stock_code}，请使用 AkshareFetcher")

        # 北交所不支持，抛出异常让 DataFetcherManager 切换到其他数据源
        if self.is_bse(stock_code):
            raise DataFetchError(
                f"PytdxFetcher 不支持北交所 {stock_code}，将自动切换其他数据源"
            )
        
        market, code = self.market_code(stock_code)
        
        # 计算需要获取的交易日数量（估算）
        from datetime import datetime as dt
        start_dt = dt.strptime(start_date, '%Y-%m-%d')
        end_dt = dt.strptime(end_date, '%Y-%m-%d')
        days = (end_dt - start_dt).days
        count = min(max(days * 5 // 7 + 10, 30), 800)  # 估算交易日，最大 800 条
        
        logger.debug(f"调用 Pytdx get_security_bars(market={market}, code={code}, count={count})")
        
        with self.session() as api:
            try:
                # 获取日 K 线数据
                # category: 9-日线, 0-5分钟, 1-15分钟, 2-30分钟, 3-1小时
                data = api.get_security_bars(
                    category=9,  # 日线
                    market=market,
                    code=code,
                    start=0,  # 从最新开始
                    count=count
                )
                
                if data is None or len(data) == 0:
                    raise DataFetchError(f"Pytdx 未查询到 {stock_code} 的数据")
                
                # 转换为 DataFrame
                df = api.to_df(data)
                
                # 过滤日期范围
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]
                
                return df
                
            except Exception as e:
                if isinstance(e, DataFetchError):
                    raise
                raise DataFetchError(f"Pytdx 获取数据失败: {e}") from e

    @staticmethod
    def normalize_data(df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化 Pytdx 数据
        
        Pytdx 返回的列名：
        datetime, open, high, low, close, vol, amount
        
        需要映射到标准列名：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # 列名映射
        column_mapping = {
            'datetime': 'date',
            'vol': 'volume',
        }
        
        df = df.rename(columns=column_mapping)
        
        # 计算涨跌幅（pytdx 不返回涨跌幅，需要自己计算）
        if 'pct_chg' not in df.columns and 'close' in df.columns:
            df['pct_chg'] = df['close'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].fillna(0).round(2)
        
        # 添加股票代码列
        df['code'] = stock_code
        
        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df

