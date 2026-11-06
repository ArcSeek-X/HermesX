# -*- coding: utf-8 -*-
"""Tencent direct daily K-line fetcher for A-share fallback routing.

A 股日线的腾讯直连兜底数据源。将标准股票代码转换为腾讯 symbol，按请求区间估算回溯天数，
解析 K 线报文并处理单次条数上限导致的截断，同时提供实时报价与名称查询所需的归一化能力。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd
import requests

try:
    import exchange_calendars as xcals
except ImportError:  # pragma: no cover - dependency is present in supported installs
    xcals = None

from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.common.errors import DataFetchError
from src.domain.market.stock_codes import normalize_stock_code, is_bse_code

logger = logging.getLogger("data_provider.tencent_fetcher")

_MAX_KLINE_BARS = 800


class TencentFetcher(BaseFetcher):
    """Fetch qfq daily K-line data from Tencent's direct quote endpoint."""

    name = "TencentFetcher"
    # This direct endpoint is the last-resort A-share daily fallback. Keeping
    # it at priority 0 made a single Efinance failure skip the richer built-in
    # fallback chain and try Tencent before AkShare/PyTDX/Baostock/YFinance.
    priority = 5
    allow_empty_daily_data = True

    _KLINE_ENDPOINT = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    _HTTP_TIMEOUT_SECONDS = 8

    def __init__(self) -> None:
        """构造抓取器：按环境变量设置数据源优先级。"""
        self.priority = _read_tencent_priority()

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """按日期区间向腾讯接口请求原始 K 线，处理截断与异常后返回原始 DataFrame。"""
        code = normalize_stock_code(stock_code)
        symbol = _to_tencent_symbol(code)
        if not symbol:
            raise DataFetchError(f"TencentFetcher unsupported stock code: {stock_code}")

        lookback = _estimate_lookback_days(start_date=start_date, end_date=end_date)
        explicit_start = _format_tencent_date(start_date)
        explicit_end = _format_tencent_date(end_date)
        explicit_window = (
            f"{explicit_start},{explicit_end}"
            if explicit_start and explicit_end
            else ","
        )
        response = requests.get(
            self._KLINE_ENDPOINT,
            params={"param": f"{symbol},day,{explicit_window},{lookback},qfq"},
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/plain,*/*"},
            timeout=self._HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        rows = _extract_kline_rows(payload, symbol=symbol)
        if not rows:
            logger.info("TencentFetcher empty daily history for %s", stock_code)
            return _empty_daily_frame()

        df = pd.DataFrame(rows)
        first_returned_date = _first_returned_date(df)
        if first_returned_date and _is_capped_history_incomplete(
            first_returned_date=first_returned_date,
            start_date=start_date,
            lookback=lookback,
            returned_rows=len(rows),
        ):
            logger.info(
                "TencentFetcher incomplete capped daily history for %s: first_date=%s requested_start=%s",
                stock_code,
                first_returned_date,
                start_date,
            )
            return _empty_daily_frame()

        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        if df.empty:
            logger.info(
                "TencentFetcher daily history outside requested range for %s: %s~%s",
                stock_code,
                start_date,
                end_date,
            )
            return _empty_daily_frame()
        return df

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """将原始行情列为标准数值类型并补齐标准列，返回可直接消费的日线数据。"""
        normalized = df.copy()
        for column in ("open", "high", "low", "close", "volume", "amount"):
            if column in normalized.columns:
                normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if "pct_chg" not in normalized.columns:
            normalized["pct_chg"] = normalized["close"].pct_change().fillna(0.0) * 100
        normalized = normalized[["date", "open", "high", "low", "close", "volume", "amount", "pct_chg"]]
        return normalized


def _to_tencent_symbol(stock_code: str) -> str:
    """将标准 6 位 A 股代码转换为腾讯 symbol（sh/sz/bj 前缀）；非法代码返回空串。"""
    code = normalize_stock_code(stock_code)
    if not code or not code.isdigit() or len(code) != 6:
        return ""
    if is_bse_code(code):
        return f"bj{code}"
    if code.startswith(("6", "5", "9")):
        return f"sh{code}"
    return f"sz{code}"


def _read_tencent_priority() -> int:
    """读取环境变量 TENCENT_PRIORITY 作为数据源优先级，解析失败回退默认值 5。"""
    raw_value = os.getenv("TENCENT_PRIORITY", "5")
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError):
        logger.warning(
            "TENCENT_PRIORITY=%r is not a valid integer; falling back to 5",
            raw_value,
        )
        return 5


def _estimate_lookback_days(*, start_date: str, end_date: str) -> int:
    """按请求起止日期估算需回溯的自然日数（含安全余量），解析失败时取默认窗口。"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        calendar_days = max(1, (end - start).days + 1)
    except ValueError:
        calendar_days = 90
    # Trading days are sparse over calendar days; add margin for holidays/suspensions.
    return max(30, min(_MAX_KLINE_BARS, int(calendar_days * 1.8) + 20))


def _empty_daily_frame() -> pd.DataFrame:
    """构造带标准列但无数据行的空日线 DataFrame。"""
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def _first_returned_date(df: pd.DataFrame) -> Optional[str]:
    """取日线数据中最早的有效日期字符串；无日期列或数据为空时返回 None。"""
    if "date" not in df.columns or df.empty:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().strftime("%Y-%m-%d")


def _is_capped_history_incomplete(
    *,
    first_returned_date: str,
    start_date: str,
    lookback: int,
    returned_rows: int,
) -> bool:
    """判断返回历史是否因单次 K 线条数上限被截断（未覆盖到请求的起始日期）。"""
    hit_cap = lookback >= _MAX_KLINE_BARS and returned_rows >= _MAX_KLINE_BARS
    if not hit_cap:
        return False
    try:
        first = datetime.strptime(first_returned_date, "%Y-%m-%d")
        requested_start = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        return False
    return first > _first_trading_date_on_or_after(requested_start)


def _first_trading_date_on_or_after(start_date: datetime) -> datetime:
    """返回不早于给定日期的首个 A 股交易日（优先用交易日历，否则按周末顺延）。"""
    if xcals is not None:
        try:
            cal = xcals.get_calendar("XSHG")
            session = cal.date_to_session(start_date.date(), direction="next")
            return datetime.combine(session.date(), datetime.min.time())
        except Exception:
            pass

    current = start_date
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def _format_tencent_date(date_text: str) -> Optional[str]:
    """将腾讯返回的日期文本归一为 YYYY-MM-DD；格式非法返回 None。"""
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _lots_to_shares(volume: Any) -> Any:
    """将腾讯以「手」为单位的成交量换算为股数（×100）；无法转换时原样返回。"""
    try:
        return float(volume) * 100
    except (TypeError, ValueError):
        return volume


def _extract_kline_rows(payload: dict[str, Any], *, symbol: str) -> list[dict[str, Any]]:
    """从腾讯 K 线 JSON 报文中提取指定 symbol 的日线/分钟线行列表；结构异常返回空列表。"""
    data = payload.get("data") if isinstance(payload, dict) else None
    item = data.get(symbol) if isinstance(data, dict) else None
    if not isinstance(item, dict):
        return []
    rows = item.get("qfqday") or item.get("day") or []
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 6:
            continue
        amount: Optional[Any] = row[6] if len(row) > 6 else None
        result.append(
            {
                "date": str(row[0]),
                "open": row[1],
                "close": row[2],
                "high": row[3],
                "low": row[4],
                "volume": _lots_to_shares(row[5]),
                "amount": amount,
            }
        )
    return result
