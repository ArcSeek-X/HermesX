"""Longbridge 日线协议与字段转换；共享客户端和状态仍由原 Fetcher 持有。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

import pandas as pd

from data_provider.common.fetcher_contract import STANDARD_COLUMNS


@dataclass(frozen=True)
class LongbridgeDailySource:
    """只使用日线所需回调，不持有宿主或新建缓存、连接及限流状态。"""

    available: Callable[[str], bool]
    get_context: Callable[[], Any]
    connection_error: Callable[[Exception], bool]
    cooldown: Callable[[Exception], None]
    symbol: Callable[[str], Optional[str]]
    to_float: Callable[..., Any]

    def fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fetch historical candlesticks from Longbridge."""
        if not self.available("daily_data"):
            raise RuntimeError("Longbridge temporarily unavailable for daily_data")

        symbol = self.symbol(stock_code)
        if symbol is None:
            raise ValueError(f"Cannot convert {stock_code} to Longbridge symbol")

        ctx = self.get_context()
        if ctx is None:
            raise RuntimeError("Longbridge QuoteContext not available")

        from longbridge.openapi import Period, AdjustType

        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        try:
            candles = ctx.history_candlesticks_by_date(
                symbol,
                Period.Day,
                AdjustType.ForwardAdjust,
                start_dt,
                end_dt,
            )
        except Exception as e:
            if self.connection_error(e):
                self.cooldown(e)
            raise

        if not candles:
            return pd.DataFrame()

        rows = []
        for c in candles:
            ts = getattr(c, "timestamp", None)
            if ts is None:
                continue
            if hasattr(ts, "date"):
                dt = ts.date()
            else:
                dt = datetime.fromtimestamp(int(ts)).date()

            rows.append({
                "date": dt.strftime("%Y-%m-%d"),
                "open": self.to_float(getattr(c, "open", None)),
                "high": self.to_float(getattr(c, "high", None)),
                "low": self.to_float(getattr(c, "low", None)),
                "close": self.to_float(getattr(c, "close", None)),
                "volume": int(getattr(c, "volume", 0) or 0),
                "turnover": self.to_float(getattr(c, "turnover", None)),
            })

        return pd.DataFrame(rows)

    @staticmethod
    def normalize_data(df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """Normalize column names to standard format."""
        if df.empty:
            return pd.DataFrame(columns=STANDARD_COLUMNS)

        rename_map = {"turnover": "amount"}
        df = df.rename(columns=rename_map)

        if "pct_chg" not in df.columns and "close" in df.columns:
            df["pct_chg"] = df["close"].pct_change() * 100

        for col in STANDARD_COLUMNS:
            if col not in df.columns:
                df[col] = None

        return df[STANDARD_COLUMNS]

