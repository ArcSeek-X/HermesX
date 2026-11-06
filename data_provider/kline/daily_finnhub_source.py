"""Finnhub 日线协议与字段转换；共享客户端和状态仍由原 Fetcher 持有。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

import pandas as pd

from data_provider.common.errors import DataFetchError
from data_provider.common.fetcher_contract import STANDARD_COLUMNS


@dataclass(frozen=True)
class FinnhubDailySource:
    """只使用日线所需回调，不持有宿主或新建缓存、连接及限流状态。"""

    api_key: Callable[[], Optional[str]]
    is_us: Callable[[str], bool]
    sleep: Callable[[float, float], None]
    http_get: Callable[..., Any]
    base_url: Callable[[], str]

    def fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """按日期区间从 Finnhub 拉取原始 K 线数据；缺少 API key 或非美股时抛错/跳过。"""
        if not self.api_key():
            raise DataFetchError("[Finnhub] API key not configured")
        if not self.is_us(stock_code):
            raise DataFetchError(f"[Finnhub] {stock_code} is not a US stock")

        symbol = stock_code.strip().upper()
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
        end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())

        url = f"{self.base_url()}/stock/candle"
        params = {
            'symbol': symbol,
            'resolution': 'D',
            'from': start_ts,
            'to': end_ts,
            'token': self.api_key(),
        }

        try:
            self.sleep(0.3, 0.8)
            resp = self.http_get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise DataFetchError(f"[Finnhub] HTTP request failed for {symbol}: {e}") from e

        if data.get('s') != 'ok' or not data.get('c'):
            raise DataFetchError(f"[Finnhub] No data returned for {symbol}")

        return pd.DataFrame({
            'c': data['c'],
            'h': data['h'],
            'l': data['l'],
            'o': data['o'],
            't': data['t'],
            'v': data['v'],
        })

    @staticmethod
    def normalize_data(df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """将 Finnhub 原始字段归一化为标准日线列（日期、开高低收、成交量等）。"""
        if df.empty:
            return df

        df = df.copy()
        df['date'] = pd.to_datetime(df['t'], unit='s').dt.date
        df = df.rename(columns={
            'o': 'open', 'h': 'high', 'l': 'low',
            'c': 'close', 'v': 'volume',
        })
        df['pct_chg'] = df['close'].pct_change() * 100
        df['pct_chg'] = df['pct_chg'].fillna(0).round(2)
        df['amount'] = df['volume'] * df['close']
        df['code'] = stock_code

        keep = ['code'] + STANDARD_COLUMNS
        df = df[[col for col in keep if col in df.columns]]
        return df

