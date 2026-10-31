"""DB-first K-line history loader for Agent tools.

Provides:
- ContextVar-based frozen target_date propagation across threads
- ``load_history_df``: read from DB first, injected daily-bar fetcher fallback

Fixes #1066 – eliminates 45+ redundant HTTP requests per stock in Agent mode.
"""
from __future__ import annotations

import contextvars
import logging
from datetime import date, datetime, timedelta
from typing import Any, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)
_CACHE_MIN_RECORDS = 30

# ---------------------------------------------------------------------------
# Frozen target date (ContextVar) – set once per stock in pipeline, read by
# all agent tool threads via copy_context().run().
# ---------------------------------------------------------------------------
_frozen_target_date: contextvars.ContextVar[Optional[date]] = contextvars.ContextVar(
    "_frozen_target_date", default=None,
)


def set_frozen_target_date(d: date) -> contextvars.Token:
    return _frozen_target_date.set(d)


def get_frozen_target_date() -> Optional[date]:
    return _frozen_target_date.get()


def reset_frozen_target_date(token: contextvars.Token) -> None:
    _frozen_target_date.reset(token)


# ---------------------------------------------------------------------------
# Daily-bar fetcher port (injected by bootstrap; network fallback only)
# ---------------------------------------------------------------------------
# ``load_history_df`` reads DB first and falls back to a daily-bar fetcher for
# the network path.  The concrete fetcher (a ``data_provider`` adapter) is wired
# at process startup via :func:`set_history_daily_bar_fetcher`, so this module
# never imports ``data_provider`` directly。未装配时网络回退优雅降级为 ``(None, "none")``。
_daily_bar_fetcher: Any = None


def set_history_daily_bar_fetcher(fetcher: Any) -> None:
    """装配日线取数网络回退端口（进程启动时由 bootstrap 自顶向下调用）。"""
    global _daily_bar_fetcher
    _daily_bar_fetcher = fetcher


def _get_daily_bar_fetcher() -> Any:
    return _daily_bar_fetcher

# ---------------------------------------------------------------------------
# DB-first K-line repo seam (injected by bootstrap; replaces ad-hoc get_db())
# ---------------------------------------------------------------------------
# load_history_df 的 DB 主路经模块级 seam 注入的 K 线仓储端口取数（进程启动时由
# bootstrap.history.configure_history_loader 装配 DatabaseManager 作适配器）；未装配时
# DB 主路在既有 try/except 内降级为网络回退，应用层不 import src.storage。
_kline_repo: Any = None


def set_history_kline_repo(repo: Any) -> None:
    """装配历史 loader 的 DB 主路 K 线仓储端口（幂等）。"""
    global _kline_repo
    _kline_repo = repo


def _get_kline_repo() -> Any:
    return _kline_repo


# ---------------------------------------------------------------------------
# DB-first history loader
# ---------------------------------------------------------------------------
def _history_code_candidates(stock_code: str) -> Tuple[List[str], str]:
    from src.application.quote.stock_code_utils import (
        canonical_stock_code_for_analysis,
        normalize_stock_code_for_analysis,
    )

    raw_code = str(stock_code or "").strip()
    normalized_code = canonical_stock_code_for_analysis(
        normalize_stock_code_for_analysis(raw_code)
    )
    candidates: List[str] = []
    for candidate in (canonical_stock_code_for_analysis(raw_code), normalized_code):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates, normalized_code


def _coerce_bar_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return date.min
    if hasattr(value, "date"):
        try:
            coerced = value.date()
            return coerced if isinstance(coerced, date) else date.min
        except Exception:
            return date.min
    return date.min


def _bar_date(bar: Any) -> date:
    row_date = _coerce_bar_date(getattr(bar, "date", None))
    if row_date != date.min:
        return row_date
    if hasattr(bar, "to_dict"):
        try:
            return _coerce_bar_date((bar.to_dict() or {}).get("date"))
        except Exception:
            return date.min
    return date.min


def _select_best_bars(db, stock_code: str, start: date, end: date) -> Tuple[Optional[str], list]:
    candidates, normalized_code = _history_code_candidates(stock_code)
    best_code = None
    best_bars = []
    best_key = None

    for candidate in candidates:
        bars = list(db.get_data_range(candidate, start, end) or [])
        if not bars:
            continue
        latest_date = max(_bar_date(bar) for bar in bars)
        key = (latest_date, len(bars), candidate == normalized_code)
        if best_key is None or key > best_key:
            best_key = key
            best_code = candidate
            best_bars = bars

    return best_code, best_bars


def load_history_df(
    stock_code: str,
    days: int = 60,
    target_date: Optional[date] = None,
) -> Tuple[Optional[pd.DataFrame], str]:
    """Load K-line history, DB first with an injected daily-bar fetcher fallback.

    Returns ``(df, source)`` where *source* is ``"db_cache"`` on DB hit or the
    actual provider name on network fallback.  Returns ``(None, "none")`` when
    both paths fail.
    """
    # Resolve effective end date
    if target_date is not None:
        end = target_date
    else:
        frozen = get_frozen_target_date()
        end = frozen if frozen else date.today()

    # Calendar-day buffer: ~1.8x trading days + margin for long holidays
    start = end - timedelta(days=int(days * 1.8) + 10)

    # --- 1. DB lookup (canonical code, then prefix-stripped fallback) ------
    try:
        db = _get_kline_repo()
        _code, bars = _select_best_bars(db, stock_code, start, end)
        required_records = max(min(days, _CACHE_MIN_RECORDS), 1)
        latest_date = max((_bar_date(bar) for bar in bars), default=date.min)
        if bars and latest_date >= end and len(bars) >= required_records:
            df = pd.DataFrame([b.to_dict() for b in bars])
            logger.debug(
                "load_history_df(%s): %d bars from DB (requested %d)",
                stock_code, len(df), days,
            )
            return df, "db_cache"
    except Exception as e:
        logger.debug("load_history_df(%s): DB read failed: %s", stock_code, e)

    # --- 2. Network fallback via injected daily-bar fetcher port ----------
    fetcher = _get_daily_bar_fetcher()
    if fetcher is None:
        logger.warning(
            "load_history_df(%s): daily-bar fetcher not configured; skip network fallback",
            stock_code,
        )
        return None, "none"
    try:
        df, source = fetcher.get_daily_data(stock_code, days=days)
        if df is not None and not df.empty:
            return df, source
    except Exception as e:
        logger.warning("load_history_df(%s): daily-bar fetcher failed: %s", stock_code, e)

    return None, "none"
