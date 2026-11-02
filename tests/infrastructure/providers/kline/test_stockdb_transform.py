# -*- coding: utf-8 -*-
"""Tests for StockDB K-line normalization and aggregation helpers."""

from data_provider.kline.transform import (
    apply_stockdb_adjust,
    normalize_stockdb_daily_rows,
    normalize_stockdb_minute_rows,
    resample_rows,
    trim_rows,
)


def test_normalize_stockdb_daily_rows_sorts_and_formats_dates() -> None:
    rows = normalize_stockdb_daily_rows(
        [
            {"date": 20260730, "open": 11, "close": 12, "high": 13, "low": 10, "volume": 2000, "amount": 10000},
            {"date": 20260729, "open": 10, "close": 11, "high": 12, "low": 9, "volume": 1000, "amount": 9000},
        ]
    )

    assert [item["date"] for item in rows] == ["2026-07-29", "2026-07-30"]
    assert rows[1]["change_percent"] == round((12 - 11) / 11 * 100, 2)


def test_normalize_stockdb_minute_rows_formats_timestamp() -> None:
    rows = normalize_stockdb_minute_rows(
        [{"date": 20260730093100, "open": 10, "close": 10.2, "high": 10.3, "low": 9.9}]
    )

    assert rows[0]["date"] == "2026-07-30 09:31:00"


def test_apply_stockdb_adjust_supports_qfq() -> None:
    rows = normalize_stockdb_daily_rows(
        [
            {"date": 20260729, "open": 10, "close": 10, "high": 10, "low": 10},
            {"date": 20260730, "open": 20, "close": 20, "high": 20, "low": 20},
        ]
    )
    factors = [
        {"date": 20260729, "cum": 2},
        {"date": 20260730, "cum": 4},
    ]

    adjusted = apply_stockdb_adjust(rows, factors, "qfq")

    assert adjusted[0]["close"] == 20.0
    assert adjusted[1]["close"] == 20.0


def test_resample_rows_supports_5d_and_weekly() -> None:
    daily_rows = normalize_stockdb_daily_rows(
        [
            {"date": 20260721 + offset, "open": 10 + offset, "close": 10 + offset, "high": 11 + offset, "low": 9 + offset}
            for offset in range(5)
        ]
    )

    five_day = resample_rows(daily_rows, "5d")
    weekly = resample_rows(daily_rows, "weekly")

    assert len(five_day) == 1
    assert five_day[0]["open"] == 10.0
    assert len(weekly) == 1


def test_trim_rows_applies_before_date_and_limit() -> None:
    rows = [
        {"date": "2026-07-28", "close": 10},
        {"date": "2026-07-29", "close": 11},
        {"date": "2026-07-30", "close": 12},
    ]

    trimmed = trim_rows(rows, 1, "2026-07-30")

    assert trimmed == [{"date": "2026-07-29", "close": 11}]

