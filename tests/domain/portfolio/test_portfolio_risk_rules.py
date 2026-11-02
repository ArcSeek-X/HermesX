# -*- coding: utf-8 -*-
"""`src/domain/portfolio/risk_rules.py` 的纯规则回归。

W5.7 把持仓风险的纯计算从 `PortfolioRiskService` 下沉到 domain 后，这里锁定
迁移前口径：占比分母保护、集中度排序与告警阈值、回撤从 0 峰起算、止损接近度
分层、主板块优先「行业」。这些用例不装配仓储、端口或数据库，验证 domain 侧
真的零 IO。
"""

from __future__ import annotations

import pytest

from src.domain.portfolio.risk_rules import (
    UNCLASSIFIED_SECTOR,
    build_stop_loss_report,
    compute_drawdown_metrics,
    compute_weight_pct,
    pick_primary_board_name,
    rank_exposure_rows,
)


def test_compute_weight_pct_guards_non_positive_total() -> None:
    assert compute_weight_pct(25.0, 100.0) == pytest.approx(25.0)
    assert compute_weight_pct(25.0, 0.0) == 0.0
    assert compute_weight_pct(25.0, -100.0) == 0.0


def test_rank_exposure_rows_sorts_and_flags_by_rounded_top_weight() -> None:
    rows = [
        {"symbol": "B", "market_value_base": 500.0, "weight_pct": 5.0},
        {"symbol": "A", "market_value_base": 9500.0, "weight_pct": 95.0},
        {"symbol": "C", "market_value_base": 0.0, "weight_pct": 0.0},
    ]

    top_rows, top_weight, alert = rank_exposure_rows(rows, 40.0)

    assert [row["symbol"] for row in top_rows] == ["A", "B", "C"]
    assert top_weight == 95.0
    assert alert is True


def test_rank_exposure_rows_caps_rows_and_handles_empty() -> None:
    rows = [
        {"symbol": f"S{index}", "market_value_base": float(index), "weight_pct": float(index)}
        for index in range(1, 15)
    ]

    top_rows, top_weight, alert = rank_exposure_rows(rows, 100.0, top_n=3)

    assert len(top_rows) == 3
    assert top_weight == 14.0
    assert alert is False
    assert rank_exposure_rows([], 10.0) == ([], 0.0, False)


def test_compute_drawdown_metrics_tracks_peak_and_current() -> None:
    series = [("2026-01-01", 100.0), ("2026-01-02", 120.0), ("2026-01-03", 90.0)]

    metrics = compute_drawdown_metrics(series, 20.0)

    assert metrics["series_points"] == 3
    assert metrics["max_drawdown_pct"] == pytest.approx(25.0)
    assert metrics["current_drawdown_pct"] == pytest.approx(25.0)
    assert metrics["alert"] is True


def test_compute_drawdown_metrics_is_order_insensitive_and_zero_peak_safe() -> None:
    unordered = [("2026-01-03", 90.0), ("2026-01-01", 100.0), ("2026-01-02", 120.0)]
    assert compute_drawdown_metrics(unordered, 20.0) == compute_drawdown_metrics(
        sorted(unordered), 20.0
    )

    zero_peak = compute_drawdown_metrics([("2026-01-01", 0.0), ("2026-01-02", 0.0)], 1.0)
    assert zero_peak["max_drawdown_pct"] == 0.0
    assert zero_peak["alert"] is False


def test_compute_drawdown_metrics_empty_series() -> None:
    metrics = compute_drawdown_metrics([], 10.0)

    assert metrics == {
        "series_points": 0,
        "max_drawdown_pct": 0.0,
        "current_drawdown_pct": 0.0,
        "alert": False,
    }


def test_build_stop_loss_report_splits_near_and_triggered() -> None:
    snapshot = {
        "accounts": [
            {
                "account_id": 1,
                "positions": [
                    {"symbol": "AAA", "avg_cost": 100.0, "last_price": 85.0},
                    {"symbol": "BBB", "avg_cost": 100.0, "last_price": 91.0},
                    {"symbol": "CCC", "avg_cost": 100.0, "last_price": 99.0},
                    {"symbol": "DDD", "avg_cost": 0.0, "last_price": 10.0},
                ],
            }
        ]
    }

    report = build_stop_loss_report(snapshot, stop_loss_pct=10.0, near_ratio=0.5)

    assert report["near_alert"] is True
    assert report["near_count"] == 2
    assert report["triggered_count"] == 1
    assert [item["symbol"] for item in report["items"]] == ["AAA", "BBB"]
    assert report["items"][0]["is_triggered"] is True
    assert report["items"][1]["is_triggered"] is False
    assert report["items"][1]["near_threshold_pct"] == pytest.approx(5.0)


def test_build_stop_loss_report_without_positions() -> None:
    report = build_stop_loss_report({"accounts": []}, stop_loss_pct=10.0, near_ratio=0.5)

    assert report == {"near_alert": False, "triggered_count": 0, "near_count": 0, "items": []}


def test_pick_primary_board_name_prefers_industry() -> None:
    boards = [
        {"name": "概念题材", "type": "概念"},
        {"name": "半导体", "type": "行业板块"},
        {"name": "其他行业", "type": "行业"},
    ]

    assert pick_primary_board_name(boards) == "半导体"
    assert pick_primary_board_name([{"name": "概念题材", "type": "概念"}]) == "概念题材"
    assert pick_primary_board_name([{"name": ""}, "not-a-dict"]) is None
    assert pick_primary_board_name(None) is None
    assert pick_primary_board_name([]) is None


def test_unclassified_sector_constant_is_stable() -> None:
    assert UNCLASSIFIED_SECTOR == "UNCLASSIFIED"
