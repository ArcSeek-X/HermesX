"""AlphaVantage 日线协议与字段转换；共享客户端和状态仍由原 Fetcher 持有。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

import pandas as pd

from data_provider.common.errors import DataFetchError
from data_provider.common.fetcher_contract import STANDARD_COLUMNS


@dataclass(frozen=True)
class AlphaVantageDailySource:
    """只使用日线所需回调，不持有宿主或新建缓存、连接及限流状态。"""

    api_key: Callable[[], Optional[str]]
    is_us: Callable[[str], bool]
    sleep: Callable[[float, float], None]
    http_get: Callable[..., Any]
    base_url: Callable[[], str]

    def fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """拉取原始行情数据。"""
        if not self.api_key():
            raise DataFetchError("[AlphaVantage] API key not configured")
        if not self.is_us(stock_code):
            raise DataFetchError(f"[AlphaVantage] {stock_code} is not a US stock")

        symbol = stock_code.strip().upper()
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': 'compact',
            'apikey': self.api_key(),
        }

        try:
            self.sleep(0.5, 1.5)
            resp = self.http_get(self.base_url(), params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise DataFetchError(f"[AlphaVantage] HTTP request failed for {symbol}: {e}") from e

        if 'Note' in data:
            raise DataFetchError(f"[AlphaVantage] Rate limited: {data['Note']}")
        if 'Error Message' in data:
            raise DataFetchError(f"[AlphaVantage] API error for {symbol}: {data['Error Message']}")

        ts_key = 'Time Series (Daily)'
        if ts_key not in data or not data[ts_key]:
            raise DataFetchError(f"[AlphaVantage] No time series data for {symbol}")

        rows = []
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        for date_str, values in data[ts_key].items():
            row_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if start <= row_date <= end:
                rows.append({
                    'date': date_str,
                    '1. open': float(values.get('1. open', 0)),
                    '2. high': float(values.get('2. high', 0)),
                    '3. low': float(values.get('3. low', 0)),
                    '4. close': float(values.get('4. close', 0)),
                    '5. volume': float(values.get('5. volume', 0)),
                })

        if not rows:
            raise DataFetchError(f"[AlphaVantage] No data in date range for {symbol}")

        df = pd.DataFrame(rows)
        df.index = pd.to_datetime(df['date'])
        df.index.name = None  # 避免与 _normalize_data 重新添加的 'date' 列冲突
        return df.drop(columns=['date'])

    @staticmethod
    def normalize_data(df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """规范化原始行情数据。"""
        if df.empty:
            return df

        df = df.copy()
        df['date'] = pd.to_datetime(df.index).date
        df = df.rename(columns={
            '1. open': 'open', '2. high': 'high', '3. low': 'low',
            '4. close': 'close', '5. volume': 'volume',
        })
        # AlphaVantage returns newest-first; sort ascending before computing pct_chg
        df = df.sort_values('date', ascending=True).reset_index(drop=True)
        df['pct_chg'] = df['close'].pct_change() * 100
        df['pct_chg'] = df['pct_chg'].fillna(0).round(2)
        df['amount'] = df['volume'] * df['close']
        df['code'] = stock_code

        keep = ['code'] + STANDARD_COLUMNS
        df = df[[col for col in keep if col in df.columns]]
        return df

